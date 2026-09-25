import hashlib
import json

from app.core.config import Settings
from app.providers.mistral import AIProviderError, MistralProvider
from app.repositories.phase3 import Phase3LocalRepository
from app.schemas.phase3 import MarketResponse, MarketTrend


class MarketIntelligenceAgent:
    def __init__(self, provider: MistralProvider, repository: Phase3LocalRepository, settings: Settings) -> None:
        self.provider = provider
        self.repository = repository
        self.settings = settings

    async def analyze(self, market: MarketResponse, owner_id: str | None = None) -> MarketTrend:
        history = market.history_30d
        if len(history) < 2:
            return MarketTrend(trend="UNAVAILABLE", confidence=0, reasoning_summary="At least two dated price observations are needed.", forecast_horizon="No forecast", source="UNAVAILABLE", is_synthetic=market.is_synthetic, limitation="Insufficient history; no price direction can be inferred.")
        context = {"commodity": market.commodity, "district": market.district, "is_synthetic": market.is_synthetic, "history": [{"date": str(item.date), "modal_price": item.modal_price, "sample_count": item.sample_count} for item in history]}
        key = "market-trend:" + hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
        cached = await self.repository.market_cache_get(key)
        if cached:
            await self.repository.record_provider("mistral", "Cached", "Market trend result cached")
            return MarketTrend.model_validate({**cached[0], "source": "AI CACHED"})
        try:
            if self.settings.mistral_api_key and owner_id and not await self.repository.claim_rate(owner_id, "market_trend", self.settings.market_trend_rate_limit_per_hour, 3600):
                raise AIProviderError("rate_limited")
            result = await self.provider.classify_market(context)
            trend = MarketTrend(**result.model_dump(), source="AI LIVE", is_synthetic=market.is_synthetic, limitation="Direction summarizes recent observations only; no future price is guaranteed.")
            await self.repository.market_cache_put(key, trend.model_dump(mode="json"), 360)
            await self.repository.record_provider("mistral", "Healthy", "Market trend classification available")
            return trend
        except AIProviderError:
            await self.repository.record_provider("mistral", "Fallback", "Deterministic market trend used")
            first = history[0].modal_price
            last = history[-1].modal_price
            change = (last - first) / first if first else 0
            direction = "RISING" if change > 0.03 else "FALLING" if change < -0.03 else "STABLE"
            return MarketTrend(trend=direction, confidence=round(min(0.7, 0.35 + abs(change)), 2), reasoning_summary=f"Observed average modal price changed {change:+.1%} across {len(history)} available dates.", forecast_horizon=f"Past {len(history)} observed dates; no future prediction", source="DETERMINISTIC", is_synthetic=market.is_synthetic, limitation="Rule-based historical direction. Missing days and synthetic examples limit interpretation.")
