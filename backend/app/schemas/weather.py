"""Application-owned weather units, freshness, and cache contracts."""

from datetime import date, timedelta
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import ApiWarning


class WeatherModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class WeatherLocation(WeatherModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    def cache_location(self) -> "WeatherLocation":
        # Share non-personal weather by ~1 km coordinates, not exact farm positions.
        return WeatherLocation(
            latitude=round(self.latitude, 2) or 0.0,
            longitude=round(self.longitude, 2) or 0.0,
        )

    @property
    def cache_key(self) -> str:
        return f"weather:v1:{self.latitude:.2f}:{self.longitude:.2f}:UTC"


class CurrentWeather(WeatherModel):
    observed_at: AwareDatetime
    temperature_c: float
    humidity_pct: float = Field(ge=0, le=100)
    rain_mm: float = Field(ge=0)
    wind_kmh: float = Field(ge=0)
    interval_seconds: int = Field(gt=0)
    measurement_kind: Literal["model_estimate"] = "model_estimate"


class DailyForecast(WeatherModel):
    date: date
    temperature_min_c: float
    temperature_max_c: float
    rain_mm: float = Field(ge=0)
    wind_max_kmh: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_temperature_range(self) -> "DailyForecast":
        if self.temperature_min_c > self.temperature_max_c:
            raise ValueError("Minimum temperature exceeds maximum")
        return self


class WeatherData(WeatherModel):
    location: WeatherLocation
    timezone: Literal["UTC"] = "UTC"
    current: CurrentWeather
    forecast_7day: list[DailyForecast] = Field(min_length=7, max_length=7)
    # Forecast rain and model estimates are not observed historical rainfall.
    recent_observed_rain_48h_mm: None = None

    @model_validator(mode="after")
    def validate_forecast_dates(self) -> "WeatherData":
        dates = [day.date for day in self.forecast_7day]
        if dates != [dates[0] + timedelta(days=i) for i in range(7)]:
            raise ValueError("Forecast must contain seven consecutive days")
        return self


class WeatherSnapshot(BaseModel):
    data: WeatherData
    fetched_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def validate_expiry(self) -> "WeatherSnapshot":
        if self.expires_at <= self.fetched_at:
            raise ValueError("Cache expiry must follow fetch time")
        return self


class WeatherSourceResult(BaseModel):
    status: Literal["live", "cached", "unavailable"]
    data: WeatherData | None = None
    provider: Literal["open-meteo"] = "open-meteo"
    observed_at: AwareDatetime | None = None
    fetched_at: AwareDatetime | None = None
    expires_at: AwareDatetime | None = None
    is_stale: bool = False
    warnings: list[ApiWarning] = Field(default_factory=list)
