from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from tiempo import a_bogota

_PREFIJOS_BOT = ("✅", "No pude leer", "Las notas de voz", "No entendí la nota", "No pude descargar")
_MENSAJES_ENVUELTOS = (
    "ephemeralMessage",
    "viewOnceMessage",
    "viewOnceMessageV2",
    "viewOnceMessageV2Extension",
    "documentWithCaptionMessage",
    "editedMessage",
)


@dataclass(frozen=True)
class MensajeWhatsApp:
    telefono: str
    texto: str
    enviado_en: datetime | None = None
    from_me: bool = False
    es_audio: bool = False
    crudo: dict[str, Any] | None = None
    message_id: str | None = None


def extraer_mensaje_entrada(
    payload: dict[str, Any],
    *,
    numero_instancia: str | None = None,
) -> MensajeWhatsApp | None:
    """Devuelve el mensaje desde un webhook de Evolution API, o None si se ignora."""
    event = str(payload.get("event") or payload.get("eventType") or "")
    if event and "upsert" not in event.lower() and event.upper() not in {"", "MESSAGES_UPSERT"}:
        return None

    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if isinstance(payload.get("data"), list) and payload["data"]:
        first = payload["data"][0]
        data = first if isinstance(first, dict) else payload

    key = data.get("key") if isinstance(data.get("key"), dict) else {}
    remote = str(key.get("remoteJid") or "")
    if not remote or remote.endswith("@g.us") or remote.endswith("@broadcast") or remote.endswith(
        "@newsletter"
    ):
        return None

    telefono = _telefono_desde_jid(remote, key, data)
    if not telefono:
        return None

    from_me = bool(key.get("fromMe"))
    if from_me and (not numero_instancia or telefono != numero_instancia):
        return None

    msg_id = str(key.get("id")) if key.get("id") else None

    message = desenvolver_mensaje(
        data.get("message") if isinstance(data.get("message"), dict) else {}
    )
    texto = _texto_de_mensaje(message)
    es_audio = _es_nota_voz(message)
    if es_audio and not texto:
        return MensajeWhatsApp(
            telefono=telefono,
            texto="",
            enviado_en=_fecha_envio(data, message),
            from_me=from_me,
            es_audio=True,
            crudo=data if isinstance(data, dict) else None,
            message_id=msg_id,
        )
    if not texto:
        return None

    texto_limpio = texto.strip()
    if texto_limpio.startswith(_PREFIJOS_BOT):
        return None

    return MensajeWhatsApp(
        telefono=telefono,
        texto=texto_limpio,
        enviado_en=_fecha_envio(data, message),
        from_me=from_me,
        message_id=msg_id,
    )


def desenvolver_mensaje(message: dict[str, Any]) -> dict[str, Any]:
    actual = message
    for _ in range(5):
        envuelto = False
        for clave in _MENSAJES_ENVUELTOS:
            nodo = actual.get(clave)
            if isinstance(nodo, dict) and isinstance(nodo.get("message"), dict):
                actual = nodo["message"]
                envuelto = True
                break
        if not envuelto:
            break
    return actual


def _texto_de_mensaje(message: dict[str, Any]) -> str | None:
    texto = message.get("conversation")
    if not texto:
        extended = message.get("extendedTextMessage") or {}
        texto = extended.get("text") if isinstance(extended, dict) else None
    if not texto or not str(texto).strip():
        return None
    return str(texto)


def _es_nota_voz(message: dict[str, Any]) -> bool:
    audio = message.get("audioMessage") or message.get("pttMessage")
    if not isinstance(audio, dict):
        return False
    return bool(audio.get("ptt") or audio.get("mimetype") or audio.get("url") or audio)


def _telefono_desde_jid(remote: str, key: dict[str, Any], data: dict[str, Any]) -> str | None:
    if remote.endswith("@lid"):
        for crudo in (
            key.get("senderPn"),
            key.get("remoteJidAlt"),
            data.get("senderPn"),
            data.get("remoteJidAlt"),
        ):
            if not crudo:
                continue
            numero = str(crudo).split("@")[0].split(":")[0]
            if numero.isdigit():
                return numero
    candidato = remote.split("@")[0].split(":")[0]
    if candidato.isdigit() and not remote.endswith("@lid"):
        return candidato
    return None


def _fecha_envio(data: dict[str, Any], message: dict[str, Any]) -> datetime | None:
    crudo = (
        data.get("messageTimestamp")
        or data.get("message_timestamp")
        or message.get("messageTimestamp")
        or message.get("message_timestamp")
    )
    if crudo is None:
        return None
    try:
        return a_bogota(int(crudo))
    except (TypeError, ValueError, OSError):
        return None
