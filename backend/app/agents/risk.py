from app.schemas.intelligence import CropHealthResult, NearbyMatch, RiskResult, Severity, SpreadPotential, WeatherResult


class RiskAgent:
    """Deterministic scoring; no model calls or invented precision."""

    def assess(self, crop_health: CropHealthResult, weather: WeatherResult, nearby: list[NearbyMatch], season: str) -> RiskResult:
        finding = crop_health.finding
        severity_points = {Severity.LOW: 18, Severity.MODERATE: 42, Severity.HIGH: 65}[finding.severity]
        spread_points = {SpreadPotential.LOW: 0, SpreadPotential.MODERATE: 10, SpreadPotential.HIGH: 20, SpreadPotential.UNKNOWN: 0}[finding.spread_potential]
        confidence_factor = max(0.3, finding.confidence)
        individual = round(min(100, (severity_points + spread_points) * confidence_factor))
        factors = [f"Possible issue severity: {finding.severity.value}", f"Assessment confidence: {finding.confidence:.0%}"]
        if finding.spread_potential != SpreadPotential.UNKNOWN:
            factors.append(f"Spread potential: {finding.spread_potential.value}")
        if season:
            factors.append(f"Reported season: {season}")
        # Synthetic reports inform the demo display but must never inflate a real risk score.
        real_nearby = [item for item in nearby if not item.is_synthetic]
        community = min(100, round(individual * 0.35 + min(len(real_nearby), 8) * 7))
        if real_nearby:
            factors.append(f"{len(real_nearby)} recent nearby field reports")
        if weather.current and not weather.stale and weather.source in ("LIVE", "CACHED"):
            if weather.current.relative_humidity_pct >= 85 and finding.spread_potential in (SpreadPotential.MODERATE, SpreadPotential.HIGH):
                individual = min(100, individual + 8)
                community = min(100, community + 5)
                factors.append("Current high humidity may favor spread")
        monitoring = finding.monitoring[:3] or ["Inspect the affected field again within 2–3 days."]
        return RiskResult(individual_risk=individual, community_risk=community, risk_factors=factors, recommended_monitoring=monitoring)
