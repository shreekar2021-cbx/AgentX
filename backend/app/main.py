"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.router import api_router
from app.adapters.gemini import GeminiAdapter
from app.adapters.market import DataGovMarketAdapter
from app.adapters.firebase_messaging import FirebaseMessagingAdapter
from app.adapters.weather import OpenMeteoAdapter
from app.agents.crop_health import CropHealthAgent
from app.agents.outbreak import OutbreakAgent
from app.agents.risk import RiskAgent
from app.config import Settings, get_settings
from app.database import SupabaseConnection
from app.repositories.health import SupabaseHealthRepository
from app.repositories.market import SupabaseMarketRepository
from app.repositories.market_csv import CsvMarketRepository
from app.repositories.notifications import SupabaseNotificationRepository
from app.repositories.weather_cache import SupabaseWeatherCacheRepository
from app.schemas.common import ApiErrorResponse, ErrorDetail, ErrorMeta
from app.services.health import HealthService
from app.services.market import MarketService
from app.services.notifications import NotificationService
from app.services.weather import WeatherService

logging.basicConfig(level=logging.INFO)
# HTTPX logs full provider URLs at INFO, including the data.gov.in API key.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("agrivision.api")


async def add_request_id(request: Request, call_next):
    supplied_id = request.headers.get("X-Request-ID")
    try:
        request_id = UUID(supplied_id) if supplied_id else uuid4()
    except ValueError:
        request_id = uuid4()
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(request_id)
    return response


def request_id_for(request: Request) -> UUID:
    return getattr(request.state, "request_id", None) or uuid4()


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_by_status = {
        401: "unauthenticated",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        429: "rate_limited",
        503: "dependency_unavailable",
    }
    content = ApiErrorResponse(
        error=ErrorDetail(
            code=code_by_status.get(exc.status_code, "http_error"),
            message=exc.detail if isinstance(exc.detail, str) else "Request could not be completed.",
            retryable=exc.status_code in (429, 503),
        ),
        meta=ErrorMeta(request_id=request_id_for(request)),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=content.model_dump(mode="json"),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    fields = {
        ".".join(str(part) for part in error["loc"]): error["msg"]
        for error in exc.errors()
    }
    content = ApiErrorResponse(
        error=ErrorDetail(
            code="validation_error",
            message="One or more request fields are invalid.",
            fields=fields,
        ),
        meta=ErrorMeta(request_id=request_id_for(request)),
    )
    return JSONResponse(status_code=422, content=content.model_dump(mode="json"))


async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled request error; request_id=%s exception_type=%s",
        request_id_for(request),
        type(exc).__name__,
    )
    content = ApiErrorResponse(
        error=ErrorDetail(
            code="internal_error", message="An unexpected error occurred."
        ),
        meta=ErrorMeta(request_id=request_id_for(request)),
    )
    return JSONResponse(
        status_code=500,
        content=content.model_dump(mode="json"),
        headers={"X-Request-ID": str(content.meta.request_id)},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct an isolated app; lifespan owns and closes the shared HTTP pool."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.http_timeout_seconds),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        ) as http_client:
            connection = SupabaseConnection(settings, http_client)
            application.state.http_client = http_client
            application.state.supabase = connection
            application.state.market_service = MarketService(
                DataGovMarketAdapter(
                    http_client,
                    api_key=settings.data_gov_api_key.get_secret_value(),
                    resource_id=settings.data_gov_resource_id,
                ) if settings.data_gov_configured else None,
                SupabaseMarketRepository(connection) if settings.supabase_configured else None,
                CsvMarketRepository(settings.market_csv_path),
            )
            application.state.weather_service = WeatherService(
                OpenMeteoAdapter(http_client),
                SupabaseWeatherCacheRepository(connection) if settings.supabase_configured else None,
            )
            application.state.health_service = HealthService(
                SupabaseHealthRepository(
                    connection, timeout_seconds=settings.http_timeout_seconds
                ),
                configured=settings.supabase_configured,
            )
            application.state.notification_service = NotificationService(
                SupabaseNotificationRepository(connection),
                FirebaseMessagingAdapter(project_id=settings.firebase_project_id),
            )
            application.state.crop_health_agent = CropHealthAgent(
                GeminiAdapter(
                    http_client,
                    api_key=(settings.gemini_api_key.get_secret_value()
                             if settings.gemini_api_key else None),
                    model=settings.gemini_model,
                    timeout_seconds=settings.gemini_timeout_seconds,
                ),
                deadline_seconds=settings.gemini_timeout_seconds,
            )
            application.state.risk_agent = RiskAgent()
            application.state.outbreak_agent = OutbreakAgent(
                radius_km=settings.alert_radius_km,
                alert_threshold=settings.outbreak_risk_threshold,
            )
            yield

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    application.middleware("http")(add_request_id)
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, unexpected_exception_handler)
    application.include_router(api_router)
    return application


app = create_app()
