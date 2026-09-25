"""Validated application settings loaded from environment or backend/.env."""

from functools import lru_cache
from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AgriVision AI API"
    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_mode: Literal["live", "demo"] = "live"
    debug: bool = Field(default=False, validation_alias="AGRIVISION_DEBUG")
    cors_origins: str = "http://localhost:5173"

    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_key: SecretStr | None = None
    http_timeout_seconds: float = Field(default=10, gt=0, le=60)
    data_gov_api_key: SecretStr | None = None
    data_gov_resource_id: str | None = None
    market_csv_path: Path = BACKEND_DIR / "data" / "market_prices.csv"
    firebase_project_id: str | None = None
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: float = Field(default=15, gt=0, le=60)

    default_language: Literal["en", "te"] = "en"
    alert_radius_km: float = Field(default=10, gt=0, le=50)
    outbreak_risk_threshold: float = Field(default=0.6, ge=0, le=1)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("CORS_ORIGINS must include at least one allowed origin")
        if "*" in origins:
            raise ValueError("Wildcard CORS origins are not allowed")
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError(f"Invalid CORS origin: {origin}")
            if parsed.username or parsed.password:
                raise ValueError("CORS origins cannot contain credentials")
            parsed.port  # Reject invalid port values.
            if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                raise ValueError(f"CORS entries must be origins without a path: {origin}")
        return ",".join(dict.fromkeys(origin.rstrip("/") for origin in origins))

    @field_validator("supabase_url")
    @classmethod
    def normalize_supabase_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().rstrip("/")
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("SUPABASE_URL must be an http(s) URL")
        if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise ValueError("SUPABASE_URL must be a project origin without credentials or a path")
        parsed.port
        return normalized

    @field_validator("supabase_anon_key", "supabase_service_key", mode="before")
    @classmethod
    def empty_secret_is_unconfigured(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("data_gov_api_key", "gemini_api_key", mode="before")
    @classmethod
    def empty_data_gov_key(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("data_gov_resource_id")
    @classmethod
    def normalize_resource_id(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from uuid import UUID

        try:
            return str(UUID(value.strip()))
        except ValueError as exc:
            raise ValueError("DATA_GOV_RESOURCE_ID must be a UUID") from exc

    @field_validator("firebase_project_id")
    @classmethod
    def normalize_firebase_project_id(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return value.strip()

    @field_validator("gemini_model")
    @classmethod
    def validate_gemini_model(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
            raise ValueError("GEMINI_MODEL must be a model ID")
        return value

    @model_validator(mode="after")
    def validate_supabase_configuration(self) -> "Settings":
        provided = (
            self.supabase_url is not None,
            self.supabase_anon_key is not None,
            self.supabase_service_key is not None,
        )
        if any(provided) and not all(provided):
            raise ValueError(
                "SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_KEY "
                "must be configured together"
            )
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return self.cors_origins.split(",")

    @property
    def supabase_configured(self) -> bool:
        return all(
            (self.supabase_url, self.supabase_anon_key, self.supabase_service_key)
        )

    @property
    def data_gov_configured(self) -> bool:
        return bool(self.data_gov_api_key and self.data_gov_resource_id)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
