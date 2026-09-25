"""Top-level API router."""

from fastapi import APIRouter

from app.api.farms import router as farms_router
from app.api.health import router as health_router
from app.api.market import router as market_router
from app.api.weather import router as weather_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(market_router)
api_router.include_router(weather_router)
api_router.include_router(farms_router)
