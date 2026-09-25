import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from app.agents.crop_health import CropHealthAgent
from app.agents.outbreak import OutbreakAgent
from app.agents.risk import RiskAgent
from app.core.config import Settings
from app.core.errors import AppError
from app.repositories.local import LocalRepository
from app.schemas.intelligence import ReportPublic
from app.services.nearby import NearbyReportService
from app.services.weather import WeatherService

ProgressCallback = Callable[[str, str], Awaitable[None]]


def season_for(when: datetime) -> str:
    month = when.month
    return "kharif" if 6 <= month <= 10 else "rabi" if month >= 11 or month <= 3 else "summer"


class ReportOrchestrator:
    def __init__(self, settings: Settings, repository: LocalRepository, crop_agent: CropHealthAgent, weather: WeatherService, nearby: NearbyReportService, risk: RiskAgent, outbreak: OutbreakAgent) -> None:
        self.settings = settings
        self.repository = repository
        self.crop_agent = crop_agent
        self.weather = weather
        self.nearby = nearby
        self.risk = risk
        self.outbreak = outbreak

    async def run(self, report_id: str, owner_id: str, on_progress: ProgressCallback | None = None) -> ReportPublic:
        report = await self.repository.get_report(report_id, owner_id)
        if not report:
            raise AppError(404, "report_not_found", "Report was not found.")
        if report.status == "completed":
            return report
        claim = await self.repository.claim_analysis(report_id, owner_id)
        if claim == "processing":
            raise AppError(409, "analysis_in_progress", "This report is already being analyzed.")
        if claim == "missing":
            raise AppError(404, "report_not_found", "Report was not found.")
        if claim == "completed":
            return (await self.repository.get_report(report_id, owner_id)) or report
        if not await self.repository.claim_rate(owner_id, "analysis", self.settings.analysis_rate_limit_per_hour, 3600):
            await self.repository.mark_failed(report_id, owner_id)
            raise AppError(429, "analysis_rate_limit", "Analysis limit reached. Try again later.")

        async def progress(stage: str, status: str = "running") -> None:
            await self.repository.update_stage(report_id, owner_id, stage)
            if on_progress:
                await on_progress(stage, status)

        try:
            await progress("weather")
            weather = await self.weather.get(report.latitude, report.longitude)
            weather_context = {"source": weather.source}
            if weather.current and not weather.stale:
                weather_context.update({"temperature_c": weather.current.temperature_c, "humidity_pct": weather.current.relative_humidity_pct, "precipitation_mm": weather.current.precipitation_mm})
            image = await self.repository.get_image(report_id, owner_id)
            if not image:
                raise AppError(422, "image_missing", "The report image is missing.")
            input_hash = await self.repository.get_input_hash(report_id, owner_id)
            if not input_hash:
                raise AppError(500, "report_invalid", "Report input could not be retrieved.")

            await progress("crop_health")
            crop_health = await self.crop_agent.evaluate(
                input_hash=input_hash, crop=report.crop, symptoms=report.symptom_description,
                notes=report.notes, season=season_for(report.created_at), image=image[0],
                mime_type=image[1], weather_context=weather_context,
            )
            await progress("nearby")
            matches = await self.nearby.matching(
                crop=report.crop, possible_problem=crop_health.finding.possible_problem,
                latitude=report.latitude, longitude=report.longitude, owner_id=owner_id, report_id=report_id,
            )
            await progress("risk")
            risk = self.risk.assess(crop_health, weather, matches, season_for(report.created_at))
            await progress("outbreak")
            outbreak = self.outbreak.detect(crop_health, matches, weather, allow_synthetic=self.settings.local_demo_mode)
            await progress("persist")
            await self.repository.save_result(report_id, owner_id, crop_health, weather, risk, outbreak, len(matches), sum(1 for match in matches if match.is_synthetic))
            result = await self.repository.get_report(report_id, owner_id)
            if not result:
                raise AppError(500, "persistence_failed", "Analysis result could not be retrieved.")
            if hasattr(self.repository, "add_notification"):
                from app.services.notifications import NotificationService
                notifier = NotificationService(self.repository)
                await notifier.notify(owner_id, "report_completed", "Crop report ready", f"Your {report.crop} field observation has been analyzed.", f"/result/{report_id}")
                if outbreak.nearby_alert:
                    await notifier.notify(owner_id, "possible_cluster", "Nearby crop cluster signal", outbreak.alert_reason, f"/result/{report_id}")
            if on_progress:
                await on_progress("complete", "completed")
            return result
        except asyncio.CancelledError:
            await self.repository.mark_failed(report_id, owner_id)
            raise
        except Exception:
            await self.repository.mark_failed(report_id, owner_id)
            raise
