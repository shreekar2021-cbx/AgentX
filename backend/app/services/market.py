import json
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path

from app.core.config import Settings
from app.providers.ogd_market import MarketProviderError, OGDMarketProvider
from app.repositories.phase3 import Phase3LocalRepository
from app.schemas.phase3 import MarketEstimate, MarketEstimateInput, MarketHistoryPoint, MarketQuote, MarketResponse
from app.services.location import haversine_km


DATASET_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "market_demo.json"


@lru_cache(maxsize=1)
def demo_records() -> list[dict]:
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    if not data["metadata"]["is_synthetic"]:
        raise ValueError("Fallback market dataset must be synthetic")
    return data["records"]


def _history(quotes: list[MarketQuote], days: int) -> list[MarketHistoryPoint]:
    if not quotes:
        return []
    newest = max(item.date for item in quotes)
    groups: dict[date, list[float]] = defaultdict(list)
    for item in quotes:
        if (newest - item.date).days < days:
            groups[item.date].append(item.modal_price)
    return [MarketHistoryPoint(date=day, modal_price=round(sum(values) / len(values), 2), sample_count=len(values)) for day, values in sorted(groups.items())]


def _latest(quotes: list[MarketQuote], latitude: float | None, longitude: float | None) -> list[MarketQuote]:
    by_mandi: dict[tuple[str, str], MarketQuote] = {}
    for quote in sorted(quotes, key=lambda item: item.date, reverse=True):
        key = (quote.mandi.casefold(), quote.variety.casefold())
        if key not in by_mandi:
            if latitude is not None and longitude is not None and quote.latitude is not None and quote.longitude is not None:
                quote = quote.model_copy(update={"distance_km": round(haversine_km(latitude, longitude, quote.latitude, quote.longitude), 1)})
            by_mandi[key] = quote
    return sorted(by_mandi.values(), key=lambda item: (item.distance_km if item.distance_km is not None else 1e9, item.mandi))


def compose_market(commodity: str, district: str | None, quotes: list[MarketQuote], source: str, stale: bool, latitude: float | None, longitude: float | None, fetched_at: datetime | None) -> MarketResponse:
    selected = [item.model_copy(update={"source": source}) for item in quotes if item.commodity.casefold() == commodity.casefold() and (not district or district.casefold() == "all" or item.district.casefold() == district.casefold())]
    newest = max((item.date for item in selected), default=None)
    synthetic = bool(selected) and all(item.is_synthetic for item in selected)
    provenance = selected[0].provenance if selected else "No matching market records available"
    return MarketResponse(commodity=commodity, district=district if district and district.casefold() != "all" else None, source=source, is_synthetic=synthetic, stale=stale, fetched_at=fetched_at, last_updated=newest, provenance=provenance, quotes=_latest(selected, latitude, longitude), history_7d=_history(selected, 7), history_30d=_history(selected, 30))


class MarketService:
    def __init__(self, settings: Settings, provider: OGDMarketProvider, repository: Phase3LocalRepository) -> None:
        self.settings = settings
        self.provider = provider
        self.repository = repository

    async def get(self, commodity: str, district: str | None = None, latitude: float | None = None, longitude: float | None = None) -> MarketResponse:
        key = f"market:{commodity.casefold()}"
        fresh = await self.repository.market_cache_get(key)
        if fresh:
            quotes = [MarketQuote.model_validate(item) for item in fresh[0]["quotes"]]
            await self.repository.record_provider("market", "Cached")
            return compose_market(commodity, district, quotes, "CACHED", False, latitude, longitude, datetime.fromisoformat(fresh[0]["fetched_at"]))
        try:
            quotes = await self.provider.quotes(commodity)
            fetched_at = datetime.now(timezone.utc)
            await self.repository.market_cache_put(key, {"quotes": [item.model_dump(mode="json") for item in quotes], "fetched_at": fetched_at.isoformat()}, self.settings.market_cache_minutes)
            await self.repository.record_provider("market", "Healthy")
            return compose_market(commodity, district, quotes, "LIVE", False, latitude, longitude, fetched_at)
        except MarketProviderError:
            stale = await self.repository.market_cache_get(key, allow_stale=True)
            if stale:
                quotes = [MarketQuote.model_validate(item) for item in stale[0]["quotes"]]
                await self.repository.record_provider("market", "Cached", "Provider unavailable; old market cache returned")
                return compose_market(commodity, district, quotes, "CACHED", True, latitude, longitude, datetime.fromisoformat(stale[0]["fetched_at"]))
            quotes = [MarketQuote.model_validate(item) for item in demo_records() if item["commodity"].casefold() == commodity.casefold()]
            await self.repository.record_provider("market", "Fallback", "Dated synthetic market examples")
            return compose_market(commodity, district, quotes, "FALLBACK", True, latitude, longitude, None)


def estimate_return(values: MarketEstimateInput) -> MarketEstimate:
    money = lambda amount: amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gross = money(values.quantity_quintals * values.modal_price_per_quintal)
    transport = money(values.distance_km * values.transport_cost_per_km)
    handling = money(values.quantity_quintals * values.handling_cost_per_quintal)
    storage = money(values.storage_cost)
    spoilage = money(gross * values.spoilage_percent / Decimal(100))
    total = transport + handling + storage + spoilage
    return MarketEstimate(quantity_quintals=values.quantity_quintals, gross_revenue=gross, transport_cost=transport, handling_cost=handling, storage_cost=storage, estimated_spoilage=spoilage, total_cost=money(total), estimated_net_return=money(gross - total))
