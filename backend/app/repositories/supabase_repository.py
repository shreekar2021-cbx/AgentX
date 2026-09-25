"""Small shared base for explicit, RLS-scoped PostgREST repositories."""

from typing import Any

from supabase import AsyncClient


class SupabaseRepository:
    def __init__(self, client: AsyncClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    async def select_many(
        self,
        *,
        columns: str = "*",
        filters: dict[str, str | int | float | bool] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = self._client.table(self._table_name).select(columns)
        for column, value in (filters or {}).items():
            query = query.eq(column, value)
        response = await query.limit(min(max(limit, 1), 100)).execute()
        return response.data or []

    async def select_one(
        self,
        *,
        columns: str = "*",
        filters: dict[str, str | int | float | bool],
    ) -> dict[str, Any] | None:
        rows = await self.select_many(columns=columns, filters=filters, limit=1)
        return rows[0] if rows else None
