"""Validated crop health input and provisional AI result contracts."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import SourceInfo
from app.schemas.enums import Language, Season, Severity

Advice = Annotated[str, Field(min_length=1, max_length=400)]


class CropImage(BaseModel):
    """A sanitized image derivative prepared by the report workflow."""

    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    data: bytes = Field(min_length=1, max_length=5 * 1024 * 1024, repr=False)


class CropHealthInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    description: str | None = Field(default=None, max_length=4000)
    image: CropImage | None = None
    crop_name: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    season: Season | None = None
    weather_context: str | None = Field(default=None, max_length=1000)
    language: Language = Language.ENGLISH

    @model_validator(mode="after")
    def require_symptom_evidence(self) -> "CropHealthInput":
        if not self.description and self.image is None:
            raise ValueError("A symptom description or prepared crop image is required")
        return self


class CropHealthDiagnosis(BaseModel):
    """Model output is a possible problem, never a confirmed diagnosis."""

    model_config = ConfigDict(
        extra="forbid", strict=True, str_strip_whitespace=True, allow_inf_nan=False
    )

    possible_problem: str = Field(min_length=1, max_length=160)
    confidence: float = Field(ge=0, le=1)
    severity: Severity
    symptoms: list[Advice] = Field(max_length=10)
    possible_causes: list[Advice] = Field(max_length=10)
    immediate_actions: list[Advice] = Field(max_length=10)
    precautions: list[Advice] = Field(max_length=10)
    monitoring: list[Advice] = Field(max_length=10)
    expert_verification: bool
    spread_potential: Literal["low", "medium", "high", "unknown"]

    @field_validator("possible_problem")
    @classmethod
    def reject_confirmed_claim(cls, value: str) -> str:
        if re.search(r"\b(confirmed|definite|certain|diagnosed)\b", value, re.IGNORECASE):
            raise ValueError("possible_problem must not claim a confirmed diagnosis")
        return value

    @model_validator(mode="after")
    def apply_expert_guardrail(self) -> "CropHealthDiagnosis":
        if self.confidence < 0.70 or self.severity == Severity.CRITICAL or not self.symptoms:
            self.expert_verification = True
        return self


class CropHealthAgentResult(BaseModel):
    status: Literal["complete", "unavailable"]
    agent: Literal["crop_health"] = "crop_health"
    diagnosis_status: Literal["unconfirmed"] = "unconfirmed"
    schema_version: Literal["1"] = "1"
    result: CropHealthDiagnosis | None = None
    sources: list[SourceInfo] = Field(default_factory=list)
    model_used: str | None = None
    prompt_version: Literal["crop-health-v1"] = "crop-health-v1"
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
