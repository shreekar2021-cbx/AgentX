from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from app.knowledge.catalog import local_finding
from app.providers.contracts import AIProvider
from app.providers.mistral import AIProviderError
from app.repositories.local import LocalRepository
from app.schemas.intelligence import AIStatus, CropHealthResult


class CropHealthAgent:
    def __init__(self, provider: AIProvider, cache: LocalRepository, model_name: str) -> None:
        self.provider = provider
        self.cache = cache
        self.model_name = model_name

    async def evaluate(self, *, input_hash: str, crop: str, symptoms: str, notes: str | None, season: str, image: bytes, mime_type: str, weather_context: dict[str, Any], language: str = "en") -> CropHealthResult:
        cache_payload = {"season": season, "weather": weather_context}
        if language and language != "en":
            cache_payload["language"] = language
        cache_key = hashlib.sha256((input_hash + json.dumps(cache_payload, sort_keys=True, default=str)).encode()).hexdigest()
        cached = await self.cache.ai_cache_get(cache_key)
        if cached:
            if hasattr(self.cache, "record_provider"):
                await self.cache.record_provider("mistral", "Cached")
            return cached.model_copy(update={"source": AIStatus.CACHED})
        context = {"crop": crop, "symptoms": symptoms, "notes": (notes or "")[:1200], "season": season, "weather": weather_context, "language": language}
        try:
            finding = await self.provider.analyze_crop(image, mime_type, context)
            result = CropHealthResult(finding=finding, source=AIStatus.LIVE, model=self.model_name, image_assessed=bool(image), analyzed_at=datetime.now(timezone.utc))
            await self.cache.ai_cache_put(cache_key, result)
            if hasattr(self.cache, "record_provider"):
                await self.cache.record_provider("mistral", "Healthy")
            return result
        except AIProviderError as exc:
            if hasattr(self.cache, "record_provider"):
                await self.cache.record_provider("mistral", "Fallback", exc.code)
            finding, reference = local_finding(crop, symptoms, language=language)
            status = AIStatus.LOCAL_KNOWLEDGE if reference else AIStatus.LIMITED
            return CropHealthResult(
                finding=finding, source=status, model=None, image_assessed=False,
                knowledge_ref=reference, analyzed_at=datetime.now(timezone.utc),
                limitation=f"AI unavailable ({exc.code}); image was not analyzed. This is a text-only, non-diagnostic fallback.",
            )
