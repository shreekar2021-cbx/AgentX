"""Liveness and dependency readiness endpoints."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.schemas.common import HealthResponse, ReadinessResponse
from app.services.health import HealthService

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report that the process is accepting requests; no external service is needed."""
    return HealthResponse(status="healthy")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "Persistence unavailable"}},
)
async def readiness(request: Request) -> ReadinessResponse | JSONResponse:
    """Report whether required persistence is configured and reachable."""
    service: HealthService = request.app.state.health_service
    ready, dependencies = await service.readiness()
    response = ReadinessResponse(
        status="ready" if ready else "not_ready", dependencies=dependencies
    )
    if not ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(mode="json"),
        )
    return response
