"""Owner-scoped farm, crop, and soil input operations."""

from uuid import UUID

from app.repositories.domain import (
    SupabaseCropRepository,
    SupabaseFarmRepository,
    SupabaseSoilTestRepository,
)
from app.schemas.entities import (
    CropCreate,
    CropRecord,
    FarmCreate,
    FarmRecord,
    SoilTestCreate,
    SoilTestRecord,
)


class FarmNotFoundError(Exception):
    """The requested farm does not exist or is not owned by this user."""


class FarmInputService:
    def __init__(
        self,
        farms: SupabaseFarmRepository,
        crops: SupabaseCropRepository,
        soil_tests: SupabaseSoilTestRepository,
    ) -> None:
        self._farms = farms
        self._crops = crops
        self._soil_tests = soil_tests

    async def list_farms(self, farmer_id: UUID) -> list[FarmRecord]:
        return await self._farms.list_for_farmer(farmer_id)

    async def create_farm(self, farmer_id: UUID, farm: FarmCreate) -> FarmRecord:
        return await self._farms.create(farm, farmer_id)

    async def list_crops(self, farmer_id: UUID, farm_id: UUID) -> list[CropRecord]:
        await self._require_owned_farm(farm_id, farmer_id)
        return await self._crops.list_for_farm(farm_id)

    async def create_crop(self, farmer_id: UUID, crop: CropCreate) -> CropRecord:
        await self._require_owned_farm(crop.farm_id, farmer_id)
        return await self._crops.create(crop)

    async def latest_soil_test(
        self, farmer_id: UUID, farm_id: UUID
    ) -> SoilTestRecord | None:
        await self._require_owned_farm(farm_id, farmer_id)
        return await self._soil_tests.latest_for_farm(farm_id)

    async def create_soil_test(
        self, farmer_id: UUID, farm_id: UUID, soil_test: SoilTestCreate
    ) -> SoilTestRecord:
        await self._require_owned_farm(farm_id, farmer_id)
        return await self._soil_tests.create(farm_id, soil_test)

    async def _require_owned_farm(self, farm_id: UUID, farmer_id: UUID) -> FarmRecord:
        farm = await self._farms.get_owned(farm_id, farmer_id)
        if farm is None:
            raise FarmNotFoundError
        return farm
