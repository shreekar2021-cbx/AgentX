from pydantic import BaseModel, Field


class VoiceStatusResponse(BaseModel):
    groq_configured: bool
    groq_model: str
    groq_fast_model: str
    active_provider: str


class VoiceAssistRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1500)
    language: str = Field(default="te", max_length=10)
    crop: str | None = Field(default=None, max_length=100)
    field: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)


class VoiceAssistResponse(BaseModel):
    reply: str
    language: str
    quick_actions: list[str] = []
    provider: str


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    target_language: str = Field(default="te", max_length=10)
    source_language: str = Field(default="auto", max_length=10)


class TranslationResponse(BaseModel):
    original: str
    translated: str
    target_language: str
    source_language: str
    provider: str
