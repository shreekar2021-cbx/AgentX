"""Supabase-backed repository implementations."""

from app.repositories.domain import (
    SupabaseCropRepository,
    SupabaseFarmerRepository,
    SupabaseFarmRepository,
    SupabaseReportRepository,
    SupabaseSoilTestRepository,
)

__all__ = [
    "SupabaseCropRepository",
    "SupabaseFarmerRepository",
    "SupabaseFarmRepository",
    "SupabaseReportRepository",
    "SupabaseSoilTestRepository",
]
