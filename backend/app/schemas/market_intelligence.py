"""Inputs and bounded outputs for estimated mandi returns and AI trend context."""

import re
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import SourceInfo
from app.schemas.enums import Language
from app.schemas.market import MarketPrice


class MarketLocation(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class MarketCostAssumptions(BaseModel):
    """Editable costs; all money is INR and quantity is in quintals."""

    model_config = ConfigDict(allow_inf_nan=False)

    transport_inr_per_km: Decimal = Field(
        default=Decimal("15"), ge=0, max_digits=14, decimal_places=2
    )
    loading_inr_per_quintal: Decimal = Field(
        default=Decimal("50"), ge=0, max_digits=14, decimal_places=2
    )
    commission_fraction: Decimal = Field(
        default=Decimal("0.02"), ge=0, le=1, max_digits=7, decimal_places=6
    )
    spoilage_fraction: Decimal = Field(
        default=Decimal("0"), ge=0, le=1, max_digits=7, decimal_places=6
    )
    storage_days: int = Field(default=0, ge=0, le=365)
    storage_inr_per_day: Decimal = Field(
        default=Decimal("100"), ge=0, max_digits=14, decimal_places=2
    )


class MarketDistanceOverride(BaseModel):
    mandi_id: UUID
    one_way_km: Decimal = Field(ge=0, le=20000, max_digits=10, decimal_places=3)


class MarketGuidanceInput(BaseModel):
    """MarketService supplies normalized observations; the agent performs no reads."""

    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    commodity_id: UUID
    variety_code: str | None = Field(default=None, min_length=1, max_length=120)
    grade: str | None = Field(default=None, min_length=1, max_length=80)
    quantity_quintals: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    location: MarketLocation
    prices: list[MarketPrice] = Field(max_length=100)
    history: list[MarketPrice] = Field(default_factory=list, max_length=1000)
    costs: MarketCostAssumptions = Field(default_factory=MarketCostAssumptions)
    distance_overrides: list[MarketDistanceOverride] = Field(default_factory=list, max_length=100)
    language: Language = Language.ENGLISH

    @model_validator(mode="after")
    def unique_distance_overrides(self) -> "MarketGuidanceInput":
        ids = [item.mandi_id for item in self.distance_overrides]
        if len(ids) != len(set(ids)):
            raise ValueError("Only one distance override is allowed per mandi")
        return self


class MarketTrend(BaseModel):
    """The only accepted Gemini output; it contains no prices or arithmetic."""

    model_config = ConfigDict(
        extra="forbid", strict=True, str_strip_whitespace=True, allow_inf_nan=False
    )

    trend: Literal["RISING", "STABLE", "FALLING"]
    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str = Field(min_length=1, max_length=240)
    forecast_horizon: Literal["7 calendar days"]

    @field_validator("reasoning_summary")
    @classmethod
    def reject_guarantees_and_amounts(cls, value: str) -> str:
        if re.search(
            r"₹|\b(?:INR|Rs\.?|guaranteed?|certain(?:ly)?|definite(?:ly)?|"
            r"assured|risk.free|gross|net return|profit|revenue)\b",
            value,
            re.IGNORECASE,
        ):
            raise ValueError("Trend reasoning must not include money totals or guarantees")
        return value


class ExcludedMandi(BaseModel):
    mandi_id: UUID | None = None
    market_name: str
    reason: Literal[
        "stale_price", "incomparable_series", "missing_mandi_id", "missing_distance"
    ]


class MarketRanking(BaseModel):
    rank: int = Field(ge=1)
    mandi_id: UUID
    market_name: str
    price_per_quintal: Decimal
    price_date: date
    distance_km: float = Field(ge=0)
    distance_method: Literal["haversine", "override"]
    gross_revenue: Decimal
    transport_cost: Decimal
    loading_cost: Decimal
    commission: Decimal
    spoilage_loss: Decimal
    storage_cost: Decimal
    net_return: Decimal
    return_per_quintal: Decimal
    trend: MarketTrend | None = None


class MarketGuidanceResult(BaseModel):
    status: Literal["complete", "partial", "needs_input", "unavailable"]
    agent: Literal["market_intelligence"] = "market_intelligence"
    schema_version: Literal["1"] = "1"
    quantity_quintals: Decimal
    variety_code: str | None = None
    grade: str | None = None
    rankings: list[MarketRanking] = Field(default_factory=list)
    assumptions: MarketCostAssumptions
    excluded_markets: list[ExcludedMandi] = Field(default_factory=list)
    sources: list[SourceInfo] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    model_used: str | None = None
    prompt_version: Literal["market-trend-v1"] = "market-trend-v1"
    disclaimer: str = (
        "Estimated returns use observed mandi prices and stated cost assumptions. "
        "Trend estimates are uncertain; actual prices and returns may differ. "
        "Use this as decision support, not a guaranteed financial outcome."
    )
