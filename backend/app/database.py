"""Supabase contexts sharing the application's asynchronous HTTP connection pool."""

import asyncio

import httpx
from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import Settings


class SupabaseConnection:
    """Keep privileged and caller-scoped headers separate; never sign in on these clients."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http_client = http_client
        self._service_client: AsyncClient | None = None
        self._service_lock = asyncio.Lock()

    def _options(self, token: str) -> AsyncClientOptions:
        return AsyncClientOptions(
            headers={"Authorization": f"Bearer {token}"},
            auto_refresh_token=False,
            persist_session=False,
            httpx_client=self._http_client,
        )

    async def service_client(self) -> AsyncClient:
        """Explicit privileged access for readiness and future authorized jobs/admin work."""
        url = self._settings.supabase_url
        key = self._settings.supabase_service_key
        if not self._settings.supabase_configured or not url or not key:
            raise RuntimeError("Supabase is not configured")
        async with self._service_lock:
            if self._service_client is None:
                self._service_client = await acreate_client(
                    url, key.get_secret_value(), options=self._options(key.get_secret_value())
                )
        return self._service_client

    async def user_client(self, access_token: str) -> AsyncClient:
        """Use an upstream-verified JWT for RLS; this factory does not verify tokens."""
        url = self._settings.supabase_url
        key = self._settings.supabase_anon_key
        if not url or not key:
            raise RuntimeError("Supabase is not configured")
        if not access_token.strip():
            raise ValueError("A non-empty user access token is required")
        return await acreate_client(
            url, key.get_secret_value(), options=self._options(access_token.strip())
        )
