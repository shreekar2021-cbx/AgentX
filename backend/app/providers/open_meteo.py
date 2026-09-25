from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import Settings
from app.schemas.intelligence import WeatherCurrent, WeatherDay, WeatherHour, WeatherResult

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
LOCAL_TZ = timezone(timedelta(hours=5, minutes=30))


class WeatherProviderError(Exception):
    pass


def _as_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return (parsed.replace(tzinfo=LOCAL_TZ) if parsed.tzinfo is None else parsed).astimezone(timezone.utc)


def agricultural_indicators(current: WeatherCurrent, daily: list[WeatherDay]) -> list[str]:
    indicators: list[str] = []
    if current.relative_humidity_pct >= 85:
        indicators.append("High humidity: inspect leaves for disease symptoms after prolonged wetness.")
    if current.wind_speed_kmh >= 20:
        indicators.append("Wind is elevated: postpone drift-prone field operations.")
    if any(day.precipitation_mm >= 5 for day in daily[:2]):
        indicators.append("Rain is forecast soon: review drainage and timing of field work.")
    if any(day.max_temperature_c >= 35 for day in daily[:2]):
        indicators.append("Heat is forecast: monitor crop water stress.")
    if not indicators:
        indicators.append("No weather threshold in this short forecast triggered a field notice.")
    return indicators


class OpenMeteoProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient, endpoint: str = OPEN_METEO_URL) -> None:
        self.settings = settings
        self.client = client
        self.endpoint = endpoint

    async def forecast(self, latitude: float, longitude: float) -> WeatherResult:
        params = {
            "latitude": latitude, "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code",
            "forecast_days": 4, "timezone": "Asia/Kolkata",
        }
        try:
            response = await self.client.get(self.endpoint, params=params, timeout=self.settings.weather_timeout_seconds)
            response.raise_for_status()
            body = response.json()
            current_body = body["current"]
            current = WeatherCurrent(
                temperature_c=current_body["temperature_2m"],
                relative_humidity_pct=current_body["relative_humidity_2m"],
                precipitation_mm=current_body["precipitation"],
                wind_speed_kmh=current_body["wind_speed_10m"],
                weather_code=current_body["weather_code"],
                observed_at=_as_utc(current_body["time"]),
            )
            daily_body = body["daily"]
            daily = [WeatherDay(
                date=day, max_temperature_c=daily_body["temperature_2m_max"][i],
                min_temperature_c=daily_body["temperature_2m_min"][i],
                precipitation_mm=daily_body["precipitation_sum"][i],
                precipitation_probability_pct=daily_body["precipitation_probability_max"][i],
                weather_code=daily_body["weather_code"][i],
            ) for i, day in enumerate(daily_body["time"])]
            hourly_body = body["hourly"]
            hourly = [WeatherHour(
                time=_as_utc(hour), temperature_c=hourly_body["temperature_2m"][i],
                relative_humidity_pct=hourly_body["relative_humidity_2m"][i],
                precipitation_probability_pct=hourly_body["precipitation_probability"][i],
            ) for i, hour in enumerate(hourly_body["time"][:24])]
            now = datetime.now(timezone.utc)
            return WeatherResult(latitude=latitude, longitude=longitude, source="LIVE", provider="Open-Meteo", current=current, daily=daily, hourly=hourly, agricultural_indicators=agricultural_indicators(current, daily), fetched_at=now, last_updated=current.observed_at, stale=False)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise WeatherProviderError("weather_provider_unavailable") from exc
