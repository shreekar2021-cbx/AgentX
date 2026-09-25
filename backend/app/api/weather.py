"""The single public weather query endpoint; no provider controls are exposed."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.schemas.common import ApiErrorResponse, ApiResponse, ResponseMeta, SourceInfo
from app.schemas.weather import WeatherData, WeatherLocation
from app.services.weather import WeatherService

router = APIRouter(prefix="/api/weather", tags=["weather"])


def get_weather_service(request: Request) -> WeatherService:
    return request.app.state.weather_service


@router.get("", response_model=ApiResponse[WeatherData], responses={503: {"model": ApiErrorResponse}})
async def weather(
    request: Request,
    lat: Annotated[float, Query(ge=-90, le=90, allow_inf_nan=False)],
    lng: Annotated[float, Query(ge=-180, le=180, allow_inf_nan=False)],
    service: Annotated[WeatherService, Depends(get_weather_service)],
) -> ApiResponse[WeatherData]:
    result = await service.get_weather(WeatherLocation(latitude=lat, longitude=lng))
    if result.data is None:
        raise HTTPException(status_code=503, detail="Weather is temporarily unavailable and no usable cached data exists.")
    return ApiResponse(
        data=result.data,
        meta=ResponseMeta(
            request_id=request.state.request_id,
            sources=[SourceInfo(**result.model_dump(exclude={"data", "warnings"}))],
            warnings=result.warnings,
        ),
    )
