import hashlib
import json
from io import BytesIO
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import aiosqlite
import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.agents.crop_health import CropHealthAgent
from app.agents.outbreak import OutbreakAgent
from app.agents.risk import RiskAgent
from app.api.intelligence import get_repository, weather_service
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.uploads import UploadPolicy
from app.knowledge.demo_generator import generate_demo_data
from app.main import app
from app.providers.mistral import AIProviderError, MistralProvider
from app.providers.open_meteo import OpenMeteoProvider, WeatherProviderError
from app.repositories.local import LocalRepository
from app.schemas.intelligence import AIStatus, CropHealthFinding, CropHealthResult, NearbyMatch, Severity, WeatherResult
from app.services.location import haversine_km
from app.services.nearby import NearbyReportService
from app.services.weather import WeatherService


FINDING = {
    "possible_problem": "Whitefly activity", "confidence": 0.81, "severity": "moderate",
    "symptoms": ["Insects beneath leaves"], "possible_causes": ["Possible whitefly presence"],
    "immediate_actions": ["Inspect affected plants"], "precautions": ["Avoid unverified treatment"],
    "monitoring": ["Recheck in two days"], "expert_verification": "Ask a local agronomist to verify the issue.",
    "spread_potential": "moderate",
}


def png_bytes():
    stream = BytesIO()
    Image.new("RGB", (16, 16), color="green").save(stream, format="PNG")
    return stream.getvalue()


def weather_payload():
    return {
        "current": {"temperature_2m": 29, "relative_humidity_2m": 88, "precipitation": 1.2, "wind_speed_10m": 8, "weather_code": 3, "time": "2026-09-26T12:00"},
        "daily": {"time": ["2026-09-26"], "temperature_2m_max": [32], "temperature_2m_min": [23], "precipitation_sum": [6], "precipitation_probability_max": [70], "weather_code": [3]},
        "hourly": {"time": ["2026-09-26T12:00"], "temperature_2m": [29], "relative_humidity_2m": [88], "precipitation_probability": [70]},
    }


async def repository(tmp_path):
    result = LocalRepository(str(tmp_path / "test.sqlite3"))
    await result.initialize()
    return result


@pytest.mark.asyncio
async def test_mistral_available_strict_schema_and_image():
    seen = {}
    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(FINDING)}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await MistralProvider(Settings(_env_file=None, mistral_api_key="test-key", mistral_max_retries=0), client).analyze_crop(b"\x89PNG\r\n\x1a\n", "image/png", {"crop": "Cotton"})
    assert result.possible_problem == "Whitefly activity"
    assert seen["model"] == "mistral-small-latest"
    assert seen["response_format"]["type"] == "json_schema"
    assert seen["messages"][1]["content"][1]["image_url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
@pytest.mark.parametrize("status,code", [(429, "rate_limited"), (503, "provider_unavailable"), (404, "model_unavailable")])
async def test_mistral_http_failures(status, code):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(status))) as client:
        with pytest.raises(AIProviderError, match=code):
            await MistralProvider(Settings(_env_file=None, mistral_api_key="test-key", mistral_max_retries=0), client).analyze_crop(b"image", "image/png", {})


@pytest.mark.asyncio
async def test_mistral_retries_429_then_succeeds(monkeypatch):
    attempts = 0
    async def no_wait(_):
        return None
    monkeypatch.setattr("app.providers.mistral.asyncio.sleep", no_wait)
    def handler(_):
        nonlocal attempts
        attempts += 1
        return httpx.Response(429) if attempts == 1 else httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(FINDING)}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await MistralProvider(Settings(_env_file=None, mistral_api_key="test-key", mistral_max_retries=1), client).analyze_crop(b"image", "image/png", {})
    assert attempts == 2 and result.confidence == 0.81


@pytest.mark.asyncio
@pytest.mark.parametrize("error,code", [(httpx.ConnectError("offline"), "network_failure"), (httpx.ReadTimeout("slow"), "timeout")])
async def test_mistral_transport_failures(error, code):
    def handler(_):
        raise error
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AIProviderError, match=code):
            await MistralProvider(Settings(_env_file=None, mistral_api_key="test-key", mistral_max_retries=0), client).analyze_crop(b"image", "image/png", {})


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["not json", json.dumps({**FINDING, "confidence": 2})])
async def test_mistral_rejects_malformed_or_invalid_schema(content):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": [{"message": {"content": content}}]}))) as client:
        with pytest.raises(AIProviderError, match="invalid_response"):
            await MistralProvider(Settings(_env_file=None, mistral_api_key="test-key", mistral_max_retries=0), client).analyze_crop(b"image", "image/png", {})


@pytest.mark.asyncio
async def test_missing_key_and_local_knowledge_fallback(tmp_path):
    repo = await repository(tmp_path)
    async with httpx.AsyncClient() as client:
        provider = MistralProvider(Settings(_env_file=None, mistral_api_key=""), client)
        with pytest.raises(AIProviderError, match="missing_api_key"):
            await provider.analyze_crop(b"image", "image/png", {})
        result = await CropHealthAgent(provider, repo, "mistral-small-latest").evaluate(input_hash="h1", crop="Cotton", symptoms="Small white insects under leaves and yellowing", notes=None, season="kharif", image=b"image", mime_type="image/png", weather_context={})
    assert result.source == AIStatus.LOCAL_KNOWLEDGE
    assert result.image_assessed is False
    assert result.finding.confidence < 0.65
    class Down:
        async def analyze_crop(self, *_):
            raise AIProviderError("provider_unavailable")
    down = await CropHealthAgent(Down(), repo, "mistral-small-latest").evaluate(input_hash="h2", crop="Cotton", symptoms="Small white insects under leaves and yellowing", notes=None, season="kharif", image=b"image", mime_type="image/png", weather_context={})
    assert down.source == AIStatus.LOCAL_KNOWLEDGE and "provider_unavailable" in down.limitation


@pytest.mark.asyncio
async def test_ai_cache_is_labelled_cached(tmp_path):
    repo = await repository(tmp_path)
    key = hashlib.sha256(('same-image' + json.dumps({"season": "kharif", "weather": {}}, sort_keys=True)).encode()).hexdigest()
    await repo.ai_cache_put(key, CropHealthResult(finding=CropHealthFinding.model_validate(FINDING), source=AIStatus.LIVE, model="mistral-small-latest", image_assessed=True, analyzed_at=datetime.now(timezone.utc)))
    class NeverCall:
        async def analyze_crop(self, *_):
            raise AssertionError("cached AI result should avoid provider")
    result = await CropHealthAgent(NeverCall(), repo, "mistral-small-latest").evaluate(input_hash="same-image", crop="Cotton", symptoms="Insects", notes=None, season="kharif", image=b"image", mime_type="image/png", weather_context={})
    assert result.source == AIStatus.CACHED


@pytest.mark.asyncio
async def test_weather_live_cache_stale_and_unavailable(tmp_path):
    repo = await repository(tmp_path)
    settings = Settings(_env_file=None)
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=weather_payload())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WeatherService(settings, OpenMeteoProvider(settings, client), repo)
        live = await service.get(17.25, 78.39)
        cached = await service.get(17.25, 78.39)
    assert live.source == "LIVE" and live.current.relative_humidity_pct == 88
    assert len(live.hourly) == 1 and len(live.daily) == 1
    assert cached.source == "CACHED" and len(calls) == 1
    async with aiosqlite.connect(repo.path) as db:
        await db.execute("update weather_cache_local set expires_at=?", ((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),))
        await db.commit()
    class Down:
        async def forecast(self, *_):
            raise WeatherProviderError("down")
    stale = await WeatherService(settings, Down(), repo).get(17.25, 78.39)
    unavailable = await WeatherService(settings, Down(), repo).get(18.0, 79.0)
    assert stale.source == "CACHED" and stale.stale is True
    assert unavailable.source == "LOCAL KNOWLEDGE" and unavailable.current is None
    assert unavailable.is_synthetic is False


def test_haversine_and_coordinate_validation():
    assert haversine_km(17, 78, 17, 78) == pytest.approx(0)
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.2, abs=0.2)
    assert haversine_km(17.2, 78.3, 17.3, 78.4) == pytest.approx(haversine_km(17.3, 78.4, 17.2, 78.3))


def test_upload_size_and_decoding():
    policy = UploadPolicy(1_000_000)
    policy.validate("image/png", png_bytes())
    with pytest.raises(AppError) as large:
        UploadPolicy(8).validate("image/png", png_bytes())
    assert large.value.status_code == 413
    with pytest.raises(AppError) as invalid:
        policy.validate("image/png", b"\x89PNG\r\n\x1a\ntruncated")
    assert invalid.value.status_code == 415


@pytest.mark.asyncio
async def test_nearby_excludes_owner_and_public_clusters_are_coarse(tmp_path):
    repo = await repository(tmp_path)
    sample = generate_demo_data(as_of=datetime.now(timezone.utc))
    await repo.seed_synthetic(sample["reports"])
    item = sample["reports"][0]
    service = NearbyReportService(repo)
    matches = await service.matching(crop=item["crop"], possible_problem=item["possible_problem"], latitude=item["latitude"], longitude=item["longitude"], owner_id=item["owner_id"], report_id=item["id"])
    assert matches and all(match.owner_id != item["owner_id"] for match in matches)
    assert all(match.distance_km <= 10 for match in matches)
    alerts = await service.public_alerts(crop="Cotton", latitude=17.2517, longitude=78.3893, include_synthetic=True)
    assert alerts and all(item.cluster_size >= 3 and item.is_synthetic for item in alerts)
    assert all(round(item.latitude, 2) == item.latitude and round(item.longitude, 2) == item.longitude for item in alerts)
    assert await service.public_alerts(crop="Cotton", latitude=17.2517, longitude=78.3893, include_synthetic=False) == []


@pytest.mark.asyncio
async def test_atomic_claim_rate_limit_and_private_image(tmp_path):
    repo = await repository(tmp_path)
    report = await repo.create_report("owner-a", "Cotton", "North Field", "Rangareddy", "White insects beneath leaves", None, 17.25, 78.39, png_bytes(), "image/png", "unique")
    assert await repo.get_image(str(report.id), "owner-b") is None
    assert await repo.get_report(str(report.id), "owner-b") is None
    assert await repo.claim_analysis(str(report.id), "owner-a") == "claimed"
    assert await repo.claim_analysis(str(report.id), "owner-a") == "processing"
    assert await repo.claim_rate("owner-a", "analysis", 1, 3600)
    assert not await repo.claim_rate("owner-a", "analysis", 1, 3600)


def test_outbreak_is_conservative_and_synthetic_not_in_risk():
    finding = CropHealthFinding.model_validate(FINDING)
    report = CropHealthResult(finding=finding, source=AIStatus.LIVE, analyzed_at=datetime.now(timezone.utc))
    nearby = [NearbyMatch(report_id=uuid4(), owner_id=str(i), crop="Cotton", possible_problem="Whitefly activity", severity=Severity.MODERATE, distance_km=1, age_hours=3, is_synthetic=True) for i in range(3)]
    weather = WeatherResult(latitude=17, longitude=78, source="LOCAL KNOWLEDGE")
    assert not OutbreakAgent().detect(report, nearby, weather).nearby_alert
    synthetic = OutbreakAgent().detect(report, nearby, weather, allow_synthetic=True)
    assert synthetic.nearby_alert and synthetic.evidence_is_synthetic
    assert RiskAgent().assess(report, weather, nearby, "kharif").community_risk == RiskAgent().assess(report, weather, [], "kharif").community_risk
    weak = report.model_copy(update={"finding": finding.model_copy(update={"confidence": 0.5})})
    assert not OutbreakAgent().detect(weak, nearby, weather, allow_synthetic=True).nearby_alert
    duplicates = [match.model_copy(update={"owner_id": "one-farmer"}) for match in nearby]
    assert not OutbreakAgent().detect(report, duplicates, weather, allow_synthetic=True).nearby_alert
    mixed = [nearby[0], nearby[1].model_copy(update={"is_synthetic": False}), nearby[2].model_copy(update={"is_synthetic": False})]
    assert not OutbreakAgent().detect(report, mixed, weather, allow_synthetic=True).nearby_alert
    real = [match.model_copy(update={"is_synthetic": False}) for match in nearby]
    verified = OutbreakAgent().detect(report, real + nearby, weather, allow_synthetic=True)
    assert verified.nearby_alert and not verified.evidence_is_synthetic and verified.cluster_size == 3


@pytest.mark.asyncio
async def test_report_http_flow_validation_stream_and_idempotence(tmp_path):
    repo = await repository(tmp_path)
    class OfflineWeather:
        async def get(self, latitude, longitude):
            return WeatherResult(latitude=latitude, longitude=longitude, source="LOCAL KNOWLEDGE", stale=True, agricultural_indicators=["Weather unavailable"])
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[weather_service] = lambda: OfflineWeather()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, demo_mode=True, mistral_api_key="", ogd_api_key="")
    try:
        with TestClient(app) as client:
            payload = {"crop": "Cotton", "field": "North Field", "district": "Rangareddy", "symptoms": "White insects beneath the lower leaves", "latitude": "17.2517", "longitude": "78.3893"}
            invalid = client.post("/api/reports", data=payload, files={"image": ("bad.png", b"plain text", "image/png")})
            assert invalid.status_code == 415
            truncated = client.post("/api/reports", data=payload, files={"image": ("bad.png", b"\x89PNG\r\n\x1a\nexample", "image/png")})
            assert truncated.status_code == 415
            created = client.post("/api/reports", data=payload, files={"image": ("crop.png", png_bytes(), "image/png")})
            assert created.status_code == 201, created.text
            report_id = created.json()["id"]
            assert client.get(f"/api/reports/{report_id}/image").status_code == 200
            assert client.get("/api/reports").json()[0]["id"] == report_id
            response = client.post(f"/api/reports/{report_id}/analyze/stream")
            assert response.status_code == 200
            events = [json.loads(line) for line in response.text.splitlines()]
            assert [item["stage"] for item in events] == ["weather", "crop_health", "nearby", "risk", "outbreak", "persist", "complete", "result"]
            result = events[-1]["report"]
            assert result["status"] == "completed" and result["crop_health"]["source"] == "LOCAL KNOWLEDGE"
            assert result["weather"]["current"] is None
            assert client.post(f"/api/reports/{report_id}/analyze").json()["status"] == "completed"
            assert client.get(f"/api/reports/{uuid4()}").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_demo_generator_reproducible():
    first = generate_demo_data()
    second = generate_demo_data()
    assert first == second
    assert len(first["farmers"]) >= 100 and len(first["reports"]) >= 300
    assert all(item["is_synthetic"] for item in first["reports"])
