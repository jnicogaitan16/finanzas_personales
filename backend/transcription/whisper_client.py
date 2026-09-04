from __future__ import annotations

import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

_GROQ_TRANSCRIBE = "https://api.groq.com/openai/v1/audio/transcriptions"
_MODELO = "whisper-large-v3-turbo"
_PROMPT = (
    "Español de Colombia. Transcribe una nota de voz de gastos personales. "
    "Escribe las cantidades en números (ej: 15000, 20 mil). "
    "Comandos posibles: borra el último, actualiza uber a 15000."
)


def transcribir_audio(contenido: bytes, *, filename: str = "audio.mp3") -> str | None:
    if not settings.groq_api_key:
        return None
    if not contenido:
        return None
    try:
        response = httpx.post(
            _GROQ_TRANSCRIBE,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            files={"file": (filename, contenido, "audio/mpeg")},
            data={"model": _MODELO, "language": "es", "prompt": _PROMPT},
            timeout=60.0,
        )
        response.raise_for_status()
        texto = response.json().get("text")
        if isinstance(texto, str) and texto.strip():
            return texto.strip()
    except Exception:
        logger.exception("Falló la transcripción Groq/Whisper")
    return None
