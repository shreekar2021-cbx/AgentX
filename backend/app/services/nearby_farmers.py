"""Crop-relevant nearby farmer matching over already-authorized location data."""

import math
from typing import Iterable, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from app.schemas.common import DatabaseModel
from app.utils.geography import haversine_distance_km


class FarmerLocation(DatabaseModel):
    """Coordinates may come from GPS or be entered manually by the farmer."""

    model_config = ConfigDict(allow_inf_nan=False)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    source: Literal["gps", "manual"] = "manual"


def preferred_farmer_location(
    farm_location: FarmerLocation | None,
    profile_location: FarmerLocation | None,
) -> FarmerLocation | None:
    """Use farm coordinates when available, otherwise the farmer's profile pin."""
    return farm_location or profile_location


class FarmerMatchCandidate(DatabaseModel):
    farmer_id: UUID
    location: FarmerLocation
    active_crop_ids: set[UUID] = Field(default_factory=set)


class NearbyFarmer(DatabaseModel):
    farmer_id: UUID
    distance_km: float = Field(ge=0)
    matched_crop_ids: list[UUID] = Field(min_length=1)


class NearbyFarmerMatcher:
    """Match each eligible farmer once, sorted by nearest matching location."""

    def __init__(self, radius_km: float = 10) -> None:
        if not math.isfinite(radius_km) or radius_km <= 0:
            raise ValueError("radius_km must be a finite positive number")
        self.radius_km = radius_km

    def match(
        self,
        *,
        reporting_farmer_id: UUID,
        reporting_location: FarmerLocation,
        relevant_crop_ids: set[UUID],
        candidates: Iterable[FarmerMatchCandidate],
    ) -> list[NearbyFarmer]:
        """Return distinct other farmers within radius who grow a relevant crop.

        `relevant_crop_ids` may contain the reported crop and any explicitly
        designated related crops. An empty set intentionally matches nobody.
        Candidate locations should already follow farm-first, profile-fallback
        selection when both are available.
        """
        if not relevant_crop_ids:
            return []

        nearest_by_farmer: dict[UUID, NearbyFarmer] = {}
        for candidate in candidates:
            if candidate.farmer_id == reporting_farmer_id:
                continue
            matched_crops = candidate.active_crop_ids.intersection(relevant_crop_ids)
            if not matched_crops:
                continue
            distance = haversine_distance_km(
                reporting_location.latitude,
                reporting_location.longitude,
                candidate.location.latitude,
                candidate.location.longitude,
            )
            if distance > self.radius_km:
                continue

            match = NearbyFarmer(
                farmer_id=candidate.farmer_id,
                distance_km=distance,
                matched_crop_ids=sorted(matched_crops, key=str),
            )
            previous = nearest_by_farmer.get(candidate.farmer_id)
            if previous is None:
                nearest_by_farmer[candidate.farmer_id] = match
            else:
                nearest_by_farmer[candidate.farmer_id] = NearbyFarmer(
                    farmer_id=candidate.farmer_id,
                    distance_km=min(previous.distance_km, match.distance_km),
                    matched_crop_ids=sorted(
                        set(previous.matched_crop_ids).union(match.matched_crop_ids),
                        key=str,
                    ),
                )

        return sorted(nearest_by_farmer.values(), key=lambda item: (item.distance_km, str(item.farmer_id)))
