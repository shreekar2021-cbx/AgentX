"""Supabase persistence for inbox notifications and registered push devices."""

import asyncio
from uuid import UUID

from app.database import SupabaseConnection
from app.schemas.notification import NotificationPayload, PersistedNotification


class SupabaseNotificationRepository:
    def __init__(self, connection: SupabaseConnection, timeout_seconds: float = 3) -> None:
        self._connection = connection
        self._timeout_seconds = timeout_seconds

    async def create(self, payload: NotificationPayload) -> PersistedNotification:
        values = payload.model_dump(mode="json")
        values["alert_id"] = str(payload.alert_id) if payload.alert_id else None
        try:
            async with asyncio.timeout(self._timeout_seconds):
                client = await self._connection.service_client()
                result = await client.table("notifications").insert(values).execute()
            if result.data:
                return PersistedNotification.model_validate(result.data[0])
        except Exception:
            # Concurrent retries may hit the unique dedupe constraint. Return the
            # already-created inbox item when present; otherwise preserve failure.
            existing = await self.get_by_dedupe_key(payload.dedupe_key)
            if existing is not None:
                return existing
            raise
        raise RuntimeError("Notification insert returned no row")

    async def get_by_dedupe_key(self, dedupe_key: str) -> PersistedNotification | None:
        async with asyncio.timeout(self._timeout_seconds):
            client = await self._connection.service_client()
            result = await (client.table("notifications").select("*")
                            .eq("dedupe_key", dedupe_key).limit(1).execute())
        return PersistedNotification.model_validate(result.data[0]) if result.data else None

    async def enabled_devices(self, farmer_id: UUID) -> list[dict[str, str]]:
        async with asyncio.timeout(self._timeout_seconds):
            client = await self._connection.service_client()
            result = await (client.table("notification_devices")
                            .select("id,fcm_token").eq("farmer_id", str(farmer_id))
                            .eq("enabled", True).limit(100).execute())
        return result.data or []

    async def disable_device(self, device_id: str) -> None:
        async with asyncio.timeout(self._timeout_seconds):
            client = await self._connection.service_client()
            await (client.table("notification_devices").update({"enabled": False})
                   .eq("id", device_id).execute())
