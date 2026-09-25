"""Validated coordinate helpers and deterministic great-circle distance."""

import math

EARTH_MEAN_RADIUS_KM = 6371.0088


def _validate_coordinate(latitude: float, longitude: float) -> None:
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("Latitude and longitude must be finite numbers")
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90 degrees")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180 degrees")


def haversine_distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Return shortest surface distance between two latitude/longitude points."""
    _validate_coordinate(latitude_a, longitude_a)
    _validate_coordinate(latitude_b, longitude_b)

    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    lat_delta = lat_b - lat_a
    lon_delta = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(lat_delta / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(lon_delta / 2) ** 2
    )
    # Bound floating point round-off at antipodal points.
    central_angle = 2 * math.asin(math.sqrt(min(1.0, max(0.0, haversine))))
    return EARTH_MEAN_RADIUS_KM * central_angle
