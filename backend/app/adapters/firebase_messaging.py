"""Optional Firebase Cloud Messaging adapter using Firebase Admin ADC."""

import asyncio
import logging
from typing import Any

from app.schemas.notification import FcmDataPayload, FcmDeliveryResult, PersistedNotification

logger = logging.getLogger("agrivision.notifications.fcm")


class FirebaseMessagingAdapter:
    def __init__(self, project_id: str | None, timeout_seconds: float = 3) -> None:
        self._project_id = project_id
        self._timeout_seconds = timeout_seconds
        self._app: Any = None
        self._lock = asyncio.Lock()

    async def _get_app(self) -> Any:
        if not self._project_id:
            return None
        if self._app is not None:
            return self._app
        async with self._lock:
            if self._app is not None:
                return self._app
            try:
                import firebase_admin

                def initialize() -> Any:
                    try:
                        return firebase_admin.get_app("agrivision-notifications")
                    except ValueError:
                        return firebase_admin.initialize_app(
                            options={"projectId": self._project_id},
                            name="agrivision-notifications",
                        )

                self._app = await asyncio.to_thread(initialize)
            except Exception as exc:
                logger.warning("FCM initialization unavailable; exception_type=%s", type(exc).__name__)
                return None
        return self._app

    async def send(self, notification: PersistedNotification, token: str) -> FcmDeliveryResult:
        app = await self._get_app()
        if app is None:
            return FcmDeliveryResult(status="unavailable")
        try:
            from firebase_admin import messaging

            data = FcmDataPayload(
                notification_id=str(notification.id),
                type=notification.type.value,
                destination_path=notification.destination_path,
            ).model_dump(exclude_none=True)
            message = messaging.Message(
                notification=messaging.Notification(title=notification.title, body=notification.body),
                data=data,
                token=token,
            )
            async with asyncio.timeout(self._timeout_seconds):
                response = await messaging.send_each_async([message], app=app)
            if response.success_count:
                return FcmDeliveryResult(status="delivered", message_id=response.responses[0].message_id)
            error = response.responses[0].exception if response.responses else None
            if isinstance(error, messaging.UnregisteredError):
                return FcmDeliveryResult(status="invalid_token")
            logger.warning("FCM send failed; exception_type=%s", type(error).__name__ if error else "unknown")
            return FcmDeliveryResult(status="failed")
        except Exception as exc:
            logger.warning("FCM send unavailable; exception_type=%s", type(exc).__name__)
            return FcmDeliveryResult(status="unavailable")
