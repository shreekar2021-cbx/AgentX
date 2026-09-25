from app.repositories.contracts import FarmRepository
from app.schemas.common import FarmRead


class FarmService:
    def __init__(self, repository: FarmRepository) -> None:
        self.repository = repository

    async def list_farms(self, user_id: str, user_token: str) -> list[FarmRead]:
        rows = await self.repository.list_for_user(user_id, user_token)
        return [FarmRead.model_validate(row) for row in rows]
