from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    database = "local_demo" if settings.local_demo_mode else "configured" if settings.database_configured else "not_configured"
    return HealthResponse(status="ok", environment=settings.app_env, database=database, timestamp=datetime.now(timezone.utc), demo_mode=settings.local_demo_mode)


@router.get("/capabilities", tags=["system"])
async def capabilities(settings: Settings = Depends(get_settings)) -> dict:
    local = settings.local_demo_mode
    return {"capabilities": {"crop_analysis": ("mistral_with_local_fallback" if settings.mistral_api_key else "local_knowledge_only") if local else "requires_production_repository", "weather": "open_meteo_with_cache" if local else "requires_production_repository", "market": ("ogd_with_cache_and_synthetic_fallback" if settings.ogd_api_key else "dated_synthetic_fallback") if local else "requires_production_repository", "nearby_alerts": "available_local" if local else "requires_production_repository", "farm_soil": "available_local" if local else "requires_production_repository", "recommendations": "available_local" if local else "requires_production_repository", "notifications": "persistent_in_app_local" if local else "requires_production_repository", "offline_sync": "indexeddb_client_queue_with_idempotent_local_api" if local else "requires_production_repository", "voice": "browser_web_speech_optional"}}


def planned(feature: str):
    async def endpoint() -> None:
        raise AppError(501, "feature_not_available", f"{feature} is planned for a later phase.")
    return endpoint


# Explicit 501 contracts prevent callers from treating sample frontend data as live API output.
for path, name, methods in [
    ("/farms", "Farm data", ["GET"]), ("/crops", "Crop data", ["GET"]),
    ("/analyses", "Crop analysis", ["GET"]), ("/alerts", "Nearby alerts", ["GET"]),
    ("/recommendations", "Recommendations", ["GET"]),
]:
    router.add_api_route(path, planned(name), methods=methods, tags=["planned"], name=f"planned_{path.replace('/', '_')}")
