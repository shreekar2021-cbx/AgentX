"""Shared API response and error contracts."""

from datetime import datetime, timezone
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SourceInfo(BaseModel):
    provider: str
    status: str
    observed_at: datetime | None = None
    fetched_at: datetime | None = None
    expires_at: datetime | None = None
    is_stale: bool = False


class ApiWarning(BaseModel):
    code: str
    message: str


class ResponseMeta(BaseModel):
    request_id: UUID | None = None
    schema_version: str = "1"
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    sources: list[SourceInfo] = Field(default_factory=list)
    warnings: list[ApiWarning] = Field(default_factory=list)


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: dict[str, str] | None = None
    retryable: bool = False


class ErrorMeta(BaseModel):
    request_id: UUID | None = None


class ApiErrorResponse(BaseModel):
    error: ErrorDetail
    meta: ErrorMeta


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: dict[str, str]


class DatabaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
