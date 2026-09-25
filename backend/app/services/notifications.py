"""Persistence-first notification orchestration with best-effort push delivery."""

import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.schemas.enums import Language, NotificationType
from app.schemas.notification import (
    FcmDeliveryResult,
    NotificationPayload,
    PersistedNotification,
)

logger = logging.getLogger("agrivision.notifications")


class NotificationRepository(Protocol):
    async def create(self, payload: NotificationPayload) -> PersistedNotification: ...
    async def enabled_devices(self, farmer_id: UUID) -> list[dict[str, str]]: ...
    async def disable_device(self, device_id: str) -> None: ...


class PushSender(Protocol):
    async def send(self, notification: PersistedNotification, token: str) -> FcmDeliveryResult: ...


@dataclass(frozen=True)
class NotificationOutcome:
    persisted: bool
    notification: PersistedNotification | None
    delivery_status: str
    sent_count: int = 0
    failed_count: int = 0


class NotificationService:
    """Create the durable inbox item first; push delivery can never undo it."""

    def __init__(self, repository: NotificationRepository, push_sender: PushSender | None) -> None:
        self._repository = repository
        self._push_sender = push_sender

    async def create(self, payload: NotificationPayload, *, deliver_push: bool = True) -> NotificationOutcome:
        try:
            notification = await self._repository.create(payload)
        except Exception as exc:
            logger.warning("Inbox notification persistence failed; exception_type=%s", type(exc).__name__)
            return NotificationOutcome(False, None, "persistence_failed", failed_count=1)

        if not deliver_push or self._push_sender is None:
            return NotificationOutcome(True, notification, "not_requested")
        try:
            devices = await self._repository.enabled_devices(notification.farmer_id)
        except Exception as exc:
            logger.warning("Push device lookup failed; exception_type=%s", type(exc).__name__)
            return NotificationOutcome(True, notification, "unavailable", failed_count=1)
        if not devices:
            return NotificationOutcome(True, notification, "no_devices")

        sent = failed = 0
        delivery_results: list[str] = []
        for device in devices:
            try:
                result = await self._push_sender.send(notification, device["fcm_token"])
            except Exception as exc:
                logger.warning("Push sender failed; exception_type=%s", type(exc).__name__)
                failed += 1
                delivery_results.append("failed")
                continue
            delivery_results.append(result.status)
            if result.status == "delivered":
                sent += 1
            else:
                failed += 1
                if result.status == "invalid_token":
                    try:
                        await self._repository.disable_device(device["id"])
                    except Exception as exc:
                        logger.warning("Invalid device cleanup failed; exception_type=%s", type(exc).__name__)

        if sent == len(devices):
            status = "delivered"
        elif sent:
            status = "partial"
        elif delivery_results and all(result == "unavailable" for result in delivery_results):
            status = "unavailable"
        elif failed:
            status = "failed"
        else:
            status = "unavailable"
        return NotificationOutcome(True, notification, status, sent, failed)

    async def notify_report_created(
        self,
        farmer_id: UUID,
        report_id: UUID,
        language: Language = Language.ENGLISH,
    ) -> NotificationOutcome:
        """Best-effort post-commit hook; safe to call after a report is committed."""
        if language == Language.TELUGU:
            title, body = "పంట నివేదిక అందింది", "మీ పంట సమస్య నివేదిక విజయవంతంగా సమర్పించబడింది."
        else:
            title, body = "Crop report received", "Your crop problem report was submitted successfully."
        payload = NotificationPayload(
            farmer_id=farmer_id,
            title=title,
            body=body,
            language=language,
            type=NotificationType.SYSTEM,
            destination_path=f"/reports/{report_id}",
            dedupe_key=f"report:{report_id}:created",
        )
        try:
            return await self.create(payload)
        except Exception as exc:
            # Keep this hook safe even if validation or a future adapter regresses.
            logger.warning("Report notification failed safely; exception_type=%s", type(exc).__name__)
            return NotificationOutcome(False, None, "failed", failed_count=1)
