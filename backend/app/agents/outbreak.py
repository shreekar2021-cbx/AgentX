from app.schemas.intelligence import CropHealthResult, NearbyMatch, OutbreakResult, Severity, SpreadPotential, WeatherResult


class OutbreakAgent:
    """Conservative local cluster signal, never a confirmed outbreak declaration."""

    def detect(self, crop_health: CropHealthResult, nearby: list[NearbyMatch], weather: WeatherResult, *, allow_synthetic: bool = False) -> OutbreakResult:
        finding = crop_health.finding
        real = [item for item in nearby if not item.is_synthetic and item.age_hours <= 168 and item.severity != Severity.LOW]
        synthetic = [item for item in nearby if item.is_synthetic and item.age_hours <= 168 and item.severity != Severity.LOW]
        real_owners = {item.owner_id for item in real}
        synthetic_owners = {item.owner_id for item in synthetic}
        # Never combine simulated and real reports to meet a cluster threshold.
        synthetic_evidence = allow_synthetic and len(real_owners) < 3 and len(synthetic_owners) >= 3
        relevant = synthetic if synthetic_evidence else real
        distinct = {item.owner_id for item in relevant}
        strong_enough = finding.confidence >= 0.65 and finding.severity != Severity.LOW and finding.spread_potential in (SpreadPotential.MODERATE, SpreadPotential.HIGH)
        # A local knowledge fallback is intentionally low-confidence and cannot trigger alerts.
        alert = strong_enough and len(distinct) >= 3
        if alert:
            prefix = "Synthetic development cluster" if synthetic_evidence else "Possible cluster"
            reason = f"{prefix}: {len(distinct)} other recent {finding.possible_problem} observations within the selected radius. Verify with local agricultural authorities."
        elif finding.confidence < 0.65:
            reason = "No cluster alert: the possible issue has insufficient analysis confidence."
        else:
            reason = "No conservative outbreak threshold was met. Continue normal monitoring."
        radius = min(10.0, max((item.distance_km for item in relevant), default=0.0) + 1.0) if alert else 0.0
        cluster_confidence = min(0.9, round(finding.confidence * min(1, len(distinct) / 5), 2)) if alert else 0.0
        if weather.current and not weather.stale and weather.source in ("LIVE", "CACHED") and weather.current.relative_humidity_pct >= 85 and finding.spread_potential == SpreadPotential.HIGH and alert:
            reason += " Current humidity supports closer monitoring."
        return OutbreakResult(nearby_alert=alert, alert_reason=reason, cluster_size=len(distinct), risk_radius_km=round(radius, 1), confidence=cluster_confidence, evidence_is_synthetic=synthetic_evidence)
