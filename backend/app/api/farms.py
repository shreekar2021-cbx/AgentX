"""Authenticated farm, crop, and soil input endpoints."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.repositories.domain import (
    SupabaseCropRepository,
    SupabaseFarmRepository,
    SupabaseSoilTestRepository,
)
from app.schemas.common import ApiErrorResponse, ApiResponse, ResponseMeta
from app.schemas.entities import (
    CropCreate,
    CropRecord,
    FarmCreate,
    FarmRecord,
    SoilTestCreate,
    SoilTestRecord,
)
from app.services.farm_inputs import FarmInputService, FarmNotFoundError

router = APIRouter(tags=["farms"])
bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class FarmRequestContext:
    farmer_id: UUID
    service: FarmInputService


async def get_farm_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> FarmRequestContext:
    settings = request.app.state.settings
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(status_code=401, detail="A valid Supabase access token is required.")
    if not settings.supabase_configured or not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Farm storage is not configured.")

    token = credentials.credentials
    try:
        response = await request.app.state.http_client.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "apikey": settings.supabase_anon_key.get_secret_value(),
                "Authorization": f"Bearer {token}",
            },
            timeout=httpx.Timeout(5.0),
        )
    except (httpx.HTTPError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Unable to verify the Supabase session.") from exc

    if response.status_code in (400, 401, 403):
        raise HTTPException(status_code=401, detail="The Supabase session is invalid or expired.")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Unable to verify the Supabase session.")
    try:
        farmer_id = UUID(response.json()["id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="The Supabase session is invalid.") from exc

    try:
        user_client = await request.app.state.supabase.user_client(token)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Farm storage is not configured.") from exc
    return FarmRequestContext(
        farmer_id=farmer_id,
        service=FarmInputService(
            SupabaseFarmRepository(user_client),
            SupabaseCropRepository(user_client),
            SupabaseSoilTestRepository(user_client),
        ),
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Farm not found.")


@router.get(
    "/api/farms",
    response_model=ApiResponse[list[FarmRecord]],
    responses={401: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
)
async def list_farms(
    request: Request,
    context: Annotated[FarmRequestContext, Depends(get_farm_context)],
) -> ApiResponse[list[FarmRecord]]:
    rows = await context.service.list_farms(context.farmer_id)
    return ApiResponse(data=rows, meta=ResponseMeta(request_id=request.state.request_id))


@router.post(
    "/api/farms",
    response_model=ApiResponse[FarmRecord],
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}},
)
async def create_farm(
    payload: FarmCreate,
    request: Request,
    context: Annotated[FarmRequestContext, Depends(get_farm_context)],
) -> ApiResponse[FarmRecord]:
    farm = await context.service.create_farm(context.farmer_id, payload)
    return ApiResponse(data=farm, meta=ResponseMeta(request_id=request.state.request_id))


@router.get(
    "/api/crops",
    response_model=ApiResponse[list[CropRecord]],
    responses={401: {"model": ApiErrorResponse}, 404: {"model": ApiErrorResponse}},
)
async def list_crops(
    request: Request,
    farm_id: Annotated[UUID, Query()],
    context: Annotated[FarmRequestContext, Depends(get_farm_context)],
) -> ApiResponse[list[CropRecord]]:
    try:
        rows = await context.service.list_crops(context.farmer_id, farm_id)
    except FarmNotFoundError as exc:
        raise _not_found() from exc
    return ApiResponse(data=rows, meta=ResponseMeta(request_id=request.state.request_id))


@router.post(
    "/api/crops",
    response_model=ApiResponse[CropRecord],
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ApiErrorResponse}, 404: {"model": ApiErrorResponse}},
)
async def create_crop(
    payload: CropCreate,
    request: Request,
    context: Annotated[FarmRequestContext, Depends(get_farm_context)],
) -> ApiResponse[CropRecord]:
    try:
        crop = await context.service.create_crop(context.farmer_id, payload)
    except FarmNotFoundError as exc:
        raise _not_found() from exc
    return ApiResponse(data=crop, meta=ResponseMeta(request_id=request.state.request_id))


@router.get(
    "/api/farms/{farm_id}/soil-test",
    response_model=ApiResponse[SoilTestRecord | None],
    responses={401: {"model": ApiErrorResponse}, 404: {"model": ApiErrorResponse}},
)
async def latest_soil_test(
    farm_id: UUID,
    request: Request,
    context: Annotated[FarmRequestContext, Depends(get_farm_context)],
) -> ApiResponse[SoilTestRecord | None]:
    try:
        result = await context.service.latest_soil_test(context.farmer_id, farm_id)
    except FarmNotFoundError as exc:
        raise _not_found() from exc
    return ApiResponse(data=result, meta=ResponseMeta(request_id=request.state.request_id))


@router.post(
    "/api/farms/{farm_id}/soil-test",
    response_model=ApiResponse[SoilTestRecord],
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ApiErrorResponse}, 404: {"model": ApiErrorResponse}},
)
async def create_soil_test(
    farm_id: UUID,
    payload: SoilTestCreate,
    request: Request,
    context: Annotated[FarmRequestContext, Depends(get_farm_context)],
) -> ApiResponse[SoilTestRecord]:
    try:
        result = await context.service.create_soil_test(context.farmer_id, farm_id, payload)
    except FarmNotFoundError as exc:
        raise _not_found() from exc
    return ApiResponse(data=result, meta=ResponseMeta(request_id=request.state.request_id))
