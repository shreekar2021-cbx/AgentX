from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
from uuid import uuid4
import json

import aiosqlite
import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.agents.market_intelligence import MarketIntelligenceAgent
from app.agents.recommendations import FertilizerAgent, SeedRecommendationAgent
from app.api.intelligence import get_repository, weather_service
from app.core.config import Settings, get_settings
from app.main import app
from app.providers.ogd_market import MarketProviderError, OGDMarketProvider
from app.providers.mistral import MistralProvider
from app.repositories.phase3 import Phase3LocalRepository
from app.schemas.phase3 import FarmProfileInput, MarketAIResult, MarketEstimateInput, MarketQuote
from app.schemas.intelligence import WeatherResult
from app.services.market import MarketService, estimate_return
from app.services.notifications import NotificationService


async def repository(tmp_path):
    repo = Phase3LocalRepository(str(tmp_path / "phase3.sqlite3"))
    await repo.initialize()
    return repo


def png_bytes():
    output = BytesIO()
    Image.new("RGB", (8, 8), "green").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_ogd_market_live_normalization():
    body = {"records": [{"commodity": "Cotton", "variety": "Local", "state": "Telangana", "district": "Warangal", "market": "Warangal", "arrival_date": "26/09/2026", "min_price": "6000", "max_price": "6400", "modal_price": "6200"}]}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))) as client:
        rows = await OGDMarketProvider(Settings(_env_file=None, ogd_api_key="test-key"), client).quotes("Cotton")
    assert len(rows) == 1 and rows[0].modal_price == 6200
    assert rows[0].source == "LIVE" and rows[0].is_synthetic is False


@pytest.mark.asyncio
async def test_market_cache_and_fallback(tmp_path):
    repo = await repository(tmp_path)
    class Live:
        calls = 0
        async def quotes(self, _):
            self.calls += 1
            return [MarketQuote(commodity="Cotton", variety="Local", state="Telangana", district="Warangal", mandi="Warangal", min_price=6000, max_price=6400, modal_price=6200, date=date(2026, 9, 26), source="LIVE", is_synthetic=False, provenance="OGD test")]
    provider = Live()
    service = MarketService(Settings(_env_file=None), provider, repo)
    live = await service.get("Cotton")
    cached = await service.get("Cotton")
    assert live.source == "LIVE" and cached.source == "CACHED" and provider.calls == 1
    async with aiosqlite.connect(repo.path) as db:
        await db.execute("update market_cache set expires_at=?", ("2020-01-01T00:00:00+00:00",))
        await db.commit()
    class Down:
        async def quotes(self, _):
            raise MarketProviderError("offline")
    stale = await MarketService(Settings(_env_file=None), Down(), repo).get("Cotton")
    assert stale.source == "CACHED" and stale.stale
    fallback = await MarketService(Settings(_env_file=None), Down(), repo).get("Paddy")
    assert fallback.source == "FALLBACK" and fallback.is_synthetic and fallback.stale
    assert len(fallback.quotes) >= 10 and len(fallback.history_30d) == 30
    assert fallback.last_updated == date(2026, 8, 31)


@pytest.mark.asyncio
async def test_market_trend_agent_and_cache(tmp_path):
    repo = await repository(tmp_path)
    class Down:
        async def quotes(self, _):
            raise MarketProviderError("offline")
    market = await MarketService(Settings(_env_file=None), Down(), repo).get("Cotton")
    class AI:
        calls = 0
        async def classify_market(self, context):
            self.calls += 1
            assert len(context["history"]) == 30
            return MarketAIResult(trend="RISING", confidence=0.7, reasoning_summary="Average prices increased across the supplied observations.", forecast_horizon="Recent 30-day pattern")
    provider = AI()
    agent = MarketIntelligenceAgent(provider, repo, Settings(_env_file=None))
    live = await agent.analyze(market)
    cached = await agent.analyze(market)
    assert live.source == "AI LIVE" and live.trend == "RISING"
    assert cached.source == "AI CACHED" and provider.calls == 1
    class Unavailable:
        async def classify_market(self, _):
            from app.providers.mistral import AIProviderError
            raise AIProviderError("offline")
    other = await MarketService(Settings(_env_file=None), Down(), repo).get("Paddy")
    deterministic = await MarketIntelligenceAgent(Unavailable(), repo, Settings(_env_file=None)).analyze(other)
    assert deterministic.source == "DETERMINISTIC" and deterministic.trend in ("RISING", "STABLE", "FALLING")


@pytest.mark.asyncio
async def test_mistral_market_structured_response():
    seen = {}
    def handler(request):
        seen.update(json.loads(request.content))
        body = {"trend": "STABLE", "confidence": 0.62, "reasoning_summary": "Recent average prices changed very little across available dates.", "forecast_horizon": "Past seven observations"}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(body)}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await MistralProvider(Settings(_env_file=None, mistral_api_key="test-key", mistral_max_retries=0), client).classify_market({"commodity": "Cotton", "history": [{"date": "2026-09-26", "modal_price": 6000}]})
    assert result.trend == "STABLE" and result.confidence == 0.62
    assert seen["model"] == "ministral-8b-latest"
    assert seen["response_format"]["type"] == "json_schema"


def test_financial_calculation_is_decimal_and_deterministic():
    values = MarketEstimateInput(quantity_quintals=Decimal("10"), modal_price_per_quintal=Decimal("6000"), distance_km=Decimal("20"), transport_cost_per_km=Decimal("15"), handling_cost_per_quintal=Decimal("30"), storage_cost=Decimal("100"), spoilage_percent=Decimal("2"))
    result = estimate_return(values)
    assert result.gross_revenue == Decimal("60000.00")
    assert result.total_cost == Decimal("1900.00")
    assert result.estimated_net_return == Decimal("58100.00")


@pytest.mark.asyncio
async def test_farm_soil_crop_and_notification_persistence(tmp_path):
    repo = await repository(tmp_path)
    profile = FarmProfileInput(farm_name="Green Valley", district="Rangareddy", soil_ph=7.2, nitrogen_kg_ha=280, lab_status={"N": "low"}, crop="Cotton", season="kharif", soil_type="loam", irrigation="rainfed")
    await repo.save_farm_profile("owner-a", profile.model_dump(mode="json"))
    assert (await repo.get_farm_profile("owner-a"))["nitrogen_kg_ha"] == 280
    assert await repo.get_farm_profile("owner-b") is None
    crop = await repo.save_crop("owner-a", {"crop": "Cotton", "field": "North Field", "health_status": "watch"})
    assert len(await repo.list_portfolio("owner-a")) == 1
    assert await repo.list_portfolio("owner-b") == []
    assert not await repo.delete_crop("owner-b", crop["id"])
    item = await repo.add_notification("owner-a", "report_completed", "Ready", "Report done")
    assert len(await repo.list_notifications("owner-a")) == 1
    assert await repo.list_notifications("owner-b") == []
    assert not await repo.mark_notification_read("owner-b", item["id"])
    assert await repo.mark_notification_read("owner-a", item["id"])


def test_seed_and_fertilizer_recommendations_allow_partial_data():
    partial = FarmProfileInput(crop="Cotton")
    seed = SeedRecommendationAgent().recommend(partial)
    nutrient = FertilizerAgent().recommend(partial)
    assert seed.suitability == "insufficient_data" and seed.is_product_recommendation is False
    assert nutrient.exact_dose_provided is False and nutrient.possible_deficiencies == []
    measured = FarmProfileInput(crop="Cotton", season="kharif", soil_type="loam", irrigation="rainfed", nitrogen_kg_ha=270, lab_status={"N": "low"})
    result = FertilizerAgent().recommend(measured)
    assert any("N deficiency" in item for item in result.possible_deficiencies)
    assert "Lab marked low" == result.nutrient_status["N"]


@pytest.mark.asyncio
async def test_notification_failure_never_breaks_caller(tmp_path):
    repo = await repository(tmp_path)
    async def broken(*_):
        raise RuntimeError("notification store down")
    repo.add_notification = broken
    await NotificationService(repo).notify("owner", "report_completed", "Ready", "Done")


@pytest.mark.asyncio
async def test_report_idempotency_for_offline_replay(tmp_path):
    repo = await repository(tmp_path)
    mutation_id = str(uuid4())
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        with TestClient(app) as client:
            data = {"crop": "Cotton", "field": "North Field", "district": "Rangareddy", "symptoms": "White insects below many leaves", "latitude": "17.25", "longitude": "78.39", "client_mutation_id": mutation_id}
            first = client.post("/api/reports", data=data, files={"image": ("field.png", png_bytes(), "image/png")})
            second = client.post("/api/reports", data=data, files={"image": ("field.png", png_bytes(), "image/png")})
            assert first.status_code == second.status_code == 201
            assert first.json()["id"] == second.json()["id"]
            assert len(client.get("/api/reports").json()) == 1
            changed = {**data, "symptoms": "A different set of field symptoms"}
            conflict = client.post("/api/reports", data=changed, files={"image": ("field.png", png_bytes(), "image/png")})
            assert conflict.status_code == 409 and conflict.json()["code"] == "idempotency_conflict"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_phase3_http_farm_market_recommendation_notification_and_health(tmp_path):
    repo = await repository(tmp_path)
    class OfflineWeather:
        async def get(self, latitude, longitude):
            return WeatherResult(latitude=latitude, longitude=longitude, source="LOCAL KNOWLEDGE", stale=True)
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[weather_service] = lambda: OfflineWeather()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, demo_mode=True, mistral_api_key="", ogd_api_key="")
    try:
        with TestClient(app) as client:
            saved = client.put("/api/farms/profile", json={"farm_name": "Green Valley", "crop": "Cotton", "season": "kharif", "soil_type": "loam", "irrigation": "rainfed", "soil_ph": 7.1, "lab_status": {"N": "low"}})
            assert saved.status_code == 200, saved.text
            assert client.get("/api/farms/profile").json()["farm_name"] == "Green Valley"
            crop = client.post("/api/portfolio", json={"crop": "Cotton", "field": "North Field", "health_status": "watch"})
            assert crop.status_code == 201
            assert client.get("/api/portfolio").json()[0]["field"] == "North Field"
            seed = client.post("/api/recommendations/seed", json=saved.json())
            nutrient = client.post("/api/recommendations/fertilizer", json=saved.json())
            assert seed.status_code == 200 and not seed.json()["is_product_recommendation"]
            assert nutrient.status_code == 200 and not nutrient.json()["exact_dose_provided"]
            market = client.get("/api/market/prices", params={"commodity": "Cotton", "district": "Warangal"})
            assert market.status_code == 200 and market.json()["source"] == "FALLBACK" and market.json()["is_synthetic"]
            trend = client.post("/api/market/trend", json={"commodity": "Cotton", "district": "Warangal"})
            assert trend.status_code == 200 and trend.json()["source"] == "DETERMINISTIC"
            estimate = client.post("/api/market/estimate", json={"quantity_quintals": 10, "modal_price_per_quintal": 6000, "distance_km": 20, "transport_cost_per_km": 15, "handling_cost_per_quintal": 30, "storage_cost": 100, "spoilage_percent": 2})
            assert estimate.status_code == 200 and estimate.json()["estimated_net_return"] == "58100.00"
            payload = {"crop": "Cotton", "field": "North Field", "district": "Rangareddy", "symptoms": "White insects beneath lower leaves", "latitude": "17.25", "longitude": "78.39"}
            report = client.post("/api/reports", data=payload, files={"image": ("crop.png", png_bytes(), "image/png")})
            assert report.status_code == 201
            analyzed = client.post(f"/api/reports/{report.json()['id']}/analyze")
            assert analyzed.status_code == 200 and analyzed.json()["status"] == "completed"
            notifications = client.get("/api/notifications")
            assert notifications.status_code == 200 and notifications.json()[0]["kind"] == "report_completed"
            notification_id = notifications.json()[0]["id"]
            assert client.patch(f"/api/notifications/{notification_id}/read").json()["read_at"]
            health = client.get("/api/provider-health")
            assert health.status_code == 200
            assert {item["name"] for item in health.json()["providers"]} == {"mistral", "weather", "market", "database", "notifications"}
    finally:
        app.dependency_overrides.clear()
