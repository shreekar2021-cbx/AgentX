from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FarmProfileInput(BaseModel):
    farm_name: str | None = Field(default=None, max_length=120)
    village: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_acres: float | None = Field(default=None, gt=0, le=100000)
    crop: str | None = Field(default=None, max_length=80)
    season: str | None = Field(default=None, max_length=40)
    soil_type: str | None = Field(default=None, max_length=80)
    soil_ph: float | None = Field(default=None, ge=0, le=14)
    nitrogen_kg_ha: float | None = Field(default=None, ge=0)
    phosphorus_kg_ha: float | None = Field(default=None, ge=0)
    potassium_kg_ha: float | None = Field(default=None, ge=0)
    micronutrients: dict[str, float] = Field(default_factory=dict)
    lab_status: dict[str, Literal["low", "adequate", "high"]] = Field(default_factory=dict)
    previous_crop: str | None = Field(default=None, max_length=80)
    irrigation: str | None = Field(default=None, max_length=80)
    budget_inr: float | None = Field(default=None, ge=0)
    planting_date: date | None = None

    @model_validator(mode="after")
    def coordinates_together(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together.")
        return self


class FarmProfile(FarmProfileInput):
    updated_at: datetime
    is_synthetic: bool = False


class PortfolioInput(BaseModel):
    crop: str = Field(min_length=2, max_length=80)
    field: str = Field(min_length=1, max_length=120)
    planting_date: date | None = None
    area_acres: float | None = Field(default=None, gt=0, le=100000)
    season: str | None = Field(default=None, max_length=40)
    health_status: Literal["unknown", "healthy", "watch", "needs_attention"] = "unknown"
    next_action: str | None = Field(default=None, max_length=300)


class PortfolioCrop(PortfolioInput):
    id: UUID
    created_at: datetime
    updated_at: datetime
    latest_report_id: UUID | None = None
    latest_report_at: datetime | None = None
    latest_risk: int | None = None
    is_synthetic: bool = False


class NotificationPublic(BaseModel):
    id: UUID
    kind: str
    title: str
    body: str
    target_url: str | None = None
    created_at: datetime
    read_at: datetime | None = None
    is_synthetic: bool = False


class MarketQuote(BaseModel):
    commodity: str
    variety: str
    state: str
    district: str
    mandi: str
    min_price: float = Field(ge=0)
    max_price: float = Field(ge=0)
    modal_price: float = Field(ge=0)
    date: date
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float | None = None
    source: Literal["LIVE", "CACHED", "FALLBACK"]
    is_synthetic: bool
    provenance: str


class MarketHistoryPoint(BaseModel):
    date: date
    modal_price: float
    sample_count: int


class MarketResponse(BaseModel):
    commodity: str
    district: str | None = None
    source: Literal["LIVE", "CACHED", "FALLBACK"]
    is_synthetic: bool
    stale: bool
    fetched_at: datetime | None = None
    last_updated: date | None = None
    provenance: str
    quotes: list[MarketQuote]
    history_7d: list[MarketHistoryPoint]
    history_30d: list[MarketHistoryPoint]


class MarketTrend(BaseModel):
    trend: Literal["RISING", "STABLE", "FALLING", "UNAVAILABLE"]
    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str = Field(max_length=500)
    forecast_horizon: str = Field(max_length=120)
    source: Literal["AI LIVE", "AI CACHED", "DETERMINISTIC", "UNAVAILABLE"]
    is_synthetic: bool
    limitation: str


class MarketAIResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trend: Literal["RISING", "STABLE", "FALLING"]
    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str = Field(min_length=10, max_length=500)
    forecast_horizon: str = Field(min_length=3, max_length=120)


class MarketEstimateInput(BaseModel):
    quantity_quintals: Decimal = Field(ge=0)
    modal_price_per_quintal: Decimal = Field(ge=0)
    distance_km: Decimal = Field(ge=0)
    transport_cost_per_km: Decimal = Field(ge=0)
    handling_cost_per_quintal: Decimal = Field(ge=0)
    storage_cost: Decimal = Field(ge=0)
    spoilage_percent: Decimal = Field(ge=0, le=100)


class MarketEstimate(BaseModel):
    quantity_quintals: Decimal
    gross_revenue: Decimal
    transport_cost: Decimal
    handling_cost: Decimal
    storage_cost: Decimal
    estimated_spoilage: Decimal
    total_cost: Decimal
    estimated_net_return: Decimal
    note: str = "Estimate from farmer-entered inputs; actual sales and costs may differ."


class SeedRecommendation(BaseModel):
    crop: str | None
    suitability: Literal["potentially_suitable", "needs_review", "insufficient_data"]
    characteristics: list[str]
    considerations: list[str]
    missing_inputs: list[str]
    provenance: str
    is_product_recommendation: bool = False


class FertilizerRecommendation(BaseModel):
    nutrient_status: dict[str, str]
    possible_deficiencies: list[str]
    priorities: list[str]
    soil_considerations: list[str]
    general_direction: list[str]
    monitoring: list[str]
    missing_inputs: list[str]
    provenance: str
    exact_dose_provided: bool = False
