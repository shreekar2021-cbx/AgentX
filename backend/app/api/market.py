"""Market prices only; prediction and ranking routes belong to later phases."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.schemas.common import ApiErrorResponse, ApiResponse, ResponseMeta, SourceInfo
from app.schemas.market import MarketCommodity, MarketHistoryResult, MarketPricesResult, MarketQuery
from app.services.market import MarketService, decode_cursor

router = APIRouter(prefix="/api/market", tags=["market"])


def get_market_service(request: Request) -> MarketService:
    return request.app.state.market_service


@router.get("/commodities", response_model=ApiResponse[list[MarketCommodity]])
async def market_commodities(
    request: Request,
    service: MarketService = Depends(get_market_service),
) -> ApiResponse[list[MarketCommodity]]:
    rows, provider = await service.get_commodities()
    return ApiResponse(
        data=rows,
        meta=ResponseMeta(
            request_id=request.state.request_id,
            sources=[SourceInfo(provider=provider, status="available" if rows else "unavailable")],
        ),
    )


@router.get("/history", response_model=ApiResponse[MarketHistoryResult],
            responses={503: {"model": ApiErrorResponse}})
async def market_history(
    request: Request,
    commodity_id: UUID,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    mandi_id: UUID | None = None,
    variety: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    grade: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    service: MarketService = Depends(get_market_service),
) -> ApiResponse[MarketHistoryResult]:
    result, provider, warnings, fetched_at = await service.get_history(
        commodity_id, days=days, mandi_id=mandi_id, variety=variety, grade=grade
    )
    return ApiResponse(
        data=result,
        meta=ResponseMeta(
            request_id=request.state.request_id,
            sources=[SourceInfo(
                provider=provider,
                status=result.source_status,
                fetched_at=fetched_at,
                is_stale=False,
            )],
            warnings=warnings,
        ),
    )


@router.get("/prices", response_model=ApiResponse[MarketPricesResult],
            responses={503: {"model": ApiErrorResponse}})
async def market_prices(
    request: Request,
    commodity_id: UUID,
    state: Annotated[str, Query(min_length=1, max_length=120)],
    district: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    variety: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    service: MarketService = Depends(get_market_service),
) -> ApiResponse[MarketPricesResult]:
    try:
        offset = decode_cursor(cursor) if cursor else 0
        query = MarketQuery(
            commodity_id=commodity_id, state=state, district=district,
            variety=variety, limit=limit, offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid market filters or cursor.") from exc
    result, provider, warnings, fetched_at = await service.get_prices(query)
    if result is None:
        raise HTTPException(status_code=503, detail="Market prices are temporarily unavailable.")
    return ApiResponse(
        data=result,
        meta=ResponseMeta(
            request_id=request.state.request_id,
            sources=[SourceInfo(
                provider=provider, status=result.source_status,
                fetched_at=fetched_at, is_stale=result.is_stale,
            )],
            warnings=warnings,
        ),
    )
