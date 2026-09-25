"""Normalized notification input, persisted record, and push delivery contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import DatabaseModel
from app.schemas.enums import Language, NotificationType


class NotificationPayload(DatabaseModel):
    farmer_id: UUID
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=1000)
    language: Language = Language.ENGLISH
    type: NotificationType = NotificationType.SYSTEM
    destination_path: str | None = Field(default=None, max_length=500)
    dedupe_key: str = Field(min_length=1, max_length=200)
    alert_id: UUID | None = None
    alert_revision: int | None = Field(default=None, ge=1)

    @field_validator("destination_path")
    @classmethod
    def internal_destination_only(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("destination_path must be an internal application path")
        return value


class PersistedNotification(NotificationPayload):
    id: UUID
    read_at: datetime | None = None
    created_at: datetime


class FcmDataPayload(DatabaseModel):
    notification_id: str
    type: str
    destination_path: str | None = None


class FcmDeliveryResult(DatabaseModel):
    status: Literal["delivered", "failed", "invalid_token", "unavailable"]
    message_id: str | None = None
