from __future__ import annotations

import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


def enviar_texto_whatsapp(telefono: str, texto: str) -> bool:
    if not settings.evolution_api_url or not settings.evolution_api_key:
        return False
    url = (
        settings.evolution_api_url.rstrip("/")
        + f"/message/sendText/{settings.evolution_instance}"
    )
    try:
        response = httpx.post(
            url,
            headers={"apikey": settings.evolution_api_key},
            json={"number": telefono, "text": texto},
            timeout=15.0,
        )
        response.raise_for_status()
        return True
    except Exception:
        logger.exception("No se pudo enviar la confirmación por WhatsApp")
        return False
