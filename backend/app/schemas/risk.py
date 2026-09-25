"""Inputs and outputs for deterministic crop and outbreak risk assessment."""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.schemas.crop_health import CropHealthDiagnosis
from app.schemas.entities import Coordinates
from app.schemas.enums import AnalysisState, ReviewStatus


class RiskWeather(BaseModel):
    """Observed weather only; forecast rain must not be supplied as past rain."""

    model_config = ConfigDict(allow_inf_nan=False)

    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    observed_rain_48h_mm: float | None = Field(default=None, ge=0)
    is_stale: bool = False


class RiskInput(BaseModel):
    crop_analysis: CropHealthDiagnosis
    weather: RiskWeather | None = None


class IndividualRiskAssessment(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    individual_risk: float = Field(ge=0, le=1)
    weather_status: Literal["fresh", "missing", "stale"]
    expert_review_recommended: bool
    rule_version: Literal["risk-v1"] = "risk-v1"


class ReportEvidence(BaseModel):
    """Persisted report projection supplied by an authorized workflow.

    `canonical_disease_code` is set only after a curated code mapping succeeds.
    Unmapped AI problem names must be represented as None.
    """

    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

    report_id: UUID
    farmer_id: UUID
    commodity_id: UUID | None = None
    canonical_disease_code: str | None = Field(default=None, min_length=1, max_length=80)
    location: Coordinates | None = None
    confidence: float = Field(ge=0, le=1)
    analysis_state: AnalysisState
    review_status: ReviewStatus
    created_at: AwareDatetime


class OutbreakInput(BaseModel):
    crop_analysis: CropHealthDiagnosis
    risk: IndividualRiskAssessment
    source_report: ReportEvidence
    nearby_reports: list[ReportEvidence] = Field(default_factory=list, max_length=2000)
    evaluated_at: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutbreakAssessment(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    individual_risk: float = Field(ge=0, le=1)
    community_risk: float = Field(ge=0, le=1)
    nearby_alert: bool
    alert_reason: str = Field(min_length=1)
