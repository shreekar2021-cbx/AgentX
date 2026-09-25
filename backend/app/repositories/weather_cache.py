"""Optional persistent weather cache in the existing service_cache table."""

import asyncio
from typing import Protocol

from app.database import SupabaseConnection
from app.schemas.weather import WeatherSnapshot


class WeatherCacheRepository(Protocol):
    async def get(self, key: str) -> WeatherSnapshot | None: ...
    async def put(self, key: str, snapshot: WeatherSnapshot) -> None: ...


class SupabaseWeatherCacheRepository:
    def __init__(self, connection: SupabaseConnection) -> None:
        self._connection = connection

    async def get(self, key: str) -> WeatherSnapshot | None:
        async with asyncio.timeout(2):
            client = await self._connection.service_client()
            result = await (client.table("service_cache")
                            .select("payload,fetched_at,expires_at")
                            .eq("cache_key", key).eq("provider", "open-meteo")
                            .eq("schema_version", "1").limit(1).execute())
        if not result.data:
            return None
        row = result.data[0]
        return WeatherSnapshot(data=row["payload"], fetched_at=row["fetched_at"], expires_at=row["expires_at"])

    async def put(self, key: str, snapshot: WeatherSnapshot) -> None:
        async with asyncio.timeout(2):
            client = await self._connection.service_client()
            await client.table("service_cache").upsert({
                "cache_key": key, "provider": "open-meteo", "schema_version": "1",
                "payload": snapshot.data.model_dump(mode="json"),
                "fetched_at": snapshot.fetched_at.isoformat(),
                "expires_at": snapshot.expires_at.isoformat(),
            }, on_conflict="cache_key").execute()
