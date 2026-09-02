import logging
from contextlib import asynccontextmanager
from datetime import datetime
from secrets import compare_digest
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

from admin.router import router as admin_router
from cache import msg_ya_visto
from config import settings
from logging_config import setup_logging
from db.session import get_db
from db.users_seed import seed_authorized_users
from services.audio import transcribir_nota_voz
from services.registro import buscar_usuario, procesar_mensaje
from webhook.client import (
    asegurar_instancia,
    estado_conexion,
    obtener_numero_instancia,
    obtener_qr,
)
from webhook.evolution import extraer_mensaje_entrada
from webhook.qr_page import QR_HTML
from webhook.sender import enviar_texto_whatsapp

setup_logging()
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_authorized_users()
    asegurar_instancia()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(admin_router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'"
    )
    return response



class TextoIn(BaseModel):
    telefono: str
    texto: str
    enviado_en: datetime | None = None


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/whatsapp/estado")
def whatsapp_estado() -> dict[str, Any]:
    return estado_conexion()


@app.get("/whatsapp/qr", response_class=HTMLResponse)
def whatsapp_qr() -> str:
    estado = estado_conexion()
    if estado.get("conectado"):
        cuerpo = (
            '<p class="ok">WhatsApp está conectado.</p>'
            '<p class="hint">Escríbete un gasto, o usa comandos: últimos · borra el último · ayuda</p>'
            '<p class="hint"><a href="/admin" style="color:#6ee7b7">Abrir panel admin</a></p>'
        )
        return QR_HTML.format(cuerpo=cuerpo)
    try:
        qr = obtener_qr()
    except Exception:
        qr = None
    if qr:
        cuerpo = (
            f'<img src="{qr}" alt="Código QR">'
            '<p class="hint">En el teléfono: WhatsApp → Dispositivos vinculados → Vincular dispositivo. '
            "La página se actualiza sola.</p>"
        )
    else:
        cuerpo = (
            f'<p>Aún no hay QR. Estado: {estado.get("estado")}.</p>'
            '<p class="hint">Espera unos segundos y recarga. Evolution puede tardar en arrancar.</p>'
        )
    return QR_HTML.format(cuerpo=cuerpo)


@app.post("/webhook/texto")
def webhook_texto(payload: TextoIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    resultado = procesar_mensaje(
        db,
        telefono=payload.telefono,
        texto=payload.texto,
        enviado_en=payload.enviado_en,
    )
    if resultado.status in {"registrado", "aclaracion", "comando"} and resultado.mensaje_respuesta:
        enviar_texto_whatsapp(payload.telefono, resultado.mensaje_respuesta)
    return {
        "status": resultado.status,
        "mensaje": resultado.mensaje_respuesta,
        "movimiento_id": resultado.movimiento_id,
    }


def _verify_webhook(
    request: Request,
    apikey: str | None = Header(None),
) -> None:
    expected = settings.evolution_api_key
    if not expected:
        return
    # Evolution puede enviar el apikey como header o como query param
    token = apikey or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if token and compare_digest(token, expected):
        return
    # Aceptar si viene del network interno de Docker (172.x.x.x)
    client_host = request.client.host if request.client else ""
    if client_host.startswith("172."):
        return
    raise HTTPException(status_code=401, detail="Webhook no autorizado")


@app.post("/webhook/evolution")
@limiter.limit("30/minute")
def webhook_evolution(
    request: Request,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    _auth: None = Depends(_verify_webhook),
) -> dict[str, Any]:
    extraido = extraer_mensaje_entrada(
        payload,
        numero_instancia=obtener_numero_instancia(),
    )
    if extraido is None:
        return {"status": "ignored"}
    if msg_ya_visto(extraido.message_id):
        return {"status": "duplicate"}
    texto = extraido.texto
    fue_audio = extraido.es_audio
    if extraido.es_audio:
        if buscar_usuario(db, extraido.telefono) is None:
            return {"status": "ignored"}
        resultado_audio = transcribir_nota_voz(extraido.crudo or {})
        if resultado_audio.error or not resultado_audio.texto:
            error = resultado_audio.error or "No entendí la nota de voz. Prueba otra vez o escríbela."
            enviar_texto_whatsapp(extraido.telefono, error)
            return {"status": "aclaracion", "mensaje": error, "movimiento_id": None}
        texto = resultado_audio.texto
    resultado = procesar_mensaje(
        db,
        telefono=extraido.telefono,
        texto=texto,
        fue_audio=fue_audio,
        enviado_en=extraido.enviado_en,
    )
    mensaje = resultado.mensaje_respuesta
    if fue_audio and texto and mensaje:
        mensaje = f'📝 "{texto}"\n{mensaje}'
    if resultado.status in {"registrado", "aclaracion", "comando"} and mensaje:
        enviar_texto_whatsapp(extraido.telefono, mensaje)
    return {
        "status": resultado.status,
        "mensaje": mensaje,
        "movimiento_id": resultado.movimiento_id,
    }
