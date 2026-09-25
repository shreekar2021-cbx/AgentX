"""Health/readiness service, separate from HTTP route handling."""

from app.repositories.interfaces import HealthRepository
from app.services.interfaces import HealthServiceInterface


class HealthService(HealthServiceInterface):
    def __init__(self, repository: HealthRepository, *, configured: bool) -> None:
        self._repository = repository
        self._configured = configured

    async def readiness(self) -> tuple[bool, dict[str, str]]:
        if not self._configured:
            return False, {"supabase": "not_configured"}
        connected = await self._repository.check_database()
        return connected, {"supabase": "connected" if connected else "unavailable"}
