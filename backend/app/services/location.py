from math import asin, cos, radians, sin, sqrt

from app.core.errors import AppError

EARTH_RADIUS_KM = 6371.0088


def validate_coordinates(latitude: float, longitude: float) -> None:
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise AppError(422, "invalid_location", "Latitude or longitude is outside the valid range.")


def haversine_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    validate_coordinates(latitude_a, longitude_a)
    validate_coordinates(latitude_b, longitude_b)
    lat_a, lat_b = radians(latitude_a), radians(latitude_b)
    delta_lat, delta_lon = radians(latitude_b - latitude_a), radians(longitude_b - longitude_a)
    chord = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(min(1, sqrt(chord)))


def coarse_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    """Round cluster centers to roughly kilometre scale before public responses."""
    validate_coordinates(latitude, longitude)
    return round(latitude, 2), round(longitude, 2)
