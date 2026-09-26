import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app
from app.providers.groq import GroqProvider


@pytest.mark.asyncio
async def test_voice_status_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/voice/status")
        assert response.status_code == 200
        data = response.json()
        assert "groq_configured" in data
        assert "groq_model" in data
        assert "active_provider" in data


@pytest.mark.asyncio
async def test_voice_assist_telugu():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "query": "వరిలో ఆకులు పసుపు రంగులోకి మారుతున్నాయి, ఏమి చేయాలి?",
            "language": "te",
            "crop": "Paddy",
            "district": "Warangal",
        }
        response = await client.post("/api/voice/assist", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "te"
        assert len(data["reply"]) > 10
        # Should have quick actions
        assert isinstance(data["quick_actions"], list)


@pytest.mark.asyncio
async def test_voice_translation_fallback():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "text": "Cotton",
            "target_language": "te",
            "source_language": "en",
        }
        response = await client.post("/api/voice/translate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["target_language"] == "te"
        assert len(data["translated"]) > 0


@pytest.mark.asyncio
async def test_groq_provider_mock_response():
    class DummyClient:
        async def post(self, url, json=None, headers=None, timeout=None):
            class DummyResponse:
                status_code = 200

                def json(self):
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": "నమస్కారం రైతు సోదరా. వరిలో జింక్ లోపం వల్ల ఆకులు పసుపు రంగులోకి మారతాయి.\n1. జింక్ సల్ఫేట్ స్ప్రే చేయండి.\n2. నీటి నిల్వను తగ్గించండి."
                                }
                            }
                        ]
                    }

            return DummyResponse()

    settings = Settings(groq_api_key="gsk_mock_test_key_12345")
    provider = GroqProvider(settings, DummyClient())  # type: ignore
    assert provider.is_configured is True

    result = await provider.voice_assist("వరి ఆకులు", language="te")
    assert result.provider.startswith("groq")
    assert "నమస్కారం" in result.reply
    assert len(result.quick_actions) >= 1
