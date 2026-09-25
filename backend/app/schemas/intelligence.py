from datetime import datetime
from enum import StrEnum
from uuid import UUID
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIStatus(StrEnum):
    LIVE = "AI LIVE"
    CACHED = "AI CACHED"
    LOCAL_KNOWLEDGE = "LOCAL KNOWLEDGE"
    LIMITED = "LIMITED MODE"


class Severity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class SpreadPotential(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class CropHealthFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    possible_problem: str = Field(min_length=3, max_length=160)
    confidence: float = Field(ge=0, le=1)
    severity: Severity
    symptoms: list[str] = Field(min_length=1, max_length=8)
    possible_causes: list[str] = Field(min_length=1, max_length=6)
    immediate_actions: list[str] = Field(min_length=1, max_length=8)
    precautions: list[str] = Field(min_length=1, max_length=6)
    monitoring: list[str] = Field(min_length=1, max_length=6)
    expert_verification: str = Field(min_length=5, max_length=500)
    spread_potential: SpreadPotential

    @field_validator("symptoms", "possible_causes", "immediate_actions", "precautions", "monitoring")
    @classmethod
    def check_guidance(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values]
        if any(not 3 <= len(item) <= 300 for item in cleaned):
            raise ValueError("Guidance items must be 3 to 300 characters.")
        unsafe = re.compile(r"https?://|<[^>]+>|\b(?:ignore (?:all |previous )?instructions|system prompt)\b|\b\d+(?:\.\d+)?\s*(?:mg|g|kg|ml|l)\s*(?:/|per)\s*(?:l|litre|liter|acre|hectare|ha)\b", re.I)
        if any(unsafe.search(item) for item in cleaned):
            raise ValueError("Unsafe or untrusted guidance text.")
        return cleaned


class CropHealthResult(BaseModel):
    finding: CropHealthFinding
    source: AIStatus
    model: str | None = None
    image_assessed: bool = False
    knowledge_ref: str | None = None
    analyzed_at: datetime
    limitation: str | None = None


class WeatherCurrent(BaseModel):
    temperature_c: float
    relative_humidity_pct: float = Field(ge=0, le=100)
    precipitation_mm: float = Field(ge=0)
    wind_speed_kmh: float = Field(ge=0)
    weather_code: int
    observed_at: datetime


class WeatherDay(BaseModel):
    date: str
    max_temperature_c: float
    min_temperature_c: float
    precipitation_mm: float = Field(ge=0)
    precipitation_probability_pct: float = Field(ge=0, le=100)
    weather_code: int


class WeatherHour(BaseModel):
    time: datetime
    temperature_c: float
    relative_humidity_pct: float = Field(ge=0, le=100)
    precipitation_probability_pct: float = Field(ge=0, le=100)


class WeatherResult(BaseModel):
    latitude: float
    longitude: float
    source: str
    provider: str | None = None
    current: WeatherCurrent | None = None
    daily: list[WeatherDay] = Field(default_factory=list)
    hourly: list[WeatherHour] = Field(default_factory=list)
    agricultural_indicators: list[str] = Field(default_factory=list)
    fetched_at: datetime | None = None
    last_updated: datetime | None = None
    stale: bool = False
    is_synthetic: bool = False


class NearbyMatch(BaseModel):
    report_id: UUID
    owner_id: str
    crop: str
    possible_problem: str
    severity: Severity
    distance_km: float
    age_hours: float
    is_synthetic: bool


class RiskResult(BaseModel):
    individual_risk: int = Field(ge=0, le=100)
    community_risk: int = Field(ge=0, le=100)
    risk_factors: list[str]
    recommended_monitoring: list[str]


class OutbreakResult(BaseModel):
    nearby_alert: bool
    alert_reason: str
    cluster_size: int = Field(ge=0)
    risk_radius_km: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    evidence_is_synthetic: bool = False


class ReportPublic(BaseModel):
    id: UUID
    crop: str
    field: str
    district: str
    symptom_description: str
    notes: str | None = None
    latitude: float
    longitude: float
    status: str
    stage: str
    created_at: datetime
    is_synthetic: bool
    image_url: str | None = None
    crop_health: CropHealthResult | None = None
    weather: WeatherResult | None = None
    risk: RiskResult | None = None
    outbreak: OutbreakResult | None = None
    nearby_count: int = 0
    nearby_synthetic_count: int = 0


class NearbyAlertPublic(BaseModel):
    id: str
    crop: str
    possible_problem: str
    district: str
    severity: Severity
    cluster_size: int
    distance_km: float
    risk_radius_km: float
    latitude: float
    longitude: float
    observed_at: datetime
    is_synthetic: bool


class AnalysisProgress(BaseModel):
    stage: str
    status: str
    report: ReportPublic | None = None
    message: str | None = None
