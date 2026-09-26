from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.intelligence import router as intelligence_router
from app.api.phase3 import router as phase3_router
from app.api.voice import router as voice_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.core.logging import configure_logging
from app.providers.supabase import supabase_client
from app.repositories.phase3 import Phase3LocalRepository
from app.knowledge.demo_generator import generate_demo_data
from app.core.security import DEMO_USER_ID
from datetime import datetime, timezone

settings = get_settings()
configure_logging(settings.app_log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with supabase_client(settings) as client:
        app.state.http_client = client
        if settings.local_demo_mode:
            repository = Phase3LocalRepository(settings.local_database_path)
            await repository.initialize()
            if settings.app_seed_demo_data:
                await repository.seed_demo_workspace(generate_demo_data(as_of=datetime.now(timezone.utc)), DEMO_USER_ID)
            app.state.local_repository = repository
        yield


app = FastAPI(title="AgriVision AI API", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = str(uuid4())
    if request.url.path == "/api/reports" and request.method == "POST":
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > settings.app_max_upload_mb * 1024 * 1024 + 1024 * 1024:
            return JSONResponse(status_code=413, content={"code": "upload_too_large", "message": "Image exceeds the upload limit.", "request_id": request.state.request_id})
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
app.include_router(router)
app.include_router(intelligence_router)
app.include_router(phase3_router)
app.include_router(voice_router)
