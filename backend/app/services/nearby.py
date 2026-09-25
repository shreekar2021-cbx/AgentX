from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.repositories.local import LocalRepository
from app.schemas.intelligence import NearbyAlertPublic, NearbyMatch, Severity
from app.services.location import coarse_coordinates, haversine_km


class NearbyReportService:
    def __init__(self, repository: LocalRepository, radius_km: float = 10) -> None:
        self.repository = repository
        self.radius_km = radius_km

    async def matching(self, *, crop: str, possible_problem: str, latitude: float, longitude: float, owner_id: str, report_id: str, radius_km: float | None = None) -> list[NearbyMatch]:
        radius = radius_km or self.radius_km
        rows = await self.repository.recent_reports(crop, datetime.now(timezone.utc) - timedelta(days=7))
        now = datetime.now(timezone.utc)
        matches: list[NearbyMatch] = []
        for row in rows:
            if row["id"] == report_id or row["owner_id"] == owner_id or row["possible_problem"].casefold() != possible_problem.casefold():
                continue
            distance = haversine_km(latitude, longitude, row["latitude"], row["longitude"])
            if distance > radius:
                continue
            age = (now - datetime.fromisoformat(row["created_at"])).total_seconds() / 3600
            matches.append(NearbyMatch(report_id=UUID(row["id"]), owner_id=row["owner_id"], crop=row["crop"], possible_problem=row["possible_problem"], severity=Severity(row["severity"]), distance_km=round(distance, 1), age_hours=round(max(0, age), 1), is_synthetic=bool(row["is_synthetic"])))
        priority = {Severity.HIGH: 0, Severity.MODERATE: 1, Severity.LOW: 2}
        return sorted(matches, key=lambda item: (priority[item.severity], item.distance_km, item.age_hours))

    async def public_alerts(self, *, crop: str, latitude: float, longitude: float, radius_km: float | None = None, include_synthetic: bool = False) -> list[NearbyAlertPublic]:
        radius = radius_km or self.radius_km
        rows = await self.repository.recent_reports(crop, datetime.now(timezone.utc) - timedelta(days=7))
        groups: dict[tuple[str, str, bool], list[dict]] = defaultdict(list)
        for row in rows:
            if row["is_synthetic"] and not include_synthetic:
                continue
            if row["confidence"] is None or row["confidence"] < 0.65:
                continue
            distance = haversine_km(latitude, longitude, row["latitude"], row["longitude"])
            if distance <= radius:
                groups[(row["district"], row["possible_problem"], bool(row["is_synthetic"]))].append(row)
        alerts: list[NearbyAlertPublic] = []
        for (district, issue, synthetic), group in groups.items():
            unique_owners = {row["owner_id"] for row in group}
            if len(unique_owners) < 3:
                continue
            center_lat = sum(row["latitude"] for row in group) / len(group)
            center_lon = sum(row["longitude"] for row in group) / len(group)
            coarse_lat, coarse_lon = coarse_coordinates(center_lat, center_lon)
            severity = max((Severity(row["severity"]) for row in group), key=lambda level: {Severity.LOW: 1, Severity.MODERATE: 2, Severity.HIGH: 3}[level])
            observed = max(datetime.fromisoformat(row["created_at"]) for row in group)
            alerts.append(NearbyAlertPublic(
                id=f"{district.casefold().replace(' ', '-')}-{issue.casefold().replace(' ', '-')}-{'demo' if synthetic else 'reported'}", crop=crop,
                possible_problem=issue, district=district, severity=severity, cluster_size=len(unique_owners),
                distance_km=round(haversine_km(latitude, longitude, center_lat, center_lon), 1),
                risk_radius_km=min(radius, max(1.0, round(max(haversine_km(center_lat, center_lon, row["latitude"], row["longitude"]) for row in group) + 1, 1))),
                latitude=coarse_lat, longitude=coarse_lon, observed_at=observed,
                is_synthetic=synthetic,
            ))
        return sorted(alerts, key=lambda item: (item.distance_km, -item.cluster_size))
