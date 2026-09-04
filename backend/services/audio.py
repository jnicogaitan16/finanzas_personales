from __future__ import annotations

from dataclasses import dataclass

from config import settings
from transcription.whisper_client import transcribir_audio
from webhook.media import descargar_audio, duracion_segundos

_MAX_SEGUNDOS = 60


@dataclass(frozen=True)
class ResultadoAudio:
    texto: str | None
    error: str | None = None


def transcribir_nota_voz(crudo: dict) -> ResultadoAudio:
    if not settings.groq_api_key:
        return ResultadoAudio(
            None,
            "Las notas de voz necesitan GROQ_API_KEY en el .env. "
            "Mientras tanto escribe el gasto.",
        )
    if duracion_segundos(crudo) > _MAX_SEGUNDOS:
        return ResultadoAudio(None, "La nota de voz es muy larga. Máximo 1 minuto, o escríbela.")
    audio = descargar_audio(crudo)
    if not audio:
        return ResultadoAudio(None, "No pude descargar el audio. Prueba de nuevo o escríbelo.")
    texto = transcribir_audio(audio)
    if not texto:
        return ResultadoAudio(None, "No entendí la nota de voz. Prueba otra vez o escríbela.")
    return ResultadoAudio(texto)
