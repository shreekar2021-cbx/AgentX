import logging

from app.repositories.phase3 import Phase3LocalRepository

logger = logging.getLogger("agrivision.notifications")


class NotificationService:
    def __init__(self, repository: Phase3LocalRepository) -> None:
        self.repository = repository

    async def notify(self, owner_id: str, kind: str, title: str, body: str, target_url: str | None = None) -> None:
        try:
            await self.repository.add_notification(owner_id, kind, title, body, target_url)
        except Exception:
            logger.exception("In-app notification persistence failed; core workflow remains available")
            try:
                await self.repository.record_provider("notifications", "Unavailable", "In-app persistence failed")
            except Exception:
                pass
        else:
            try:
                await self.repository.record_provider("notifications", "Healthy")
            except Exception:
                logger.exception("Notification health event could not be stored")
