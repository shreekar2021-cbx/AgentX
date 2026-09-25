from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: Literal["development", "test", "production"] = "development"
    demo_mode: bool = False
    app_log_level: str = "INFO"
    app_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    app_max_upload_mb: int = Field(default=10, ge=1, le=25)
    app_rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    mistral_api_key: str = ""
    mistral_model_general: str = "mistral-medium-latest"
    mistral_model_fast: str = "ministral-8b-latest"
    mistral_model_vision: str = "mistral-small-latest"
    mistral_timeout_seconds: float = Field(default=25, ge=5, le=90)
    mistral_max_retries: int = Field(default=2, ge=0, le=4)
    weather_timeout_seconds: float = Field(default=8, ge=2, le=30)
    weather_cache_minutes: int = Field(default=30, ge=5, le=180)
    nearby_radius_km: float = Field(default=10, ge=1, le=100)
    local_database_path: str = ".data/agrivision.sqlite3"
    app_seed_demo_data: bool = True
    analysis_rate_limit_per_hour: int = Field(default=12, ge=1, le=100)
    ogd_api_key: str = ""
    ogd_market_resource_id: str = "9ef84268-d588-465a-a308-a864a43d0070"
    market_cache_minutes: int = Field(default=60, ge=5, le=1440)
    market_timeout_seconds: float = Field(default=10, ge=2, le=30)
    market_trend_rate_limit_per_hour: int = Field(default=20, ge=1, le=200)

    @field_validator("app_cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def secure_production(self):
        if self.app_env == "production":
            if self.demo_mode:
                raise ValueError("DEMO_MODE must be false in production.")
            if any(origin == "*" or not origin.startswith("https://") for origin in self.app_cors_origins):
                raise ValueError("Production CORS origins must be explicit HTTPS origins.")
        return self

    @property
    def database_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def local_demo_mode(self) -> bool:
        return self.demo_mode and self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
