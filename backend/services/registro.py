from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from db.models import Categoria, Movimiento, User
from parser.extractor import extraer_mensaje
from parser.mensajes import mensaje_aclaracion, mensaje_confirmacion
from parser.numeros_hablados import normalizar_numeros_hablados
from services.audit import registrar_creacion
from services.comandos import (
    aplicar_pendiente,
    ejecutar_comando,
    interpretar_comando,
    limpiar_pendiente,
    parece_comando,
)
from services.resultado import ResultadoRegistro
from tiempo import a_bogota, ahora_bogota


def procesar_mensaje(
    db: Session,
    *,
    telefono: str,
    texto: str,
    fue_audio: bool = False,
    enviado_en: datetime | None = None,
) -> ResultadoRegistro:
    user = buscar_usuario(db, telefono)
    if user is None:
        return ResultadoRegistro(status="ignored", mensaje_respuesta="")
    texto_limpio = normalizar_numeros_hablados(texto.strip())
    momento = a_bogota(enviado_en) if enviado_en is not None else ahora_bogota()
    comando = interpretar_comando(texto_limpio, hoy=momento.date())
    if comando is not None:
        return ejecutar_comando(db, user, comando)
    pendiente = aplicar_pendiente(db, user, texto_limpio)
    if pendiente is not None:
        return pendiente
    limpiar_pendiente(user.id)
    if parece_comando(texto_limpio):
        return ResultadoRegistro(
            status="comando",
            mensaje_respuesta=(
                "No entendí qué movimiento quieres. "
                'Prueba: "borra el último", "elimina gasto de maya" o "actualiza maya a 15.000".'
            ),
        )
    return registrar_texto(
        db,
        telefono=telefono,
        texto=texto_limpio,
        fue_audio=fue_audio,
        enviado_en=enviado_en,
    )


def registrar_texto(
    db: Session,
    *,
    telefono: str,
    texto: str,
    fue_audio: bool = False,
    enviado_en: datetime | None = None,
) -> ResultadoRegistro:
    user = buscar_usuario(db, telefono)
    if user is None:
        return ResultadoRegistro(
            status="ignored",
            mensaje_respuesta="",
        )

    enviado_en = a_bogota(enviado_en) if enviado_en is not None else ahora_bogota()

    texto_limpio = texto.strip()
    if not texto_limpio:
        return ResultadoRegistro(
            status="aclaracion",
            mensaje_respuesta=mensaje_aclaracion(),
        )

    extraccion = extraer_mensaje(texto_limpio, enviado_en=enviado_en)
    if not extraccion.es_valida:
        return ResultadoRegistro(
            status="aclaracion",
            mensaje_respuesta=mensaje_aclaracion(),
            extraccion=extraccion,
        )

    categoria = buscar_categoria(db, extraccion.categoria or "Otros")
    movimiento = Movimiento(
        user_id=user.id,
        categoria_id=categoria.id if categoria else None,
        monto_cop=extraccion.monto_cop or 0,
        descripcion=extraccion.descripcion,
        mensaje_original=texto_limpio,
        fue_audio=fue_audio,
        confianza_parsing=extraccion.confianza,
        fecha_registro=enviado_en,
        fecha_gasto=extraccion.fecha_gasto,
        es_compartido=extraccion.compartido,
        porcentaje_compartido=50 if extraccion.compartido else None,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    registrar_creacion(db, movimiento, origen="whatsapp")
    return ResultadoRegistro(
        status="registrado",
        mensaje_respuesta=mensaje_confirmacion(extraccion),
        movimiento_id=movimiento.id,
        extraccion=extraccion,
    )


def buscar_usuario(db: Session, telefono: str) -> User | None:
    numero = _normalizar_telefono(telefono)
    return db.query(User).filter(User.numero_whatsapp == numero).one_or_none()


def buscar_categoria(db: Session, nombre: str) -> Categoria | None:
    return db.query(Categoria).filter(Categoria.nombre == nombre).one_or_none()


def _normalizar_telefono(telefono: str) -> str:
    return "".join(ch for ch in telefono if ch.isdigit())
