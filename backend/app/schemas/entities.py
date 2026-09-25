"""Initial validated payload and row shapes for the Supabase domain tables."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_serializer, field_validator, model_validator

from app.schemas.common import DatabaseModel
from app.schemas.enums import (
    AlertLevel,
    AlertStatus,
    AlertType,
    AnalysisState,
    CropStatus,
    IrrigationType,
    JobType,
    Language,
    NotificationType,
    PhosphorusBasis,
    PotassiumBasis,
    RecommendationType,
    ReviewStatus,
    Season,
    Severity,
    SoilType,
    JobStatus,
)


class Coordinates(DatabaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class FarmerProfile(DatabaseModel):
    id: UUID
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    language: Language = Language.ENGLISH
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    district: str | None = None
    state: str | None = None
    location_source: str | None = None
    location_updated_at: datetime | None = None
    alerts_opt_in: bool = False
    created_at: datetime
    updated_at: datetime


class FarmCreate(DatabaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    farm_name: str = Field(min_length=1, max_length=120)
    area_acres: Decimal = Field(gt=0, le=1000, max_digits=10, decimal_places=2)
    budget_inr: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    irrigation_type: IrrigationType
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    address: str | None = Field(default=None, max_length=500)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)

    @field_serializer("area_acres", when_used="json")
    def serialize_area_acres(self, value: Decimal) -> float:
        return float(value)

    @field_validator("farm_name")
    @classmethod
    def strip_farm_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("farm_name cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> "FarmCreate":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self


class FarmRecord(FarmCreate):
    id: UUID
    farmer_id: UUID
    created_at: datetime
    updated_at: datetime


class CropCreate(DatabaseModel):
    farm_id: UUID
    commodity_id: UUID
    variety: str | None = Field(default=None, max_length=120)
    season: Season
    sowing_date: date | None = None
    expected_harvest: date | None = None
    growth_stage: str | None = Field(default=None, max_length=80)
    status: CropStatus = CropStatus.ACTIVE

    @model_validator(mode="after")
    def validate_harvest_date(self) -> "CropCreate":
        if (
            self.sowing_date is not None
            and self.expected_harvest is not None
            and self.expected_harvest < self.sowing_date
        ):
            raise ValueError("expected_harvest must not precede sowing_date")
        return self


class CropRecord(CropCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


MicronutrientName = Literal[
    "iron", "zinc", "manganese", "copper", "boron", "molybdenum", "chloride"
]
MicronutrientLevel = Annotated[
    Decimal, Field(ge=0, le=10000, max_digits=8, decimal_places=3)
]


class SoilTestCreate(DatabaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    ph: float | None = Field(default=None, ge=3, le=10)
    nitrogen_kg_ha: float | None = Field(default=None, ge=0, le=500)
    phosphorus_kg_ha: float | None = Field(default=None, ge=0, le=200)
    potassium_kg_ha: float | None = Field(default=None, ge=0, le=500)
    micronutrients_mg_kg: dict[MicronutrientName, MicronutrientLevel] = Field(
        default_factory=dict, max_length=7
    )
    phosphorus_basis: PhosphorusBasis = PhosphorusBasis.UNKNOWN
    potassium_basis: PotassiumBasis = PotassiumBasis.UNKNOWN
    organic_carbon_pct: float | None = Field(default=None, ge=0, le=5)
    soil_type: SoilType | None = None
    previous_commodity_id: UUID | None = None
    test_date: date
    lab_name: str | None = Field(default=None, max_length=160)
    method: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_test_date(self) -> "SoilTestCreate":
        if self.test_date > date.today():
            raise ValueError("test_date cannot be in the future")
        return self


class SoilTestRecord(SoilTestCreate):
    id: UUID
    farm_id: UUID
    created_at: datetime


class ReportDraftCreate(DatabaseModel):
    client_request_id: UUID
    description: str | None = Field(default=None, max_length=4000)
    voice_transcript: str | None = Field(default=None, max_length=4000)
    crop_id: UUID | None = None
    commodity_id: UUID | None = None
    language: Language = Language.ENGLISH
    location: Coordinates | None = None
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)


class ReportRecord(DatabaseModel):
    id: UUID
    farmer_id: UUID
    client_request_id: UUID
    crop_id: UUID | None = None
    commodity_id: UUID | None = None
    description: str | None = None
    voice_transcript: str | None = None
    language: Language
    image_path: str | None = None
    image_checksum: str | None = None
    image_state: str = "none"
    latitude: float | None = None
    longitude: float | None = None
    district: str | None = None
    state: str | None = None
    analysis_state: AnalysisState = AnalysisState.DRAFT
    review_status: ReviewStatus = ReviewStatus.PENDING
    ai_diagnosis: dict[str, Any] | None = None
    diagnosis_schema_version: str | None = None
    disease_code: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    severity: Severity | None = None
    model_used: str | None = None
    prompt_version: str | None = None
    weather_context: dict[str, Any] | None = None
    analysis_error_code: str | None = None
    analysis_attempt: int = Field(default=0, ge=0)
    analyzed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CommodityRecord(DatabaseModel):
    id: UUID
    code: str
    name_en: str
    name_te: str | None = None
    provider_aliases: dict[str, Any] = Field(default_factory=dict)


class MandiRecord(DatabaseModel):
    id: UUID
    provider_key: str
    market_name: str
    district: str | None = None
    state: str
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    coordinate_source: str | None = None


class MarketPriceRecord(DatabaseModel):
    id: UUID
    mandi_id: UUID
    commodity_id: UUID
    variety_code: str = "unspecified"
    grade: str = "unspecified"
    min_price: Decimal = Field(ge=0)
    max_price: Decimal = Field(ge=0)
    modal_price: Decimal = Field(ge=0)
    currency: str = "INR"
    unit: str = "quintal"
    price_date: date
    source: str
    source_record_id: str | None = None
    fetched_at: datetime
    original_unit: str | None = None

    @model_validator(mode="after")
    def validate_price_order(self) -> "MarketPriceRecord":
        if not self.min_price <= self.modal_price <= self.max_price:
            raise ValueError("prices must satisfy min_price <= modal_price <= max_price")
        return self


class RecommendationRecord(DatabaseModel):
    id: UUID
    farmer_id: UUID
    farm_id: UUID | None = None
    crop_id: UUID | None = None
    soil_test_id: UUID | None = None
    client_request_id: UUID
    type: RecommendationType
    input_context: dict[str, Any] = Field(default_factory=dict)
    recommendation: dict[str, Any]
    schema_version: str = "1"
    sources: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    model_used: str | None = None
    rule_version: str | None = None
    created_at: datetime


class AlertRecord(DatabaseModel):
    id: UUID
    source_report_id: UUID | None = None
    commodity_id: UUID | None = None
    disease_code: str | None = None
    alert_type: AlertType
    severity: Severity
    risk_score: float = Field(ge=0, le=1)
    level: AlertLevel
    center_lat: float = Field(ge=-90, le=90)
    center_lng: float = Field(ge=-180, le=180)
    radius_km: Decimal = Field(gt=0, le=500)
    affected_farmer_count: int = Field(ge=0)
    status: AlertStatus
    weather_context: dict[str, Any] | None = None
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    rule_version: str
    revision: int = Field(ge=1)
    last_evidence_at: datetime
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


class NotificationRecord(DatabaseModel):
    id: UUID
    farmer_id: UUID
    alert_id: UUID | None = None
    alert_revision: int | None = None
    title: str
    body: str
    language: Language
    type: NotificationType
    destination_path: str | None = None
    dedupe_key: str
    read_at: datetime | None = None
    created_at: datetime


class JobRecord(DatabaseModel):
    id: UUID
    type: JobType
    resource_id: UUID | None = None
    dedupe_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: JobStatus
    attempts: int = Field(ge=0)
    max_attempts: int = Field(gt=0)
    run_after: datetime
    locked_until: datetime | None = None
    last_error_code: str | None = None
    created_at: datetime
    updated_at: datetime
