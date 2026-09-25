"""Single Gemini GenerateContent adapter for bounded structured agent outputs."""

import base64
from typing import Any

import httpx

from app.schemas.crop_health import CropImage


class GeminiUnavailable(Exception):
    """Provider is unconfigured or did not complete the request."""


class GeminiMalformedResponse(Exception):
    """Provider returned a response with no usable JSON text."""


CROP_HEALTH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "possible_problem": {"type": "string"},
        "confidence": {"type": "number"},
        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
        "symptoms": {"type": "array", "items": {"type": "string"}},
        "possible_causes": {"type": "array", "items": {"type": "string"}},
        "immediate_actions": {"type": "array", "items": {"type": "string"}},
        "precautions": {"type": "array", "items": {"type": "string"}},
        "monitoring": {"type": "array", "items": {"type": "string"}},
        "expert_verification": {"type": "boolean"},
        "spread_potential": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
    },
    "required": [
        "possible_problem", "confidence", "severity", "symptoms", "possible_causes",
        "immediate_actions", "precautions", "monitoring", "expert_verification",
        "spread_potential",
    ],
}

MARKET_TREND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "trend": {"type": "string", "enum": ["RISING", "STABLE", "FALLING"]},
        "confidence": {"type": "number"},
        "reasoning_summary": {"type": "string"},
        "forecast_horizon": {"type": "string", "enum": ["7 calendar days"]},
    },
    "required": ["trend", "confidence", "reasoning_summary", "forecast_horizon"],
}


class GeminiAdapter:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        *,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 15,
    ) -> None:
        self._http_client = http_client
        self._api_key = api_key
        self.model = model
        self._timeout_seconds = timeout_seconds

    async def generate_json(self, prompt: str, image: CropImage | None = None) -> str:
        return await self._generate_json(prompt, CROP_HEALTH_SCHEMA, image)

    async def generate_market_trend_json(self, prompt: str) -> str:
        return await self._generate_json(prompt, MARKET_TREND_SCHEMA)

    async def _generate_json(
        self, prompt: str, response_schema: dict[str, Any], image: CropImage | None = None
    ) -> str:
        if not self._api_key:
            raise GeminiUnavailable("gemini_not_configured")

        parts: list[dict[str, Any]] = [{"text": prompt}]
        if image is not None:
            parts.append({
                "inline_data": {
                    "mime_type": image.media_type,
                    "data": base64.b64encode(image.data).decode("ascii"),
                }
            })
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseFormat": {
                    "text": {"mimeType": "application/json", "schema": response_schema}
                },
                "temperature": 0.2,
            },
        }
        try:
            response = await self._http_client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self._api_key},
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except (httpx.HTTPError, TimeoutError) as exc:
            raise GeminiUnavailable("gemini_request_failed") from exc

        try:
            body = response.json()
            candidates = body["candidates"]
            if not isinstance(candidates, list) or not candidates:
                raise ValueError("missing candidates")
            first = candidates[0]
            if first.get("finishReason") not in (None, "STOP"):
                raise ValueError("generation did not finish normally")
            content_parts = first["content"]["parts"]
            text = "".join(part.get("text", "") for part in content_parts)
            if not text.strip():
                raise ValueError("missing response text")
            return text
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise GeminiMalformedResponse("gemini_response_malformed") from exc
