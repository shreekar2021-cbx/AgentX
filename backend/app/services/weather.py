from app.core.config import Settings
from app.providers.open_meteo import OpenMeteoProvider, WeatherProviderError
from app.repositories.local import LocalRepository
from app.schemas.intelligence import WeatherResult
from app.services.location import validate_coordinates


class WeatherService:
    def __init__(self, settings: Settings, provider: OpenMeteoProvider, cache: LocalRepository) -> None:
        self.settings = settings
        self.provider = provider
        self.cache = cache

    async def get(self, latitude: float, longitude: float) -> WeatherResult:
        validate_coordinates(latitude, longitude)
        key = f"{round(latitude, 2)}:{round(longitude, 2)}"
        fresh = await self.cache.weather_cache_get(key)
        if fresh:
            if hasattr(self.cache, "record_provider"):
                await self.cache.record_provider("weather", "Cached")
            return fresh
        try:
            live = await self.provider.forecast(latitude, longitude)
            await self.cache.weather_cache_put(key, live, self.settings.weather_cache_minutes)
            if hasattr(self.cache, "record_provider"):
                await self.cache.record_provider("weather", "Healthy")
            return live
        except WeatherProviderError:
            stale = await self.cache.weather_cache_get(key, allow_stale=True)
            if stale:
                if hasattr(self.cache, "record_provider"):
                    await self.cache.record_provider("weather", "Cached", "Stale weather cache")
                stale.agricultural_indicators.append("Cached forecast may be outdated; verify locally before field action.")
                return stale
            if hasattr(self.cache, "record_provider"):
                await self.cache.record_provider("weather", "Fallback", "No current observation")
            return WeatherResult(
                latitude=latitude, longitude=longitude, source="LOCAL KNOWLEDGE", provider=None,
                current=None, daily=[], hourly=[], stale=True, is_synthetic=False,
                agricultural_indicators=["Live weather is unavailable. Check a local forecast before making weather-sensitive decisions."],
            )
