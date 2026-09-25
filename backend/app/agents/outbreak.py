"""Deterministic nearby report matching and outbreak alert gating."""

import math
from datetime import datetime, timedelta
from uuid import UUID

from app.schemas.enums import AnalysisState, ReviewStatus
from app.schemas.risk import OutbreakAssessment, OutbreakInput, ReportEvidence
from app.utils.geography import haversine_distance_km


class OutbreakAgent:
    """Score corroborated local evidence; leave persistence and delivery to services."""

    def __init__(
        self,
        *,
        radius_km: float = 10,
        lookback_days: int = 14,
        alert_threshold: float = 0.60,
    ) -> None:
        if not math.isfinite(radius_km) or not 0 < radius_km <= 50:
            raise ValueError("radius_km must be between 0 and 50")
        if lookback_days <= 0:
            raise ValueError("lookback_days must be positive")
        if not math.isfinite(alert_threshold) or not 0 <= alert_threshold <= 1:
            raise ValueError("alert_threshold must be between 0 and 1")
        self.radius_km = radius_km
        self.lookback_days = lookback_days
        self.alert_threshold = max(0.60, alert_threshold)

    def assess(self, request: OutbreakInput) -> OutbreakAssessment:
        source = request.source_report
        cutoff = request.evaluated_at - timedelta(days=self.lookback_days)
        can_match = (
            source.location is not None
            and source.commodity_id is not None
            and source.canonical_disease_code is not None
            and self._qualifies(source, cutoff, request.evaluated_at)
        )

        matching_farmers: set[UUID] = set()
        if can_match:
            for report in request.nearby_reports:
                if report.report_id == source.report_id or report.farmer_id == source.farmer_id:
                    continue
                if report.commodity_id != source.commodity_id:
                    continue
                if report.canonical_disease_code != source.canonical_disease_code:
                    continue
                if not self._qualifies(report, cutoff, request.evaluated_at):
                    continue
                if report.location is None:
                    continue
                if haversine_distance_km(
                    source.location.latitude,
                    source.location.longitude,
                    report.location.latitude,
                    report.location.longitude,
                ) <= self.radius_km:
                    matching_farmers.add(report.farmer_id)

        individual = request.risk.individual_risk
        community = min(1.0, individual + min(len(matching_farmers) * 0.15, 0.50))
        alert = False
        analysis = request.crop_analysis

        if analysis.confidence < 0.70 and source.review_status != ReviewStatus.VERIFIED:
            reason = "Monitor and request expert review: the crop analysis has low confidence."
        elif not can_match:
            reason = "Monitor and request expert review: location, canonical crop/problem, or eligible report evidence is missing."
        elif analysis.spread_potential in {"low", "unknown"}:
            reason = "Monitor and request expert review: spread potential is low or uncertain."
        elif community < 0.30:
            reason = "Monitor: the deterministic community risk score is below the advisory threshold."
        elif len(matching_farmers) < 2:
            reason = (
                "Advisory for expert review: fewer than three distinct farmers have "
                "qualifying local reports."
            )
        elif community < self.alert_threshold:
            reason = "Advisory: corroborated community risk is below the nearby alert threshold."
        else:
            alert = True
            level = "critical" if community >= 0.80 else "warning"
            reason = (
                f"{level.capitalize()} nearby alert: {len(matching_farmers) + 1} distinct "
                f"farmers have qualifying reports of the same crop problem within "
                f"{self.radius_km:g} km during the last {self.lookback_days} days."
            )

        return OutbreakAssessment(
            individual_risk=individual,
            community_risk=community,
            nearby_alert=alert,
            alert_reason=reason,
        )

    @staticmethod
    def _qualifies(report: ReportEvidence, cutoff: datetime, evaluated_at: datetime) -> bool:
        return (
            report.analysis_state == AnalysisState.SUCCEEDED
            and report.review_status in {ReviewStatus.PENDING, ReviewStatus.VERIFIED}
            and cutoff <= report.created_at <= evaluated_at
            and (report.confidence >= 0.70 or report.review_status == ReviewStatus.VERIFIED)
        )
