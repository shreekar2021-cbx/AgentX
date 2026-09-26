from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class SourceStatus(StrEnum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    FALLBACK = "FALLBACK"
    DEMO = "DEMO"


class Severity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class FarmRead(BaseModel):
    id: UUID
    name: str
    district: str
    area_acres: float = Field(ge=0)
    created_at: datetime


class CropReportCreate(BaseModel):
    field_id: UUID
    crop_id: UUID
    symptom_description: str = Field(min_length=10, max_length=4000)
    notes: str | None = Field(default=None, max_length=4000)
    observed_at: datetime
    location: Coordinate | None = None


class CropReportRead(BaseModel):
    id: UUID
    user_id: UUID
    crop_id: UUID
    status: str
    severity: Severity | None
    created_at: datetime


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    environment: str
    database: str
    timestamp: datetime
    demo_mode: bool = False
    groq_configured: bool = False
