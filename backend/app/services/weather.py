"""Weather orchestration: cache first, live refresh, then truthful stale fallback."""

from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import logging

from app.adapters.weather import FRESH_FOR, STALE_LIMIT, OpenMeteoAdapter
from app.repositories.weather_cache import WeatherCacheRepository
from app.schemas.common import ApiWarning
from app.schemas.weather import WeatherLocation, WeatherSnapshot, WeatherSourceResult

logger = logging.getLogger("agrivision.weather")


class WeatherService:
    def __init__(
        self, adapter: OpenMeteoAdapter, cache: WeatherCacheRepository | None = None,
        *, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        max_memory_entries: int = 256,
    ) -> None:
        self._adapter, self._cache, self._now = adapter, cache, now
        self._memory: OrderedDict[str, WeatherSnapshot] = OrderedDict()
        self._max_entries = max(1, max_memory_entries)

    def _remember(self, key: str, snapshot: WeatherSnapshot) -> None:
        self._memory[key] = snapshot
        self._memory.move_to_end(key)
        while len(self._memory) > self._max_entries:
            self._memory.popitem(last=False)

    def _usable(self, snapshot: WeatherSnapshot, location: WeatherLocation) -> bool:
        now = self._now()
        return (
            snapshot.data.location == location
            and timedelta(0) <= now - snapshot.fetched_at <= STALE_LIMIT
            and timedelta(minutes=-10) <= now - snapshot.data.current.observed_at <= STALE_LIMIT
            and snapshot.expires_at <= snapshot.fetched_at + FRESH_FOR
        )

    async def get_weather(self, location: WeatherLocation) -> WeatherSourceResult:
        location = location.cache_location()
        key, warnings = location.cache_key, []
        cached = self._memory.get(key)
        if cached is not None and not self._usable(cached, location):
            self._memory.pop(key, None)
            cached = None
        if cached is None and self._cache is not None:
            try:
                candidate = await self._cache.get(key)
                if candidate is not None and self._usable(candidate, location):
                    cached = candidate
                    self._remember(key, cached)
            except Exception:
                # Cache outages/malformed rows must not block live weather; never log payloads.
                logger.warning("weather_cache_read_failed")
                warnings.append(ApiWarning(code="weather_cache_unavailable", message="Persistent weather cache is unavailable."))

        if cached is not None and self._now() < cached.expires_at:
            self._memory.move_to_end(key)
            return self._cached_result(cached, stale=False, warnings=warnings)

        result = await self._adapter.get_weather(location)
        if result.data is not None and result.status == "live":
            snapshot = WeatherSnapshot(data=result.data, fetched_at=result.fetched_at, expires_at=result.expires_at)
            self._remember(key, snapshot)
            if self._cache is not None:
                try:
                    await self._cache.put(key, snapshot)
                except Exception:
                    logger.warning("weather_cache_write_failed")
                    warnings.append(ApiWarning(code="weather_cache_write_failed", message="Weather is available but could not be saved to the persistent cache."))
            result.warnings.extend(warnings)
            return result

        warnings.extend(result.warnings)
        # Recheck age after provider retries; a snapshot may have crossed the limit.
        if cached is not None and self._usable(cached, location):
            warnings.append(ApiWarning(
                code="stale_weather", message="Showing last known weather because live weather is unavailable. Do not use stale weather for risk bonuses or dosing advice."
            ))
            return self._cached_result(cached, stale=True, warnings=warnings)
        result.warnings = warnings
        return result

    @staticmethod
    def _cached_result(snapshot: WeatherSnapshot, *, stale: bool, warnings: list[ApiWarning]) -> WeatherSourceResult:
        return WeatherSourceResult(
            status="cached", data=snapshot.data, observed_at=snapshot.data.current.observed_at,
            fetched_at=snapshot.fetched_at, expires_at=snapshot.expires_at,
            is_stale=stale, warnings=warnings,
        )
