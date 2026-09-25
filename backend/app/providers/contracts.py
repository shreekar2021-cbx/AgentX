from typing import Any, Protocol

from app.schemas.intelligence import CropHealthFinding, WeatherResult


class AIProvider(Protocol):
    async def analyze_crop(self, image: bytes, mime_type: str, context: dict[str, Any]) -> CropHealthFinding: ...


class WeatherProvider(Protocol):
    async def forecast(self, latitude: float, longitude: float) -> WeatherResult: ...


class MarketProvider(Protocol):
    async def prices(self, commodity: str, district: str) -> dict[str, Any]: ...


class NotificationProvider(Protocol):
    async def send(self, user_id: str, template: str, payload: dict[str, Any]) -> str: ...
