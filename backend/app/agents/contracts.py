from typing import Any, Protocol


class CropHealthAgent(Protocol):
    async def evaluate(self, report_id: str) -> dict[str, Any]: ...


class RiskAgent(Protocol):
    async def assess(self, farm_id: str) -> dict[str, Any]: ...


class OutbreakAgent(Protocol):
    async def detect(self, district: str) -> list[dict[str, Any]]: ...


class MarketIntelligenceAgent(Protocol):
    async def summarize(self, commodity: str, district: str) -> dict[str, Any]: ...


class SeedRecommendationAgent(Protocol):
    async def recommend(self, field_id: str, season: str) -> list[dict[str, Any]]: ...


class FertilizerAgent(Protocol):
    async def advise(self, crop_cycle_id: str) -> dict[str, Any]: ...
