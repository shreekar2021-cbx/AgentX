"""Crop agent contract and Gemini adapter behavior with controlled provider output."""

import json
import unittest

import httpx
from pydantic import ValidationError

from app.adapters.gemini import GeminiAdapter
from app.agents.crop_health import CropHealthAgent
from app.schemas.crop_health import CropHealthInput, CropImage


def diagnosis(**changes):
    data = {
        "possible_problem": "Early blight",
        "confidence": 0.68,
        "severity": "medium",
        "symptoms": ["Brown spots on leaves"],
        "possible_causes": ["Fungal infection"],
        "immediate_actions": ["Remove badly affected leaves"],
        "precautions": ["Avoid wetting leaves"],
        "monitoring": ["Check new leaves each day"],
        "expert_verification": False,
        "spread_potential": "unknown",
    }
    data.update(changes)
    return data


def gemini_response(payload):
    return {"candidates": [{"finishReason": "STOP", "content": {
        "parts": [{"text": json.dumps(payload)}]
    }}]}


class CropHealthTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_analysis_uses_structured_json_and_stays_provisional(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json=gemini_response(diagnosis()))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            agent = CropHealthAgent(GeminiAdapter(
                client, api_key="test-key", model="gemini-3.8-flash"
            ))
            result = await agent.analyze(CropHealthInput(
                description="My tomato leaves have brown spots", crop_name="tomato"
            ))

        self.assertEqual(result.status, "complete")
        self.assertEqual(result.diagnosis_status, "unconfirmed")
        self.assertEqual(result.result.possible_problem, "Early blight")
        self.assertTrue(result.result.expert_verification)  # Guardrail overrides low-confidence model output.
        self.assertIn("possible problem", result.warnings[0])
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].headers["x-goog-api-key"], "test-key")
        body = json.loads(requests[0].content)
        self.assertEqual(body["generationConfig"]["responseFormat"]["text"]["mimeType"], "application/json")
        self.assertEqual(len(body["contents"][0]["parts"]), 1)

    async def test_image_is_sent_as_inline_data(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json=gemini_response(diagnosis(confidence=0.85)))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            agent = CropHealthAgent(GeminiAdapter(
                client, api_key="test-key", model="gemini-3.8-flash"
            ))
            result = await agent.analyze(CropHealthInput(
                image=CropImage(media_type="image/jpeg", data=b"prepared-image-bytes")
            ))

        self.assertEqual(result.status, "complete")
        parts = json.loads(requests[0].content)["contents"][0]["parts"]
        self.assertEqual(parts[1]["inline_data"]["mime_type"], "image/jpeg")
        self.assertEqual(parts[1]["inline_data"]["data"], "cHJlcGFyZWQtaW1hZ2UtYnl0ZXM=")

    async def test_malformed_result_gets_one_repair_attempt(self):
        calls = 0

        def respond(request):
            nonlocal calls
            calls += 1
            payload = {"possible_problem": "incomplete"} if calls == 1 else diagnosis()
            return httpx.Response(200, json=gemini_response(payload))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            agent = CropHealthAgent(GeminiAdapter(
                client, api_key="test-key", model="gemini-3.8-flash"
            ))
            result = await agent.analyze(CropHealthInput(description="Leaves have spots"))

        self.assertEqual(result.status, "complete")
        self.assertEqual(calls, 2)

    async def test_repeated_malformed_result_is_unavailable_without_raw_output(self):
        def respond(request):
            return httpx.Response(200, json={"candidates": [{"content": {"parts": []}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            agent = CropHealthAgent(GeminiAdapter(
                client, api_key="test-key", model="gemini-3.8-flash"
            ))
            result = await agent.analyze(CropHealthInput(description="Leaves have spots"))

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.error_code, "malformed_model_output")
        self.assertIsNone(result.result)

    async def test_unconfigured_provider_is_unavailable(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: self.fail("Unconfigured adapter must not call Gemini")
        )) as client:
            agent = CropHealthAgent(GeminiAdapter(
                client, api_key=None, model="gemini-3.8-flash"
            ))
            result = await agent.analyze(CropHealthInput(description="Leaves have spots"))
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.error_code, "gemini_unavailable")

    def test_input_and_diagnosis_claims_are_validated(self):
        with self.assertRaises(ValidationError):
            CropHealthInput(description=" ")
        with self.assertRaises(ValidationError):
            from app.schemas.crop_health import CropHealthDiagnosis
            CropHealthDiagnosis.model_validate(diagnosis(possible_problem="Confirmed early blight"))
        with self.assertRaises(ValidationError):
            CropHealthDiagnosis.model_validate_json(json.dumps(diagnosis(confidence="0.68")))


if __name__ == "__main__":
    unittest.main()
