from typing import Protocol


class FarmRepository(Protocol):
    async def list_for_user(self, user_id: str, user_token: str) -> list[dict]: ...


class ReportRepository(Protocol):
    async def list_for_user(self, user_id: str, user_token: str) -> list[dict]: ...


class AlertRepository(Protocol):
    async def list_for_district(self, district: str, user_token: str) -> list[dict]: ...
