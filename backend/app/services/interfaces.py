"""Narrow application-service interfaces for upcoming feature phases."""

from typing import Protocol
from uuid import UUID

from app.schemas.entities import CropRecord, FarmRecord, FarmerProfile, ReportRecord


class HealthServiceInterface(Protocol):
    async def readiness(self) -> tuple[bool, dict[str, str]]: ...


class ProfileServiceInterface(Protocol):
    async def get_profile(self, farmer_id: UUID) -> FarmerProfile | None: ...


class FarmServiceInterface(Protocol):
    async def get_owned(self, farm_id: UUID, farmer_id: UUID) -> FarmRecord | None: ...
    async def list_for_farmer(self, farmer_id: UUID) -> list[FarmRecord]: ...


class CropServiceInterface(Protocol):
    async def list_for_farm(self, farm_id: UUID) -> list[CropRecord]: ...


class ReportServiceInterface(Protocol):
    async def get_owned(self, report_id: UUID, farmer_id: UUID) -> ReportRecord | None: ...
    async def list_for_farmer(self, farmer_id: UUID) -> list[ReportRecord]: ...
