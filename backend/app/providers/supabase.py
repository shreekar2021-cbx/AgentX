from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.core.errors import AppError


class SupabaseGateway:
    """User-scoped PostgREST gateway. RLS sees the caller's JWT."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    async def get(self, table: str, user_token: str, params: dict[str, str]) -> list[dict]:
        if not self.settings.database_configured:
            raise AppError(503, "database_unavailable", "Supabase is not configured.")
        # Table names come only from repository constants, never untrusted input.
        response = await self.client.get(
            f"{self.settings.supabase_url.rstrip('/')}/rest/v1/{quote(table, safe='')}",
            params=params,
            headers={"apikey": self.settings.supabase_anon_key, "Authorization": f"Bearer {user_token}"},
        )
        if response.status_code >= 400:
            raise AppError(502, "database_error", "Data could not be retrieved.")
        return response.json()


@asynccontextmanager
async def supabase_client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
        yield client
