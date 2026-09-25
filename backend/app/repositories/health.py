"""Supabase-backed readiness check."""

import asyncio

from app.database import SupabaseConnection


class SupabaseHealthRepository:
    def __init__(self, connection: SupabaseConnection, *, timeout_seconds: float = 10) -> None:
        self._connection = connection
        self._timeout_seconds = timeout_seconds

    async def check_database(self) -> bool:
        try:
            await asyncio.wait_for(
                self._check_database(), timeout=self._timeout_seconds
            )
            return True
        except Exception:
            return False

    async def _check_database(self) -> None:
        client = await self._connection.service_client()
        await client.table("commodities").select("id").limit(1).execute()
