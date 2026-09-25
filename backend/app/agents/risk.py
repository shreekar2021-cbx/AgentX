"""Deterministic individual crop risk scoring."""

from app.schemas.enums import Severity
from app.schemas.risk import IndividualRiskAssessment, RiskInput

SEVERITY_WEIGHTS = {
    Severity.LOW: 0.25,
    Severity.MEDIUM: 0.50,
    Severity.HIGH: 0.75,
    Severity.CRITICAL: 1.00,
}


class RiskAgent:
    """Apply the versioned architecture formula without a model call."""

    def assess(self, request: RiskInput) -> IndividualRiskAssessment:
        analysis = request.crop_analysis
        weather = request.weather
        weather_status = "missing" if weather is None else ("stale" if weather.is_stale else "fresh")

        multiplier = 1.0
        if weather_status == "fresh" and weather is not None:
            if weather.humidity_pct is not None and weather.humidity_pct > 80:
                multiplier += 0.20
            if weather.observed_rain_48h_mm is not None and weather.observed_rain_48h_mm > 0:
                multiplier += 0.15

        score = min(1.0, analysis.confidence * SEVERITY_WEIGHTS[analysis.severity] * multiplier)
        expert_review = (
            analysis.expert_verification
            or analysis.confidence < 0.70
            or analysis.severity == Severity.CRITICAL
            or analysis.spread_potential == "unknown"
        )
        return IndividualRiskAssessment(
            individual_risk=score,
            weather_status=weather_status,
            expert_review_recommended=expert_review,
        )
