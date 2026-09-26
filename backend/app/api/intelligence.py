import asyncio
import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.agents.crop_health import CropHealthAgent
from app.agents.outbreak import OutbreakAgent
from app.agents.risk import RiskAgent
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import Principal, current_principal
from app.core.uploads import UploadPolicy
from app.knowledge.catalog import CROPS, ISSUES, normalize_crop
from app.providers.groq import GroqProvider
from app.providers.mistral import MistralProvider
from app.providers.open_meteo import OpenMeteoProvider
from app.repositories.local import LocalRepository
from app.schemas.intelligence import CropHealthFinding, NearbyAlertPublic, ReportPublic, WeatherResult
from app.services.location import validate_coordinates
from app.services.nearby import NearbyReportService
from app.services.report_orchestrator import ReportOrchestrator
from app.services.weather import WeatherService

router = APIRouter(prefix="/api", tags=["intelligence"])


def get_repository(request: Request, settings: Settings = Depends(get_settings)) -> LocalRepository:
    if not settings.local_demo_mode:
        raise AppError(503, "repository_unavailable", "The authenticated report repository is not configured.")
    return request.app.state.local_repository


def weather_service(request: Request, repository: LocalRepository = Depends(get_repository), settings: Settings = Depends(get_settings)) -> WeatherService:
    return WeatherService(settings, OpenMeteoProvider(settings, request.app.state.http_client), repository)


def report_orchestrator(request: Request, repository: LocalRepository = Depends(get_repository), weather: WeatherService = Depends(weather_service), settings: Settings = Depends(get_settings)) -> ReportOrchestrator:
    crop_agent = CropHealthAgent(MistralProvider(settings, request.app.state.http_client), repository, settings.mistral_model_vision)
    nearby = NearbyReportService(repository, settings.nearby_radius_km)
    return ReportOrchestrator(settings, repository, crop_agent, weather, nearby, RiskAgent(), OutbreakAgent())


@router.get("/knowledge/crops")
async def knowledge_crops() -> dict:
    return {"source": "CURATED STATIC KNOWLEDGE", "version": "2026-09-26", "crops": [{"name": crop.name, "stages": crop.stages, "seasons": crop.seasons} for crop in CROPS.values()], "issue_count": len(ISSUES)}


@router.post("/reports", response_model=ReportPublic, status_code=201)
async def create_report(
    crop: str = Form(...), field: str = Form(...), district: str = Form(...),
    symptoms: str = Form(...), notes: str | None = Form(None), client_mutation_id: UUID | None = Form(None), demo_sample: bool = Form(False),
    latitude: float = Form(...), longitude: float = Form(...),
    image: UploadFile = File(...),
    principal: Principal = Depends(current_principal),
    repository: LocalRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> ReportPublic:
    if normalize_crop(crop) not in CROPS:
        raise AppError(422, "unsupported_crop", "Select a crop from the supported crop list.")
    if not 1 <= len(field.strip()) <= 120 or not 1 <= len(district.strip()) <= 80:
        raise AppError(422, "invalid_field", "Field and district are required.")
    if not 10 <= len(symptoms.strip()) <= 4000 or (notes and len(notes) > 4000):
        raise AppError(422, "invalid_description", "Describe symptoms in 10 to 4000 characters.")
    validate_coordinates(latitude, longitude)
    max_bytes = settings.app_max_upload_mb * 1024 * 1024
    content = await image.read(max_bytes + 1)
    UploadPolicy(max_bytes).validate(image.content_type or "", content)
    if not await repository.claim_rate(principal.user_id, "report_create", settings.app_rate_limit_per_minute, 60):
        raise AppError(429, "report_rate_limit", "Too many report submissions. Try again shortly.")
    normalized_crop = CROPS[normalize_crop(crop)].name
    digest = hashlib.sha256()
    digest.update(json.dumps([normalized_crop, symptoms.strip(), (notes or "").strip(), round(latitude, 3), round(longitude, 3), demo_sample], ensure_ascii=False).encode())
    digest.update(content)
    return await repository.create_report(principal.user_id, normalized_crop, field.strip(), district.strip(), symptoms.strip(), notes.strip() if notes else None, latitude, longitude, content, image.content_type or "", digest.hexdigest(), str(client_mutation_id) if client_mutation_id else None, is_synthetic=demo_sample and settings.local_demo_mode)


@router.get("/reports", response_model=list[ReportPublic])
async def list_reports(principal: Principal = Depends(current_principal), repository: LocalRepository = Depends(get_repository)) -> list[ReportPublic]:
    return await repository.list_reports(principal.user_id)


_TRANSLATED_FINDINGS_CACHE: dict[str, CropHealthFinding] = {}


def _localize_risk_factors(factors: list[str], lang: str) -> list[str]:
    if lang != "te":
        return factors

    severity_map = {"low": "తక్కువ", "moderate": "మధ్యస్థం", "high": "ఎక్కువ"}
    season_map = {
        "monsoon": "వర్షాకాలం / ఖరీఫ్",
        "kharif": "ఖరీఫ్",
        "rabi": "రబీ",
        "summer": "వేసవి",
        "zaid": "జాయెద్",
    }

    localized = []
    for f in factors:
        lower = f.lower()
        if lower.startswith("possible issue severity:"):
            val = f.split(":", 1)[1].strip()
            localized.append(f"సంభావ్య సమస్య తీవ్రత: {severity_map.get(val.lower(), val)}")
        elif lower.startswith("assessment confidence:"):
            val = f.split(":", 1)[1].strip()
            localized.append(f"అంచనా విశ్వసనీయత: {val}")
        elif lower.startswith("spread potential:"):
            val = f.split(":", 1)[1].strip()
            localized.append(f"వ్యాప్తి సంభావ్యత: {severity_map.get(val.lower(), val)}")
        elif lower.startswith("reported season:"):
            val = f.split(":", 1)[1].strip()
            localized.append(f"నివేదించబడిన కాలం: {season_map.get(val.lower(), val)}")
        elif "recent nearby field reports" in lower:
            count = f.split()[0]
            localized.append(f"{count} సమీప పొలాల పరిశీలనలు")
        elif "current high humidity may favor spread" in lower:
            localized.append("ప్రస్తుత అధిక తేమ తెగులు వ్యాప్తికి అనుకూలంగా ఉండవచ్చు")
        elif "synthetic sample" in lower:
            localized.append("సింథటిక్ నమూనా; ప్రత్యక్ష వాతావరణం లేదా క్షేత్ర అంచనా లేదు")
        else:
            localized.append(f)
    return localized


def _localize_outbreak(reason: str | None, lang: str) -> str | None:
    if not reason or lang != "te":
        return reason
    if "No conservative outbreak threshold was met" in reason:
        return "ఎలాంటి తీవ్ర వ్యాప్తి హెచ్చరిక పరిమితి నమోదు కాలేదు. సాధారణ పర్యవేక్షణ కొనసాగించండి."
    return reason


@router.get("/reports/{report_id}", response_model=ReportPublic)
async def get_report(
    report_id: UUID,
    request: Request,
    language: str = Query("en"),
    principal: Principal = Depends(current_principal),
    repository: LocalRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> ReportPublic:
    report = await repository.get_report(str(report_id), principal.user_id)
    if not report:
        raise AppError(404, "report_not_found", "Report was not found.")

    lang = language.lower().strip()
    if lang in ("te", "hi"):
        if report.crop_health and report.crop_health.finding:
            cache_key = f"{report.id}:{lang}"
            if cache_key in _TRANSLATED_FINDINGS_CACHE:
                report.crop_health.finding = _TRANSLATED_FINDINGS_CACHE[cache_key]
            else:
                finding = report.crop_health.finding
                is_already_translated = False
                if lang == "te" and any("\u0c00" <= ch <= "\u0c7f" for ch in finding.possible_problem):
                    is_already_translated = True
                elif lang == "hi" and any("\u0900" <= ch <= "\u097f" for ch in finding.possible_problem):
                    is_already_translated = True

                if not is_already_translated:
                    client = getattr(request.app.state, "http_client", None) if request else None
                    groq = GroqProvider(settings, client)
                    try:
                        translated_dict = await groq.translate_finding(finding.model_dump(), target_language=lang)
                        translated_finding = CropHealthFinding.model_validate(translated_dict)
                        report.crop_health.finding = translated_finding
                        _TRANSLATED_FINDINGS_CACHE[cache_key] = translated_finding
                    except Exception:
                        pass

        if lang == "te":
            if report.risk and report.risk.risk_factors:
                report.risk.risk_factors = _localize_risk_factors(report.risk.risk_factors, "te")
            if report.outbreak and report.outbreak.alert_reason:
                report.outbreak.alert_reason = _localize_outbreak(report.outbreak.alert_reason, "te")

    return report


@router.get("/reports/{report_id}/image")
async def get_report_image(report_id: UUID, principal: Principal = Depends(current_principal), repository: LocalRepository = Depends(get_repository)) -> Response:
    image = await repository.get_image(str(report_id), principal.user_id)
    if not image:
        raise AppError(404, "image_not_found", "Image was not found.")
    return Response(content=image[0], media_type=image[1], headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/reports/{report_id}/analyze", response_model=ReportPublic)
async def analyze_report(report_id: UUID, principal: Principal = Depends(current_principal), orchestrator: ReportOrchestrator = Depends(report_orchestrator)) -> ReportPublic:
    return await orchestrator.run(str(report_id), principal.user_id)


@router.post("/reports/{report_id}/analyze/stream")
async def analyze_report_stream(report_id: UUID, principal: Principal = Depends(current_principal), orchestrator: ReportOrchestrator = Depends(report_orchestrator)) -> StreamingResponse:
    async def stream():
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def on_progress(stage: str, status: str) -> None:
            await queue.put({"stage": stage, "status": status})

        async def work() -> None:
            try:
                result = await orchestrator.run(str(report_id), principal.user_id, on_progress)
                await queue.put({"stage": "result", "status": "completed", "report": result.model_dump(mode="json")})
            except AppError as exc:
                await queue.put({"stage": "error", "status": "failed", "message": exc.message})
            except Exception:
                await queue.put({"stage": "error", "status": "failed", "message": "Analysis could not be completed. The report remains available for retry."})
            finally:
                await queue.put(None)

        task = asyncio.create_task(work())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield json.dumps(item) + "\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(stream(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.get("/weather", response_model=WeatherResult)
async def get_weather(
    latitude: float = Query(..., ge=-90, le=90), longitude: float = Query(..., ge=-180, le=180),
    principal: Principal = Depends(current_principal), service: WeatherService = Depends(weather_service),
) -> WeatherResult:
    return await service.get(latitude, longitude)


@router.get("/alerts/nearby", response_model=list[NearbyAlertPublic])
async def nearby_alerts(
    crop: str = Query(...), latitude: float = Query(..., ge=-90, le=90), longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10, ge=1, le=100), principal: Principal = Depends(current_principal),
    repository: LocalRepository = Depends(get_repository), settings: Settings = Depends(get_settings),
) -> list[NearbyAlertPublic]:
    if normalize_crop(crop) not in CROPS:
        raise AppError(422, "unsupported_crop", "Select a supported crop.")
    service = NearbyReportService(repository, settings.nearby_radius_km)
    return await service.public_alerts(crop=CROPS[normalize_crop(crop)].name, latitude=latitude, longitude=longitude, radius_km=radius_km, include_synthetic=settings.local_demo_mode)
