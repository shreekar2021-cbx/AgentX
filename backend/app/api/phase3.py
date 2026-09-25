from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.agents.market_intelligence import MarketIntelligenceAgent
from app.agents.recommendations import FertilizerAgent, SeedRecommendationAgent
from app.api.intelligence import get_repository, weather_service
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import Principal, current_principal
from app.knowledge.catalog import CROPS, normalize_crop
from app.providers.mistral import MistralProvider
from app.providers.ogd_market import OGDMarketProvider
from app.repositories.phase3 import Phase3LocalRepository
from app.schemas.phase3 import FarmProfile, FarmProfileInput, FertilizerRecommendation, MarketEstimate, MarketEstimateInput, MarketResponse, MarketTrend, NotificationPublic, PortfolioCrop, PortfolioInput, SeedRecommendation
from app.services.market import MarketService, estimate_return
from app.services.weather import WeatherService

router = APIRouter(prefix="/api", tags=["phase3"])


def market_service(request: Request, repository: Phase3LocalRepository = Depends(get_repository), settings: Settings = Depends(get_settings)) -> MarketService:
    return MarketService(settings, OGDMarketProvider(settings, request.app.state.http_client), repository)


@router.get("/farms/profile", response_model=FarmProfile | None)
async def get_profile(principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository)):
    return await repository.get_farm_profile(principal.user_id)


@router.put("/farms/profile", response_model=FarmProfile)
async def put_profile(profile: FarmProfileInput, principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository)):
    return await repository.save_farm_profile(principal.user_id, profile.model_dump(mode="json"))


@router.get("/portfolio", response_model=list[PortfolioCrop])
async def list_portfolio(principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository)):
    crops = await repository.list_portfolio(principal.user_id)
    reports = await repository.list_reports(principal.user_id, limit=200)
    for crop in crops:
        recent = next((report for report in reports if report.crop.casefold() == crop["crop"].casefold() and report.field.casefold() == crop["field"].casefold()), None)
        if recent:
            crop["latest_report_id"] = recent.id
            crop["latest_report_at"] = recent.created_at
            crop["latest_risk"] = recent.risk.individual_risk if recent.risk else None
    return crops


@router.post("/portfolio", response_model=PortfolioCrop, status_code=201)
async def add_crop(crop: PortfolioInput, principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository)):
    if normalize_crop(crop.crop) not in CROPS:
        raise AppError(422, "unsupported_crop", "Select a crop from the supported list.")
    return await repository.save_crop(principal.user_id, crop.model_dump(mode="json"))


@router.put("/portfolio/{crop_id}", response_model=PortfolioCrop)
async def update_crop(crop_id: UUID, crop: PortfolioInput, principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository)):
    try:
        return await repository.save_crop(principal.user_id, crop.model_dump(mode="json"), str(crop_id))
    except KeyError as exc:
        raise AppError(404, "crop_not_found", "Crop portfolio entry not found.") from exc


@router.delete("/portfolio/{crop_id}", status_code=204)
async def delete_crop(crop_id: UUID, principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository)):
    if not await repository.delete_crop(principal.user_id, str(crop_id)):
        raise AppError(404, "crop_not_found", "Crop portfolio entry not found.")


@router.get("/market/prices", response_model=MarketResponse)
async def market_prices(
    commodity: str = Query(..., min_length=2, max_length=80), district: str | None = Query(None, max_length=80),
    latitude: float | None = Query(None, ge=-90, le=90), longitude: float | None = Query(None, ge=-180, le=180),
    principal: Principal = Depends(current_principal), service: MarketService = Depends(market_service),
):
    if (latitude is None) != (longitude is None):
        raise AppError(422, "invalid_location", "Provide latitude and longitude together.")
    return await service.get(commodity, district, latitude, longitude)


class TrendRequest(BaseModel):
    commodity: str
    district: str | None = None


@router.post("/market/trend", response_model=MarketTrend)
async def market_trend(body: TrendRequest, request: Request, principal: Principal = Depends(current_principal), service: MarketService = Depends(market_service), repository: Phase3LocalRepository = Depends(get_repository), settings: Settings = Depends(get_settings)):
    market = await service.get(body.commodity, body.district)
    return await MarketIntelligenceAgent(MistralProvider(settings, request.app.state.http_client), repository, settings).analyze(market, principal.user_id)


@router.post("/market/estimate", response_model=MarketEstimate)
async def market_estimate(values: MarketEstimateInput, principal: Principal = Depends(current_principal)):
    return estimate_return(values)


@router.post("/recommendations/seed", response_model=SeedRecommendation)
async def seed_recommendation(profile: FarmProfileInput, principal: Principal = Depends(current_principal), weather: WeatherService = Depends(weather_service)):
    context = await weather.get(profile.latitude, profile.longitude) if profile.latitude is not None and profile.longitude is not None else None
    return SeedRecommendationAgent().recommend(profile, context)


@router.post("/recommendations/fertilizer", response_model=FertilizerRecommendation)
async def fertilizer_recommendation(profile: FarmProfileInput, principal: Principal = Depends(current_principal)):
    return FertilizerAgent().recommend(profile)


@router.get("/notifications", response_model=list[NotificationPublic])
async def notifications(principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository)):
    return await repository.list_notifications(principal.user_id)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationPublic)
async def read_notification(notification_id: UUID, principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository)):
    if not await repository.mark_notification_read(principal.user_id, str(notification_id)):
        raise AppError(404, "notification_not_found", "Notification not found.")
    return await repository.get_notification(principal.user_id, str(notification_id))


@router.get("/provider-health")
async def provider_health(principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository), settings: Settings = Depends(get_settings)):
    if not principal.is_demo and principal.role != "admin":
        raise AppError(403, "forbidden", "Administrator access is required.")
    events = await repository.provider_events()
    def item(name: str, default: str, detail: str):
        event = events.get(name)
        return {"name": name, "state": event["state"] if event else default, "observed_at": event["observed_at"] if event else None, "detail": event["detail"] if event and event["detail"] else detail}
    return {"providers": [
        item("mistral", "Degraded" if settings.mistral_api_key else "Unavailable", "Configured; no recent result" if settings.mistral_api_key else "API key not set"),
        item("weather", "Degraded", "No recent weather request"),
        item("market", "Degraded" if settings.ogd_api_key else "Fallback", "No recent market request" if settings.ogd_api_key else "OGD key not set; dated synthetic dataset available"),
        item("database", "Healthy", "Local development SQLite active"),
        item("notifications", "Healthy", "Persistent in-app store active"),
    ]}


@router.get("/admin/overview")
async def admin_overview(principal: Principal = Depends(current_principal), repository: Phase3LocalRepository = Depends(get_repository)):
    if not principal.is_demo and principal.role != "admin":
        raise AppError(403, "forbidden", "Administrator access is required.")
    return await repository.demo_overview()
