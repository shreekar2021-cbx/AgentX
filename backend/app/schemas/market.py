"""One price shape for AGMARKNET, Supabase, and local CSV."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


def market_today() -> date:
    """AGMARKNET reports Indian market dates, even when the API host runs in UTC."""
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


class MarketQuery(BaseModel):
    commodity_id: UUID
    state: str = Field(min_length=1, max_length=120)
    district: str | None = Field(default=None, min_length=1, max_length=120)
    variety: str | None = Field(default=None, min_length=1, max_length=120)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)

    @field_validator("state", "district", "variety")
    @classmethod
    def strip_filter(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Filter cannot be blank")
        return value.strip() if value is not None else None


class CommodityIdentity(BaseModel):
    id: UUID
    code: str
    name_en: str
    provider_aliases: dict[str, list[str]] = Field(default_factory=dict)

    @property
    def data_gov_names(self) -> list[str]:
        return self.provider_aliases.get("data.gov.in") or [self.name_en]


class MarketCommodity(BaseModel):
    id: UUID
    code: str
    name_en: str


class MarketPrice(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    commodity_id: UUID
    commodity_code: str
    mandi_id: UUID | None = None
    mandi_latitude: float | None = Field(default=None, ge=-90, le=90)
    mandi_longitude: float | None = Field(default=None, ge=-180, le=180)
    provider_key: str
    market_name: str
    district: str | None = None
    state: str
    variety_code: str = "unspecified"
    grade: str = "unspecified"
    min_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    max_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    modal_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    currency: Literal["INR"] = "INR"
    unit: Literal["quintal"] = "quintal"
    price_date: date
    source: str
    source_record_id: str | None = None
    fetched_at: AwareDatetime
    original_unit: str | None = None

    @model_validator(mode="after")
    def validate_price(self) -> "MarketPrice":
        if not self.min_price <= self.modal_price <= self.max_price:
            raise ValueError("Prices must satisfy min <= modal <= max")
        if self.price_date > market_today():
            raise ValueError("Price date cannot be in the future")
        if not all((self.commodity_code.strip(), self.provider_key.strip(),
                    self.market_name.strip(), self.state.strip(), self.source.strip())):
            raise ValueError("Market identity and source are required")
        if (self.mandi_latitude is None) != (self.mandi_longitude is None):
            raise ValueError("Mandi latitude and longitude must be supplied together")
        return self

    @property
    def stale_by_date(self) -> bool:
        return (market_today() - self.price_date).days > 7


class MarketPriceView(MarketPrice):
    is_stale: bool

    @classmethod
    def from_price(cls, price: MarketPrice) -> "MarketPriceView":
        return cls(**price.model_dump(), is_stale=price.stale_by_date)


class MarketPricesResult(BaseModel):
    source_status: Literal["LIVE", "CACHED", "FALLBACK"]
    prices: list[MarketPriceView]
    as_of: date
    is_stale: bool
    next_cursor: str | None = None


class MarketHistoryResult(BaseModel):
    source_status: Literal["CACHED", "FALLBACK"]
    days: int = Field(ge=1, le=365)
    prices: list[MarketPriceView]
    as_of: date | None = None
