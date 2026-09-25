"""Inbox persistence remains successful when push delivery is unavailable."""

from datetime import datetime, timezone
import unittest
from uuid import UUID, uuid4

from app.adapters.firebase_messaging import FirebaseMessagingAdapter
from app.schemas.enums import Language
from app.schemas.notification import FcmDeliveryResult, NotificationPayload, PersistedNotification
from app.services.notifications import NotificationService

FARMER_ID = UUID("11111111-1111-4111-8111-111111111111")


class MemoryNotifications:
    def __init__(self):
        self.records = {}
        self.devices = []
        self.disabled = []

    async def create(self, payload):
        if payload.dedupe_key in self.records:
            return self.records[payload.dedupe_key]
        record = PersistedNotification(
            **payload.model_dump(), id=uuid4(), created_at=datetime.now(timezone.utc)
        )
        self.records[payload.dedupe_key] = record
        return record

    async def enabled_devices(self, farmer_id):
        return self.devices

    async def disable_device(self, device_id):
        self.disabled.append(device_id)


class NotificationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repository = MemoryNotifications()
        self.payload = NotificationPayload(
            farmer_id=FARMER_ID,
            title="Crop report received",
            body="Your report was saved.",
            dedupe_key="report:test:created",
            destination_path="/reports/test",
        )

    async def test_in_app_notification_is_created_when_fcm_not_configured(self):
        service = NotificationService(self.repository, FirebaseMessagingAdapter(project_id=None))
        self.repository.devices = [{"id": "device-1", "fcm_token": "never-logged"}]

        outcome = await service.create(self.payload)

        self.assertTrue(outcome.persisted)
        self.assertEqual(outcome.delivery_status, "unavailable")
        self.assertEqual(outcome.notification.dedupe_key, self.payload.dedupe_key)
        self.assertIn(self.payload.dedupe_key, self.repository.records)

    async def test_in_app_notification_survives_sender_exception(self):
        class BrokenPushSender:
            async def send(self, notification, token):
                raise RuntimeError("provider unavailable")

        self.repository.devices = [{"id": "device-1", "fcm_token": "private"}]
        service = NotificationService(self.repository, BrokenPushSender())

        outcome = await service.create(self.payload)

        self.assertTrue(outcome.persisted)
        self.assertEqual(outcome.delivery_status, "failed")
        self.assertEqual(len(self.repository.records), 1)

    async def test_report_hook_is_idempotent_and_persistence_first(self):
        service = NotificationService(self.repository, None)
        report_id = UUID("22222222-2222-4222-8222-222222222222")

        outcome = await service.notify_report_created(FARMER_ID, report_id, Language.TELUGU)

        self.assertTrue(outcome.persisted)
        self.assertEqual(outcome.notification.dedupe_key, f"report:{report_id}:created")
        self.assertEqual(outcome.notification.destination_path, f"/reports/{report_id}")
        self.assertEqual(outcome.notification.language, Language.TELUGU)

    async def test_external_notification_destination_is_rejected(self):
        with self.assertRaises(ValueError):
            NotificationPayload(
                farmer_id=FARMER_ID,
                title="Title",
                body="Body",
                dedupe_key="external-path",
                destination_path="https://example.com",
            )


if __name__ == "__main__":
    unittest.main()
