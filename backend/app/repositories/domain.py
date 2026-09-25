"""Initial owner-scoped repository implementations used by future services."""

from typing import Any
from uuid import UUID

from supabase import AsyncClient

from app.repositories.interfaces import (
    CropRepository,
    FarmerRepository,
    FarmRepository,
    ReportRepository,
)
from app.schemas.entities import CropCreate, CropRecord, FarmCreate, FarmRecord, SoilTestCreate, SoilTestRecord
from app.repositories.supabase_repository import SupabaseRepository


class SupabaseFarmerRepository(SupabaseRepository, FarmerRepository):
    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client, "farmers")

    async def get_profile(self, farmer_id: UUID) -> dict[str, Any] | None:
        return await self.select_one(filters={"id": str(farmer_id)})


class SupabaseFarmRepository(SupabaseRepository, FarmRepository):
    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client, "farms")

    async def get_owned(self, farm_id: UUID, farmer_id: UUID) -> FarmRecord | None:
        row = await self.select_one(
            filters={"id": str(farm_id), "farmer_id": str(farmer_id)}
        )
        return FarmRecord.model_validate(row) if row else None

    async def list_for_farmer(self, farmer_id: UUID) -> list[FarmRecord]:
        rows = await self.select_many(
            filters={"farmer_id": str(farmer_id)}, limit=100
        )
        return [FarmRecord.model_validate(row) for row in rows]

    async def create(self, farm: FarmCreate, farmer_id: UUID) -> FarmRecord:
        payload = farm.model_dump(mode="json")
        payload["farmer_id"] = str(farmer_id)
        result = await self._client.table(self._table_name).insert(payload).select("*").single().execute()
        return FarmRecord.model_validate(result.data)


class SupabaseCropRepository(SupabaseRepository, CropRepository):
    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client, "crops")

    async def list_for_farm(self, farm_id: UUID) -> list[CropRecord]:
        rows = await self.select_many(filters={"farm_id": str(farm_id)}, limit=100)
        return [CropRecord.model_validate(row) for row in rows]

    async def create(self, crop: CropCreate) -> CropRecord:
        result = await self._client.table(self._table_name).insert(
            crop.model_dump(mode="json")
        ).select("*").single().execute()
        return CropRecord.model_validate(result.data)


class SupabaseSoilTestRepository(SupabaseRepository):
    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client, "soil_tests")

    async def latest_for_farm(self, farm_id: UUID) -> SoilTestRecord | None:
        result = await (self._client.table(self._table_name).select("*")
                        .eq("farm_id", str(farm_id))
                        .order("test_date", desc=True).order("created_at", desc=True)
                        .limit(1).execute())
        rows = result.data or []
        return SoilTestRecord.model_validate(rows[0]) if rows else None

    async def create(self, farm_id: UUID, soil_test: SoilTestCreate) -> SoilTestRecord:
        payload = soil_test.model_dump(mode="json")
        payload["farm_id"] = str(farm_id)
        payload["micronutrients_mg_kg"] = {
            name: float(value) for name, value in soil_test.micronutrients_mg_kg.items()
        }
        result = await self._client.table(self._table_name).insert(payload).select("*").single().execute()
        return SoilTestRecord.model_validate(result.data)


class SupabaseReportRepository(SupabaseRepository, ReportRepository):
    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client, "reports")

    async def get_owned(
        self, report_id: UUID, farmer_id: UUID
    ) -> dict[str, Any] | None:
        return await self.select_one(
            filters={"id": str(report_id), "farmer_id": str(farmer_id)}
        )

    async def list_for_farmer(self, farmer_id: UUID) -> list[dict[str, Any]]:
        return await self.select_many(
            filters={"farmer_id": str(farmer_id)}, limit=100
        )
