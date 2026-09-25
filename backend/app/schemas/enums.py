"""Stable string values shared by the HTTP and persistence schemas."""

from enum import StrEnum


class Language(StrEnum):
    ENGLISH = "en"
    TELUGU = "te"


class Season(StrEnum):
    KHARIF = "kharif"
    RABI = "rabi"
    ZAID = "zaid"


class IrrigationType(StrEnum):
    RAINFED = "rainfed"
    DRIP = "drip"
    SPRINKLER = "sprinkler"
    FLOOD = "flood"


class SoilType(StrEnum):
    CLAY = "clay"
    LOAM = "loam"
    SANDY = "sandy"
    SILT = "silt"
    RED = "red"
    BLACK = "black"


class PhosphorusBasis(StrEnum):
    P = "P"
    P2O5 = "P2O5"
    UNKNOWN = "unknown"


class PotassiumBasis(StrEnum):
    K = "K"
    K2O = "K2O"
    UNKNOWN = "unknown"


class CropStatus(StrEnum):
    ACTIVE = "active"
    HARVESTED = "harvested"
    FAILED = "failed"


class AnalysisState(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    RESOLVED = "resolved"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(StrEnum):
    DISEASE_OUTBREAK = "disease_outbreak"
    PEST_WARNING = "pest_warning"
    WEATHER_RISK = "weather_risk"


class AlertLevel(StrEnum):
    ADVISORY = "advisory"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class RecommendationType(StrEnum):
    SEED = "seed"
    FERTILIZER = "fertilizer"
    MARKET = "market"
    GENERAL = "general"


class NotificationType(StrEnum):
    ALERT = "alert"
    RECOMMENDATION = "recommendation"
    MARKET = "market"
    SYSTEM = "system"


class JobType(StrEnum):
    DIAGNOSE_REPORT = "diagnose_report"
    EVALUATE_OUTBREAK = "evaluate_outbreak"
    DELIVER_PUSH = "deliver_push"
    REFRESH_MARKET_PRICES = "refresh_market_prices"
    EXPIRE_ALERTS = "expire_alerts"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
