from __future__ import annotations

import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

_numero_instancia: str | None = None


def _headers() -> dict[str, str]:
    return {"apikey": settings.evolution_api_key, "Content-Type": "application/json"}


def configurado() -> bool:
    return bool(settings.evolution_api_url and settings.evolution_api_key)


def asegurar_instancia() -> bool:
    """Crea la instancia y el webhook si Evolution está disponible."""
    if not configurado():
        return False
    try:
        if not _instancia_existe():
            _crear_instancia()
        _configurar_webhook()
        return True
    except Exception:
        logger.exception("No se pudo preparar la instancia de Evolution")
        return False


def estado_conexion() -> dict[str, Any]:
    if not configurado():
        return {"conectado": False, "estado": "sin_configurar"}
    try:
        response = httpx.get(
            f"{_base()}/instance/connectionState/{settings.evolution_instance}",
            headers=_headers(),
            timeout=10.0,
        )
        response.raise_for_status()
        body = response.json()
        estado = (
            (body.get("instance") or {}).get("state")
            or body.get("state")
            or body.get("status")
            or "desconocido"
        )
        return {"conectado": str(estado).lower() in {"open", "connected"}, "estado": estado}
    except Exception:
        logger.exception("No se pudo consultar el estado de WhatsApp")
        return {"conectado": False, "estado": "error"}


def obtener_qr() -> str | None:
    """Devuelve el QR en data-URI base64, o None si ya está conectado / no hay QR."""
    if not configurado():
        return None
    asegurar_instancia()
    response = httpx.get(
        f"{_base()}/instance/connect/{settings.evolution_instance}",
        headers=_headers(),
        timeout=20.0,
    )
    response.raise_for_status()
    body = response.json()
    qrcode = body.get("qrcode") if isinstance(body.get("qrcode"), dict) else body
    base64 = None
    if isinstance(qrcode, dict):
        base64 = qrcode.get("base64") or qrcode.get("code")
    if isinstance(base64, str) and base64.startswith("data:image"):
        return base64
    if isinstance(base64, str) and len(base64) > 20:
        return f"data:image/png;base64,{base64}"
    return None


def obtener_numero_instancia() -> str | None:
    global _numero_instancia
    if _numero_instancia:
        return _numero_instancia
    if not configurado():
        return None
    try:
        response = httpx.get(
            f"{_base()}/instance/fetchInstances",
            headers=_headers(),
            params={"instanceName": settings.evolution_instance},
            timeout=10.0,
        )
        response.raise_for_status()
        body = response.json()
        items = body if isinstance(body, list) else [body]
        for item in items:
            instancia = item.get("instance") if isinstance(item.get("instance"), dict) else item
            owner = (
                instancia.get("owner")
                or instancia.get("ownerJid")
                or instancia.get("wuid")
                or item.get("owner")
            )
            if owner:
                numero = str(owner).split("@")[0].split(":")[0]
                if numero.isdigit():
                    _numero_instancia = numero
                    return _numero_instancia
    except Exception:
        logger.exception("No se pudo leer el número de la instancia")
    return _numero_instancia


def _base() -> str:
    return settings.evolution_api_url.rstrip("/")


def _instancia_existe() -> bool:
    response = httpx.get(
        f"{_base()}/instance/fetchInstances",
        headers=_headers(),
        params={"instanceName": settings.evolution_instance},
        timeout=10.0,
    )
    if response.status_code == 404:
        return False
    response.raise_for_status()
    body = response.json()
    if not body:
        return False
    if isinstance(body, list):
        return len(body) > 0
    return True


def _crear_instancia() -> None:
    webhook_url = settings.evolution_webhook_url
    payload: dict[str, Any] = {
        "instanceName": settings.evolution_instance,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
        "groupsIgnore": True,
        "rejectCall": True,
    }
    if webhook_url:
        payload["webhook"] = {
            "enabled": True,
            "url": webhook_url,
            "byEvents": False,
            "base64": False,
            "events": ["MESSAGES_UPSERT"],
        }
    response = httpx.post(
        f"{_base()}/instance/create",
        headers=_headers(),
        json=payload,
        timeout=30.0,
    )
    if response.status_code not in {200, 201}:
        logger.warning("Crear instancia: %s %s", response.status_code, response.text)
        response.raise_for_status()


def _configurar_webhook() -> None:
    webhook_url = settings.evolution_webhook_url
    if not webhook_url:
        return
    payload = {
        "enabled": True,
        "url": webhook_url,
        "webhookByEvents": False,
        "webhookBase64": False,
        "events": ["MESSAGES_UPSERT"],
    }
    response = httpx.post(
        f"{_base()}/webhook/set/{settings.evolution_instance}",
        headers=_headers(),
        json=payload,
        timeout=15.0,
    )
    if response.status_code >= 400:
        anidado = {"webhook": {**payload, "byEvents": False, "base64": False}}
        response = httpx.post(
            f"{_base()}/webhook/set/{settings.evolution_instance}",
            headers=_headers(),
            json=anidado,
            timeout=15.0,
        )
    if response.status_code >= 400:
        logger.warning("Webhook Evolution: %s %s", response.status_code, response.text)
