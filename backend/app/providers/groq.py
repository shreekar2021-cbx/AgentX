"""Groq AI provider for ultra-low latency translations and agricultural voice assistance."""

import json
import logging
import re
from typing import Any
import httpx

from app.core.config import Settings
from app.knowledge.catalog import ISSUES, CROPS, TELUGU_CROPS, TELUGU_KEYWORDS
from app.schemas.voice import TranslationResponse, VoiceAssistResponse, VoiceStatusResponse

logger = logging.getLogger("agrivision.groq")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TRANSCRIPT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"


class GroqProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.groq_api_key and self.settings.groq_api_key.strip())

    async def get_status(self) -> VoiceStatusResponse:
        active = "groq" if self.is_configured else ("mistral" if self.settings.mistral_api_key else "local")
        return VoiceStatusResponse(
            groq_configured=self.is_configured,
            groq_model=self.settings.groq_model,
            groq_fast_model=self.settings.groq_fast_model,
            active_provider=active,
        )

    async def translate(
        self, text: str, target_language: str = "te", source_language: str = "auto"
    ) -> TranslationResponse:
        clean_text = text.strip()
        if not clean_text:
            return TranslationResponse(
                original=text,
                translated="",
                target_language=target_language,
                source_language=source_language,
                provider="none",
            )

        lang_names = {"te": "Telugu (తెలుగు)", "hi": "Hindi (हिन्दी)", "en": "English"}
        target_name = lang_names.get(target_language.lower(), target_language)

        system_prompt = (
            "You are a professional, accurate translator specializing in Indian agriculture and rural terminology. "
            f"Translate the given text into {target_name}. "
            "Output ONLY the raw translated text. Do not wrap in quotation marks. "
            "Do not add any explanations, markdown, or greetings."
        )

        # 1. Try Groq with available candidate models
        if self.is_configured:
            candidate_models = []
            for m in [self.settings.groq_fast_model, self.settings.groq_model, "qwen/qwen3.8-27b", "openai/gpt-oss-120b", "llama-3.1-8b-instant", "llama-3.3-70b-versatile"]:
                if m and m not in candidate_models:
                    candidate_models.append(m)

            for model_candidate in candidate_models:
                try:
                    payload = {
                        "model": model_candidate,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": clean_text},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1024,
                    }
                    headers = {
                        "Authorization": f"Bearer {self.settings.groq_api_key}",
                        "Content-Type": "application/json",
                    }
                    response = await self.client.post(
                        GROQ_CHAT_URL, json=payload, headers=headers, timeout=self.settings.groq_timeout_seconds
                    )
                    if response.status_code == 200:
                        data = response.json()
                        translated = data["choices"][0]["message"]["content"].strip()
                        return TranslationResponse(
                            original=clean_text,
                            translated=translated,
                            target_language=target_language,
                            source_language=source_language,
                            provider=f"groq ({model_candidate})",
                        )
                except Exception as exc:
                    logger.warning("Groq translation request failed for model %s: %s", model_candidate, exc)

        # 2. Fallback to Mistral if configured
        if self.settings.mistral_api_key:
            try:
                payload = {
                    "model": self.settings.mistral_model_fast,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": clean_text},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1024,
                }
                headers = {
                    "Authorization": f"Bearer {self.settings.mistral_api_key}",
                    "Content-Type": "application/json",
                }
                response = await self.client.post(
                    MISTRAL_CHAT_URL, json=payload, headers=headers, timeout=self.settings.mistral_timeout_seconds
                )
                if response.status_code == 200:
                    data = response.json()
                    translated = data["choices"][0]["message"]["content"].strip()
                    return TranslationResponse(
                        original=clean_text,
                        translated=translated,
                        target_language=target_language,
                        source_language=source_language,
                        provider="mistral",
                    )
            except Exception as exc:
                logger.warning("Mistral translation fallback failed: %s", exc)

        # 3. Local fallback for common agricultural terms
        catalog_trans = self._lookup_catalog_term(clean_text, target_language)
        if catalog_trans:
            return TranslationResponse(
                original=clean_text,
                translated=catalog_trans,
                target_language=target_language,
                source_language=source_language,
                provider="catalog_fallback",
            )

        return TranslationResponse(
            original=clean_text,
            translated=clean_text,
            target_language=target_language,
            source_language=source_language,
            provider="untranslated_fallback",
        )

    async def voice_assist(
        self,
        query: str,
        language: str = "te",
        crop: str | None = None,
        field: str | None = None,
        district: str | None = None,
    ) -> VoiceAssistResponse:
        clean_query = query.strip()
        lang = language.lower() if language else "te"

        # Check if query is in Telugu or requested language is Telugu
        is_telugu = lang == "te" or any("\u0c00" <= ch <= "\u0c7f" for ch in clean_query)
        is_hindi = lang == "hi" or any("\u0900" <= ch <= "\u097f" for ch in clean_query)
        target_lang = "te" if is_telugu else ("hi" if is_hindi else "en")

        context_lines = []
        if crop:
            context_lines.append(f"Crop: {crop}")
        if field:
            context_lines.append(f"Field: {field}")
        if district:
            context_lines.append(f"District: {district}")
        context_str = ", ".join(context_lines) if context_lines else "General agricultural query"

        system_prompt = (
            "You are 'రైతు మిత్ర' (AgriVoice Assistant), an expert Indian agricultural companion for farmers. "
            "You are speaking to a farmer who is using a voice interface.\n\n"
            "LANGUAGE RULES:\n"
            "- If language is Telugu ('te'): Respond strictly in natural, fluent, spoken Telugu (తెలుగు) script.\n"
            "- If language is Hindi ('hi'): Respond strictly in natural, fluent, spoken Hindi (हिन्दी) script.\n"
            "- If language is English ('en'): Respond in clear, simple Indian English.\n\n"
            "VOICE SPOKEN CONSTRAINTS:\n"
            "1. Length: Keep the reply under 3 to 4 short sentences (around 50 to 80 words) so it can be read aloud cleanly by Text-To-Speech.\n"
            "2. Tone: Warm, respectful, encouraging, and direct.\n"
            "3. Agronomic Advice: Provide safe, practical immediate guidance (balanced irrigation, organic remedies, micronutrient balance, field inspection, or consulting the local agricultural officer/KVK). Avoid dangerous high-toxicity pesticide dosages.\n"
            "4. Action Steps: Conclude with 2 short actionable bullet points (starting with 1. and 2.)."
        )

        user_content = f"Farmer context: {context_str}\nFarmer's spoken question: {clean_query}"

        # 1. Try Groq (trying configured model and available candidates)
        if self.is_configured:
            candidate_models = []
            for m in [self.settings.groq_model, "openai/gpt-oss-120b", "qwen/qwen3.8-27b", self.settings.groq_fast_model, "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                if m and m not in candidate_models:
                    candidate_models.append(m)

            for model_candidate in candidate_models:
                try:
                    payload = {
                        "model": model_candidate,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 600,
                    }
                    headers = {
                        "Authorization": f"Bearer {self.settings.groq_api_key}",
                        "Content-Type": "application/json",
                    }
                    response = await self.client.post(
                        GROQ_CHAT_URL, json=payload, headers=headers, timeout=self.settings.groq_timeout_seconds
                    )
                    if response.status_code == 200:
                        data = response.json()
                        raw_reply = data["choices"][0]["message"]["content"].strip()
                        reply, actions = self._parse_reply_and_actions(raw_reply, target_lang)
                        return VoiceAssistResponse(
                            reply=reply,
                            language=target_lang,
                            quick_actions=actions,
                            provider=f"groq ({model_candidate})",
                        )
                except Exception as exc:
                    logger.warning("Groq voice assistant request failed for model %s: %s", model_candidate, exc)

        # 2. Fallback to Mistral
        if self.settings.mistral_api_key:
            try:
                payload = {
                    "model": self.settings.mistral_model_general,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 600,
                }
                headers = {
                    "Authorization": f"Bearer {self.settings.mistral_api_key}",
                    "Content-Type": "application/json",
                }
                response = await self.client.post(
                    MISTRAL_CHAT_URL, json=payload, headers=headers, timeout=self.settings.mistral_timeout_seconds
                )
                if response.status_code == 200:
                    data = response.json()
                    raw_reply = data["choices"][0]["message"]["content"].strip()
                    reply, actions = self._parse_reply_and_actions(raw_reply, target_lang)
                    return VoiceAssistResponse(
                        reply=reply,
                        language=target_lang,
                        quick_actions=actions,
                        provider="mistral",
                    )
            except Exception as exc:
                logger.warning("Mistral voice assistant fallback failed: %s", exc)

        # 3. Intelligent Local Fallback
        reply, actions = self._local_voice_fallback(clean_query, target_lang, crop)
        return VoiceAssistResponse(
            reply=reply,
            language=target_lang,
            quick_actions=actions,
            provider="local_knowledge",
        )

    async def transcribe_audio(
        self, audio_bytes: bytes, filename: str = "recording.webm", language: str | None = None
    ) -> str:
        if not self.is_configured:
            return ""

        try:
            files = {"file": (filename, audio_bytes, "audio/webm")}
            data = {"model": "whisper-large-v3-turbo"}
            if language in ("te", "hi", "en"):
                data["language"] = language

            headers = {"Authorization": f"Bearer {self.settings.groq_api_key}"}
            response = await self.client.post(
                GROQ_TRANSCRIPT_URL, files=files, data=data, headers=headers, timeout=20.0
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("text", "").strip()
            logger.warning("Groq Whisper transcription failed: %s", response.text)
        except Exception as exc:
            logger.warning("Groq Whisper transcription error: %s", exc)
        return ""

    def _parse_reply_and_actions(self, raw_text: str, language: str) -> tuple[str, list[str]]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        actions: list[str] = []
        body_lines: list[str] = []

        for line in lines:
            if re.match(r"^(\d+[\.\)]|[\*\-\•])\s+", line):
                action_text = re.sub(r"^(\d+[\.\)]|[\*\-\•])\s+", "", line).strip()
                if 5 <= len(action_text) <= 120:
                    actions.append(action_text)
            else:
                body_lines.append(line)

        reply = " ".join(body_lines).strip()
        if not reply and lines:
            reply = " ".join(lines[:2])
        if not actions and len(lines) > 2:
            actions = lines[2:4]

        return reply, actions[:3]

    def _lookup_catalog_term(self, text: str, target_language: str) -> str | None:
        clean = text.strip()
        if target_language == "te":
            for en_crop, te_crop in TELUGU_CROPS.items():
                if clean.lower() == en_crop.lower():
                    return te_crop
        return None

    def _local_voice_fallback(
        self, query: str, language: str, crop: str | None
    ) -> tuple[str, list[str]]:
        q = query.lower()
        if language == "te":
            if any(k in q for k in ["పసుపు", "yellow", "ఎండి", "ఆకు"]):
                return (
                    "నమస్కారం రైతు సోదరా. పంటలో ఆకులు పసుపు రంగులోకి మారడానికి లేదా ఎండిపోవడానికి పోషకాల లోపం (ముఖ్యంగా జింక్ లేదా నత్రజని) లేదా అధిక నీటి నిల్వ కారణం కావచ్చు.",
                    [
                        "పొలంలో నీరు నిల్వ ఉండకుండా చూసుకోండి.",
                        "ఎకరాకు 2 గ్రాముల జింక్ సల్ఫేట్ ద్రావణాన్ని పిచికారీ చేయండి.",
                    ],
                )
            if any(k in q for k in ["పురుగు", "pest", "కీటక", "రసం"]):
                return (
                    "పంటలో పురుగులు లేదా రసం పీల్చే పురుగుల ఉధృతిని నివారించడానికి ముందుగా సహజ లేదా సేంద్రీయ పద్ధతులను పాటించండి. పసుపు లేదా నీలి రంగు జిగురు అట్టలను ఏర్పాటు చేయడం మంచిది.",
                    [
                        "ఎకరాకు 5 లీటర్ల వేప నూనె (నీమాస్ట్రం) పిచికారీ చేయండి.",
                        "పొలంలో మిత్ర పురుగుల ఉనికిని గమనించండి.",
                    ],
                )
            if any(k in q for k in ["వాతావరణం", "weather", "వర్షం"]):
                return (
                    "వాతావరణ మార్పులను గమనిస్తూ సాగు పనులు చేపట్టండి. వర్ష సూచన ఉన్నప్పుడు ఎరువులు మరియు పురుగుమందుల పిచికారీని తాత్కాలికంగా వాయిదా వేయండి.",
                    [
                        "పొలంలో మురుగునీటి కాలువలను శుభ్రం చేయండి.",
                        "తాజా వాతావరణ హెచ్చరికలను యాప్‌లో గమనించండి.",
                    ],
                )
            return (
                "నమస్కారం రైతు సోదరా. మీ వ్యవసాయ క్షేత్రం కోసం AgriVision AI సిద్ధంగా ఉంది. పంట ఫోటో తీసి పరిశీలనకు సమర్పించండి లేదా సమీప వ్యవసాయ అధికారిని సంప్రదించండి.",
                [
                    "స్పష్టమైన పంట ఆకుల ఫోటోతో రిపోర్ట్ నమోదు చేయండి.",
                    "సమీప రైతులతో తెగుళ్ల సమాచారాన్ని సరిచూడండి.",
                ],
            )
        else:
            return (
                f"Hello farmer. For your {crop or 'crop'}, ensure balanced nutrition and check the field drainage. If observing discoloration or pests, inspect leaf undersides promptly.",
                [
                    "Ensure adequate field drainage without waterlogging.",
                    "Apply organic neem formulation if early pests appear.",
                ],
            )

    async def translate_finding(self, finding: dict[str, Any], target_language: str = "te") -> dict[str, Any]:
        """Translates all text fields in a finding into the target language using Groq."""
        if not self.is_configured:
            return finding

        prompt = (
            f"Translate this agricultural diagnosis JSON into fluent, natural {target_language.upper()} script for Indian farmers.\n"
            "RULES:\n"
            "1. Translate ALL text inside: 'possible_problem', 'symptoms', 'possible_causes', 'immediate_actions', 'precautions', 'monitoring', and 'expert_verification'.\n"
            "2. Ensure the Telugu phrasing is natural, encouraging, and easy for rural farmers to read and listen to.\n"
            "3. Keep enum values 'severity', 'confidence', and 'spread_potential' unchanged.\n"
            "4. Return ONLY valid JSON with the exact same structure.\n\n"
            f"JSON to translate:\n{json.dumps(finding, ensure_ascii=False)}"
        )

        candidate_models = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", self.settings.groq_model]
        for model in candidate_models:
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are an expert Indian agricultural translator. Return ONLY valid JSON matching the input schema."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                }
                headers = {
                    "Authorization": f"Bearer {self.settings.groq_api_key}",
                    "Content-Type": "application/json",
                }
                response = await self.client.post(
                    GROQ_CHAT_URL, json=payload, headers=headers, timeout=self.settings.groq_timeout_seconds + 5
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    if "possible_problem" in parsed and "immediate_actions" in parsed:
                        parsed["confidence"] = finding.get("confidence", 0.7)
                        parsed["severity"] = finding.get("severity", "moderate")
                        parsed["spread_potential"] = finding.get("spread_potential", "moderate")
                        return parsed
            except Exception as exc:
                logger.warning("Groq finding translation failed with model %s: %s", model, exc)

        return finding

    async def generate_spoken_script(self, crop: str, problem: str, actions: list[str], language: str = "te") -> str:
        """Generates a conversational, phonetically natural spoken audio script in Telugu, specifically written for speech engines to pronounce clearly and smoothly."""
        if not self.is_configured:
            actions_spoken = ". ".join(actions[:2])
            if language == "te":
                return f"నమస్కారం రైతు సోదరా. మీ {crop} పంటలో {problem} లక్షణాలు గమనించబడ్డాయి. వెంటనే ఈ పనులు చేయండి: {actions_spoken}."
            return f"Hello farmer. For your {crop} crop, {problem} was observed. Immediate actions: {actions_spoken}."

        prompt = (
            f"Write a short (40 to 60 words), warm, respectful spoken-word audio voice script in Telugu (తెలుగు) script for an Indian farmer.\n"
            "This will be read aloud by Text-To-Speech. It must sound like a friendly local agricultural officer speaking directly to the farmer in authentic Telugu.\n"
            "DO NOT include English words, brackets, asterisks, numbers like '01', or bullet points. Use natural spoken Telugu cadence.\n\n"
            f"Crop: {crop}\n"
            f"Issue: {problem}\n"
            f"Key Actions: {actions[:2]}"
        )

        candidate_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", self.settings.groq_fast_model]
        for model in candidate_models:
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You write spoken Telugu voice scripts for farmers. Return ONLY the spoken text in Telugu script."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 200,
                }
                headers = {
                    "Authorization": f"Bearer {self.settings.groq_api_key}",
                    "Content-Type": "application/json",
                }
                response = await self.client.post(
                    GROQ_CHAT_URL, json=payload, headers=headers, timeout=self.settings.groq_timeout_seconds
                )
                if response.status_code == 200:
                    text = response.json()["choices"][0]["message"]["content"].strip()
                    cleaned = re.sub(r'[*_#`"\'()]', '', text).strip()
                    if len(cleaned) > 10:
                        return cleaned
            except Exception as exc:
                logger.warning("Spoken script generation failed on model %s: %s", model, exc)

        actions_spoken = ". ".join(actions[:2])
        return f"నమస్కారం రైతు సోదరా. మీ {crop} పంటలో {problem} లక్షణాలు గమనించబడ్డాయి. వెంటనే ఈ పనులు చేయండి: {actions_spoken}."

