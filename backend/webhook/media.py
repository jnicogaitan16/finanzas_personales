from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from config import settings
from webhook.evolution import desenvolver_mensaje

logger = logging.getLogger(__name__)


def descargar_audio(crudo: dict[str, Any]) -> bytes | None:
    """Pide a Evolution el audio en base64 (mp3) y lo decodifica."""
    if not settings.evolution_api_url or not settings.evolution_api_key:
        return None
    url = (
        settings.evolution_api_url.rstrip("/")
        + f"/chat/getBase64FromMediaMessage/{settings.evolution_instance}"
    )
    cuerpos = (
        {"message": crudo, "convertToMp3": True},
        {"message": {"key": crudo.get("key"), "message": crudo.get("message")}, "convertToMp3": True},
    )
    headers = {"apikey": settings.evolution_api_key, "Content-Type": "application/json"}
    for payload in cuerpos:
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=45.0)
            if response.status_code >= 400:
                logger.warning("Audio Evolution %s %s", response.status_code, response.text[:300])
                continue
            body = response.json()
            b64 = body.get("base64") if isinstance(body, dict) else None
            if not b64 and isinstance(body, dict):
                inner = body.get("data") if isinstance(body.get("data"), dict) else {}
                b64 = inner.get("base64")
            if not isinstance(b64, str) or len(b64) < 20:
                continue
            if "," in b64[:40]:
                b64 = b64.split(",", 1)[1]
            return base64.b64decode(b64)
        except Exception:
            logger.exception("No se pudo descargar el audio de Evolution")
    return None


def duracion_segundos(crudo: dict[str, Any]) -> int:
    message = desenvolver_mensaje(
        crudo.get("message") if isinstance(crudo.get("message"), dict) else {}
    )
    audio = message.get("audioMessage") or message.get("pttMessage") or {}
    if not isinstance(audio, dict):
        return 0
    try:
        return int(audio.get("seconds") or 0)
    except (TypeError, ValueError):
        return 0
