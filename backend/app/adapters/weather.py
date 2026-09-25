"""Open-Meteo forecast adapter; retry policy lives only at this boundary."""

import asyncio
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import math
import random
import time

import httpx
from pydantic import ValidationError

from app.schemas.common import ApiWarning
from app.schemas.weather import (
    CurrentWeather, DailyForecast, WeatherData, WeatherLocation, WeatherSourceResult,
)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FRESH_FOR = timedelta(minutes=30)
STALE_LIMIT = timedelta(hours=24)


class OpenMeteoAdapter:
    def __init__(
        self, client: httpx.AsyncClient, *, timeout_seconds: float = 5,
        operation_budget_seconds: float = 12,
    ) -> None:
        self._client = client
        self._timeout = timeout_seconds
        self._budget = operation_budget_seconds

    async def get_weather(self, location: WeatherLocation) -> WeatherSourceResult:
        params = {
            "latitude": location.latitude, "longitude": location.longitude,
            "current": "temperature_2m,relative_humidity_2m,rain,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,rain_sum,wind_speed_10m_max",
            "temperature_unit": "celsius", "wind_speed_unit": "kmh",
            "precipitation_unit": "mm", "timezone": "UTC", "forecast_days": 7,
        }
        deadline = time.monotonic() + self._budget
        code = "weather_unavailable"
        for attempt in range(2):  # One initial attempt, at most one retry.
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            retry_after = None
            retryable = True
            try:
                # Enforce a whole-attempt deadline as well as HTTPX phase timeouts.
                async with asyncio.timeout(min(self._timeout, remaining)):
                    response = await self._client.get(
                        FORECAST_URL, params=params, timeout=min(self._timeout, remaining)
                    )
                if response.is_success:
                    now = datetime.now(timezone.utc)
                    data = self._normalize(response.json(), location, now)
                    return WeatherSourceResult(
                        status="live", data=data, observed_at=data.current.observed_at,
                        fetched_at=now, expires_at=now + FRESH_FOR,
                    )
                retryable = response.status_code in {429, 500, 502, 503, 504}
                code = "weather_rate_limited" if response.status_code == 429 else "weather_provider_error"
                retry_after = self._retry_after(response.headers.get("Retry-After"))
            except (TimeoutError, httpx.TimeoutException):
                code = "weather_timeout"
            except httpx.TransportError:
                code = "weather_network_error"
            except httpx.RequestError:
                code, retryable = "weather_invalid_response", False
            except (ValueError, KeyError, TypeError, ValidationError):
                # Invalid JSON, units, times, or incomplete data are not transient failures.
                code, retryable = "weather_invalid_response", False

            if not retryable or attempt == 1:
                break
            delay = max(0.25 * (2 ** attempt) + random.uniform(0, 0.1), retry_after or 0)
            # Never shorten Retry-After to fit the deadline; use the cache instead.
            if delay + self._timeout > deadline - time.monotonic():
                break
            await asyncio.sleep(delay)

        return WeatherSourceResult(status="unavailable", warnings=[ApiWarning(
            code=code, message="Open-Meteo could not provide usable weather data."
        )])

    @staticmethod
    def _retry_after(value: str | None) -> float | None:
        if not value:
            return None
        try:
            seconds = float(value)
        except ValueError:
            try:
                when = parsedate_to_datetime(value)
                seconds = (when - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                return None
        return max(0, seconds) if math.isfinite(seconds) else None

    @staticmethod
    def _normalize(payload: dict, location: WeatherLocation, now: datetime) -> WeatherData:
        if not isinstance(payload, dict) or any(
            not isinstance(payload.get(section), dict)
            for section in ("current", "daily", "current_units", "daily_units")
        ):
            raise ValueError("Invalid provider response structure")
        if payload.get("error") or payload["utc_offset_seconds"] != 0:
            raise ValueError("Invalid provider result or timezone")
        expected_units = {
            "current_units": {"time": "iso8601", "interval": "seconds", "temperature_2m": "°C",
                              "relative_humidity_2m": "%", "rain": "mm", "wind_speed_10m": "km/h"},
            "daily_units": {"time": "iso8601", "temperature_2m_min": "°C", "temperature_2m_max": "°C",
                            "rain_sum": "mm", "wind_speed_10m_max": "km/h"},
        }
        for section, units in expected_units.items():
            if any(payload[section].get(field) != unit for field, unit in units.items()):
                raise ValueError("Unexpected provider units")
        current, daily = payload["current"], payload["daily"]
        observed_at = datetime.fromisoformat(current["time"])
        if observed_at.tzinfo is None:  # We explicitly requested UTC.
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        if not timedelta(minutes=-10) <= now - observed_at <= timedelta(hours=2):
            raise ValueError("Provider current timestamp is out of range")
        fields = ("time", "temperature_2m_min", "temperature_2m_max", "rain_sum", "wind_speed_10m_max")
        if any(not isinstance(daily[field], list) or len(daily[field]) != 7 for field in fields):
            raise ValueError("Incomplete seven-day forecast")
        data = WeatherData(
            location=location,
            current=CurrentWeather(
                observed_at=observed_at, temperature_c=current["temperature_2m"],
                humidity_pct=current["relative_humidity_2m"], rain_mm=current["rain"],
                wind_kmh=current["wind_speed_10m"], interval_seconds=current["interval"],
            ),
            forecast_7day=[DailyForecast(
                date=daily["time"][i], temperature_min_c=daily["temperature_2m_min"][i],
                temperature_max_c=daily["temperature_2m_max"][i], rain_mm=daily["rain_sum"][i],
                wind_max_kmh=daily["wind_speed_10m_max"][i],
            ) for i in range(7)],
        )
        if data.forecast_7day[0].date != observed_at.date():
            raise ValueError("Forecast dates do not match current conditions")
        return data
