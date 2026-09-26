from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.core.config import Settings, get_settings
from app.providers.groq import GroqProvider
from app.schemas.voice import (
    TranslationRequest,
    TranslationResponse,
    VoiceAssistRequest,
    VoiceAssistResponse,
    VoiceStatusResponse,
)

router = APIRouter(tags=["voice"])


def get_groq_provider(request: Request, settings: Settings = Depends(get_settings)) -> GroqProvider:
    client = getattr(request.app.state, "http_client", None)
    return GroqProvider(settings, client)


@router.get("/api/voice/status", response_model=VoiceStatusResponse)
async def get_voice_status(provider: GroqProvider = Depends(get_groq_provider)) -> VoiceStatusResponse:
    return await provider.get_status()


@router.post("/api/voice/assist", response_model=VoiceAssistResponse)
async def voice_assist(body: VoiceAssistRequest, provider: GroqProvider = Depends(get_groq_provider)) -> VoiceAssistResponse:
    return await provider.voice_assist(
        query=body.query,
        language=body.language,
        crop=body.crop,
        field=body.field,
        district=body.district,
    )


@router.post("/api/voice/translate", response_model=TranslationResponse)
@router.post("/api/translate", response_model=TranslationResponse)
async def translate_text(body: TranslationRequest, provider: GroqProvider = Depends(get_groq_provider)) -> TranslationResponse:
    return await provider.translate(
        text=body.text,
        target_language=body.target_language,
        source_language=body.source_language,
    )


@router.post("/api/voice/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = None,
    provider: GroqProvider = Depends(get_groq_provider),
) -> dict[str, str]:
    content = await file.read()
    text = await provider.transcribe_audio(content, filename=file.filename or "recording.webm", language=language)
    return {"text": text}
