from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from datetime import date

from sqlalchemy.orm import Session

from db.models import Categoria, Movimiento, User
from parser.fallback_regex import extraer_con_regex, extraer_fecha_explicita
from parser.mensajes import format_cop
from services.admin import (
    actualizar_movimiento,
    eliminar_movimiento,
    listar_movimientos,
    obtener_movimiento,
    ultimo_movimiento,
)
from services.resultado import ResultadoRegistro
from tiempo import ahora_bogota

_VERBOS_BORRAR = (
    "borra",
    "borrar",
    "elimina",
    "eliminar",
    "suprime",
    "suprimir",
    "quita",
    "quitar",
)
_VERBOS_EDITAR = (
    "corrige",
    "corregir",
    "cambia",
    "cambiar",
    "actualiza",
    "actualizar",
    "modifica",
    "modificar",
    "edita",
    "editar",
    "ajusta",
    "ajustar",
    "pon",
    "ponle",
)
_STOP_OBJETIVO = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "uno",
    "de",
    "del",
    "a",
    "al",
    "por",
    "en",
    "con",
    "que",
    "se",
    "me",
    "mi",
    "mis",
    "ese",
    "esa",
    "eso",
    "este",
    "esta",
    "esto",
    "ultimo",
    "ultima",
    "ultimos",
    "ultimas",
    "registro",
    "registros",
    "gasto",
    "gastos",
    "ingreso",
    "ingresos",
    "movimiento",
    "movimientos",
    "item",
    "entrada",
    "categoria",
    "categorias",
    "valor",
    "valores",
    "monto",
    "montos",
    "precio",
    "cantidad",
    "cifra",
    "po",
    "pa",
    "pesos",
    "peso",
    "cop",
    "fecha",
    "fechas",
    "dia",
    "descripcion",
    "descripciones",
    "nombre",
    "nombres",
}
_AYUDA = (
    "Puedes hablarme más suelto. Ejemplos:\n"
    "• gasté 15.300 en almuerzo\n"
    "• últimos\n"
    "• borra / elimina / suprime el último\n"
    "• borra gasto de maya\n"
    "• si hay varios (borrar o actualizar), responde 16, #16 o el 16\n"
    "• corrige / cambia / actualiza maya a 15.000\n"
    "• actualiza fecha de uber a ayer (o 31/08/2026)\n"
    "• cambia descripción de uber a didi\n"
    "• categoría del último: Transporte\n"
    "• también notas de voz con lo mismo\n"
    "• ayuda"
)


@dataclass(frozen=True)
class Comando:
    accion: str
    monto: int | None = None
    categoria: str | None = None
    filtro_categoria: str | None = None
    consulta: str | None = None
    usar_ultimo: bool = True
    movimiento_id: int | None = None
    fecha_gasto: date | None = None
    descripcion_nueva: str | None = None


@dataclass
class _Pendiente:
    accion: str
    ids: tuple[int, ...]
    monto: int | None = None
    categoria: str | None = None
    fecha_gasto: date | None = None
    descripcion_nueva: str | None = None


_PENDIENTES: dict[int, _Pendiente] = {}
_ID_RESPUESTA = re.compile(
    r"^(?:(?:borra|borrar|elimina|eliminar|suprime|suprimir|quita|quitar|"
    r"corrige|corregir|cambia|cambiar|actualiza|actualizar|modifica|modificar)\s+)?"
    r"(?:el|la|ese|esa|numero)?\s*#?(\d+)$"
)


def reset_pendientes() -> None:
    _PENDIENTES.clear()


def limpiar_pendiente(user_id: int) -> None:
    _PENDIENTES.pop(user_id, None)


def parece_comando(texto: str) -> bool:
    t = _normalizar(texto)
    if not t:
        return False
    if t.startswith("el ultimo") or t.startswith("categoria"):
        return True
    primero = t.split(" ", 1)[0]
    return primero in _VERBOS_BORRAR or primero in _VERBOS_EDITAR or primero in {
        "ayuda",
        "help",
        "comandos",
        "ultimos",
        "ultimo",
        "listar",
        "lista",
    }


def aplicar_pendiente(db: Session, user: User, texto: str) -> ResultadoRegistro | None:
    pendiente = _PENDIENTES.get(user.id)
    if pendiente is None:
        return None
    t = _normalizar(texto)
    match = _ID_RESPUESTA.fullmatch(t)
    if not match:
        return None
    nid = int(match.group(1))
    if nid not in pendiente.ids:
        opciones = ", ".join(f"#{i}" for i in pendiente.ids)
        return ResultadoRegistro(
            status="comando",
            mensaje_respuesta=f"Ese # no está en las opciones. Elige {opciones}.",
        )
    _PENDIENTES.pop(user.id, None)
    return ejecutar_comando(
        db,
        user,
        Comando(
            accion=pendiente.accion,
            movimiento_id=nid,
            monto=pendiente.monto,
            categoria=pendiente.categoria,
            fecha_gasto=pendiente.fecha_gasto,
            descripcion_nueva=pendiente.descripcion_nueva,
            usar_ultimo=False,
        ),
    )


def interpretar_comando(texto: str, *, hoy: date | None = None) -> Comando | None:
    t = _normalizar(texto)
    if not t:
        return None
    if t in {"ayuda", "help", "comandos"}:
        return Comando("ayuda")
    if _es_listar(t):
        return Comando("listar")

    m_ultimo = re.fullmatch(r"el ultimo (fue|es|era|quedo|quedó) (?P<rest>.+)", t)
    if m_ultimo:
        return _comando_editar(m_ultimo.group("rest"), forzar_ultimo=True, hoy=hoy)

    primero, _, resto = t.partition(" ")
    if primero in _VERBOS_BORRAR:
        return _comando_borrar(resto)
    if primero in _VERBOS_EDITAR:
        return _comando_editar(resto, hoy=hoy)
    if primero == "categoria":
        return _comando_categoria(resto)
    return None


def ejecutar_comando(db: Session, user: User, comando: Comando) -> ResultadoRegistro:
    if comando.accion == "ayuda":
        return ResultadoRegistro(status="comando", mensaje_respuesta=_AYUDA)
    if comando.accion == "listar":
        return _listar(db, user)
    if comando.accion == "borrar":
        return _borrar(db, user, comando)
    if comando.accion == "corregir_monto":
        return _aplicar_edicion(db, user, comando)
    if comando.accion == "cambiar_categoria":
        return _aplicar_edicion(db, user, comando)
    if comando.accion == "corregir_fecha":
        return _aplicar_edicion(db, user, comando)
    if comando.accion == "corregir_descripcion":
        return _aplicar_edicion(db, user, comando)
    if comando.accion == "incompleto":
        return ResultadoRegistro(
            status="comando",
            mensaje_respuesta=(
                "Entendí que quieres cambiar un movimiento, pero me falta el dato. "
                'Prueba: "actualiza maya a 15.000", "fecha de uber a ayer" '
                'o "descripción de uber a didi".'
            ),
        )
    return ResultadoRegistro(status="comando", mensaje_respuesta=_AYUDA)


def _es_listar(t: str) -> bool:
    return bool(
        re.fullmatch(
            r"(ver |muestra |mostrar )?(los |mis )?(ultimos|ultimo|listar|lista|movimientos)"
            r"( registros| gastos| movimientos)?",
            t,
        )
    )


def _comando_borrar(resto: str) -> Comando:
    objetivo = _parse_objetivo(resto)
    return Comando("borrar", **objetivo)


def _comando_editar(resto: str, *, forzar_ultimo: bool = False, hoy: date | None = None) -> Comando:
    hoy = hoy or ahora_bogota().date()
    extra = extraer_con_regex(resto)
    fecha = extraer_fecha_explicita(resto, hoy=hoy)
    izq, der = _partir_valor(resto)
    objetivo = _parse_objetivo(_quitar_marcadores_edicion(izq if der else resto))
    if forzar_ultimo:
        objetivo["usar_ultimo"] = True

    cat_nueva = None
    desc_nueva = None
    if der and extraer_con_regex(der).monto_cop is None and extraer_fecha_explicita(der, hoy=hoy) is None:
        cat_nueva = _texto_categoria(der)
        if cat_nueva is None:
            limpio = der.strip(" -:.,")
            if limpio and _normalizar(limpio) not in _STOP_OBJETIVO:
                desc_nueva = limpio

    extras = {
        "fecha_gasto": fecha,
        "descripcion_nueva": desc_nueva,
    }
    if extra.monto_cop:
        return Comando("corregir_monto", monto=extra.monto_cop, **objetivo, **extras)
    if cat_nueva:
        return Comando(
            "cambiar_categoria",
            categoria=cat_nueva,
            consulta=objetivo.get("consulta"),
            usar_ultimo=objetivo.get("usar_ultimo", True),
            movimiento_id=objetivo.get("movimiento_id"),
            filtro_categoria=None,
            fecha_gasto=fecha,
        )
    if fecha:
        return Comando("corregir_fecha", **objetivo, **extras)
    if desc_nueva:
        return Comando("corregir_descripcion", **objetivo, **extras)
    nueva = objetivo.get("filtro_categoria") or _texto_categoria(objetivo.get("consulta"))
    if nueva:
        return Comando(
            "cambiar_categoria",
            categoria=nueva,
            consulta=None if objetivo.get("filtro_categoria") else objetivo.get("consulta"),
            usar_ultimo=True if objetivo.get("filtro_categoria") else objetivo.get("usar_ultimo", True),
            movimiento_id=objetivo.get("movimiento_id"),
        )
    return Comando("incompleto")


def _comando_categoria(resto: str) -> Comando:
    objetivo = _parse_objetivo(resto)
    nueva = objetivo.get("filtro_categoria") or objetivo.get("consulta")
    if not nueva:
        return Comando("incompleto")
    return Comando(
        "cambiar_categoria",
        categoria=nueva,
        consulta=None,
        usar_ultimo=True,
        movimiento_id=objetivo.get("movimiento_id"),
    )


def _parse_objetivo(resto: str) -> dict:
    texto = _normalizar(resto)
    movimiento_id = None
    id_match = re.search(r"(?:#|id\s+)(\d+)", texto)
    if id_match:
        movimiento_id = int(id_match.group(1))
        texto = texto[: id_match.start()] + " " + texto[id_match.end() :]
    tokens = [tok for tok in re.split(r"\s+", texto) if tok]
    usar_ultimo = any(tok in {"ultimo", "ultima", "ultimos", "ultimas"} for tok in tokens) or not tokens
    consulta_tokens = [tok for tok in tokens if tok not in _STOP_OBJETIVO]
    consulta = " ".join(consulta_tokens) or None
    filtro_categoria = None
    if consulta:
        cat = _texto_categoria(consulta)
        if cat and consulta == _normalizar(cat):
            filtro_categoria = cat
            consulta = None
            usar_ultimo = True
    if movimiento_id is not None:
        usar_ultimo = False
    return {
        "consulta": consulta,
        "usar_ultimo": usar_ultimo,
        "movimiento_id": movimiento_id,
        "filtro_categoria": filtro_categoria,
    }


def _quitar_monto(texto: str) -> str:
    sin = re.sub(r"\bpo\b", "por", texto, flags=re.IGNORECASE)
    sin = re.sub(r"\$?\d[\d.\s]*", " ", sin)
    sin = re.sub(r"\b(mil|k|millones|millon|millón)\b", " ", sin, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", sin).strip()


def _partir_valor(resto: str) -> tuple[str, str | None]:
    n = _normalizar(resto)
    idx = n.rfind(" a ")
    if idx == -1:
        return n, None
    izquierda = n[:idx].strip()
    derecha = n[idx + 3 :].strip()
    return izquierda, derecha or None


def _quitar_marcadores_edicion(texto: str) -> str:
    sin = _quitar_monto(texto)
    sin = re.sub(
        r"\b(hoy|ayer|anteayer|fecha|fechas|dia|descripcion|descripciones|nombre|nombres)\b",
        " ",
        sin,
        flags=re.IGNORECASE,
    )
    sin = re.sub(r"\b\d{4}-\d{1,2}-\d{1,2}\b", " ", sin)
    sin = re.sub(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", " ", sin)
    return re.sub(r"\s+", " ", sin).strip()


def _texto_categoria(texto: str | None) -> str | None:
    if not texto:
        return None
    objetivo = _normalizar(texto)
    from parser.categorias import CATEGORIAS_TODAS

    for nombre in CATEGORIAS_TODAS:
        if _normalizar(nombre) == objetivo:
            return nombre
    return None


def _listar(db: Session, user: User) -> ResultadoRegistro:
    filas = listar_movimientos(db, limit=5, user_id=user.id)
    if not filas:
        return ResultadoRegistro(status="comando", mensaje_respuesta="No tienes movimientos todavía.")
    if len(filas) == 1:
        return ResultadoRegistro(
            status="comando",
            mensaje_respuesta=f"Tu último movimiento:\n{_linea(filas[0])}",
        )
    lineas = ["Tus últimos movimientos:", *(_viñeta(m) for m in filas)]
    return ResultadoRegistro(status="comando", mensaje_respuesta="\n".join(lineas))


def _borrar(db: Session, user: User, comando: Comando) -> ResultadoRegistro:
    movimiento, error = _resolver_movimiento(db, user, comando)
    if error:
        return ResultadoRegistro(status="comando", mensaje_respuesta=error)
    assert movimiento is not None
    resumen = _resumen(movimiento)
    eliminar_movimiento(db, movimiento, origen="whatsapp")
    _PENDIENTES.pop(user.id, None)
    return ResultadoRegistro(
        status="comando",
        mensaje_respuesta=f"🗑️ Borrado: {resumen}",
        movimiento_id=movimiento.id,
    )


def _aplicar_edicion(db: Session, user: User, comando: Comando) -> ResultadoRegistro:
    movimiento, error = _resolver_movimiento(db, user, comando)
    if error:
        return ResultadoRegistro(status="comando", mensaje_respuesta=error)
    assert movimiento is not None
    kwargs: dict = {}
    campos: list[str] = []
    if comando.monto is not None:
        kwargs["monto_cop"] = comando.monto
        campos.append("monto")
    if comando.fecha_gasto is not None:
        kwargs["fecha_gasto"] = comando.fecha_gasto
        campos.append("fecha")
    if comando.descripcion_nueva is not None:
        kwargs["descripcion"] = comando.descripcion_nueva
        campos.append("descripción")
    if comando.categoria is not None:
        categoria = _buscar_categoria_flexible(db, comando.categoria)
        if categoria is None:
            return ResultadoRegistro(
                status="comando",
                mensaje_respuesta="No encontré esa categoría. Prueba: Mercado, Transporte, Servicios, Ocio, Salud, Otros, Salario.",
            )
        kwargs["categoria_id"] = categoria.id
        campos.append("categoría")
    if not kwargs:
        return ResultadoRegistro(
            status="comando",
            mensaje_respuesta=(
                "Entendí que quieres cambiar un movimiento, pero me falta el dato. "
                'Prueba: "actualiza maya a 15.000", "fecha de uber a ayer" '
                'o "descripción de uber a didi".'
            ),
        )
    try:
        actualizar_movimiento(db, movimiento, origen="whatsapp", **kwargs)
    except ValueError as exc:
        return ResultadoRegistro(status="comando", mensaje_respuesta=str(exc))
    if campos == ["monto"]:
        mensaje = f"✏️ Monto actualizado: {_resumen(movimiento)}"
    elif campos == ["categoría"]:
        mensaje = f"✏️ Categoría actualizada: {_resumen(movimiento)}"
    elif campos == ["fecha"]:
        mensaje = f"✏️ Fecha actualizada: {_resumen(movimiento)}"
    elif campos == ["descripción"]:
        mensaje = f"✏️ Descripción actualizada: {_resumen(movimiento)}"
    else:
        mensaje = f"✏️ Actualizado ({', '.join(campos)}): {_resumen(movimiento)}"
    return ResultadoRegistro(
        status="comando",
        mensaje_respuesta=mensaje,
        movimiento_id=movimiento.id,
    )


def _resolver_movimiento(
    db: Session,
    user: User,
    comando: Comando,
) -> tuple[Movimiento | None, str | None]:
    if comando.movimiento_id is not None:
        movimiento = obtener_movimiento(db, comando.movimiento_id)
        if movimiento is None or movimiento.user_id != user.id:
            return None, f"No encontré el movimiento #{comando.movimiento_id}."
        return movimiento, None

    if comando.consulta and comando.consulta.isdigit():
        nid = int(comando.consulta)
        movimiento = obtener_movimiento(db, nid)
        if movimiento is not None and movimiento.user_id == user.id:
            return movimiento, None

    candidatos = listar_movimientos(db, limit=80, user_id=user.id)
    if not candidatos:
        return None, "No hay movimientos para esa acción."

    if comando.filtro_categoria:
        cat = _buscar_categoria_flexible(db, comando.filtro_categoria)
        if cat:
            candidatos = [m for m in candidatos if m.categoria_id == cat.id]
            if not candidatos:
                return None, f"No hay movimientos en {cat.nombre}."

    if comando.consulta:
        hits = _filtrar_por_consulta(candidatos, comando.consulta)
        if not hits:
            return None, (
                f"No encontré un gasto de «{comando.consulta}». "
                "Di «últimos» para verlos o prueba con otra palabra."
            )
        if len(hits) > 1 and not comando.usar_ultimo:
            return None, _mensaje_confirmacion(hits, comando.consulta, comando, user.id)
        if len(hits) == 1 and comando.accion == "borrar" and not comando.usar_ultimo:
            return None, _mensaje_confirmacion(hits, comando.consulta, comando, user.id)
        return hits[0], None

    return candidatos[0], None


def _filtrar_por_consulta(movimientos: list[Movimiento], consulta: str) -> list[Movimiento]:
    q = _normalizar(consulta)
    if not q:
        return []
    tokens = [tok for tok in q.split() if tok not in _STOP_OBJETIVO]
    claves = [tok for tok in tokens if len(tok) >= 4] or tokens
    hits: list[Movimiento] = []
    for m in movimientos:
        blob = _normalizar(
            " ".join(
                part
                for part in (
                    m.descripcion or "",
                    m.mensaje_original or "",
                    m.categoria.nombre if m.categoria else "",
                )
                if part
            )
        )
        if q in blob or (claves and all(tok in blob for tok in claves)):
            hits.append(m)
            continue
        if q.isdigit() and m.monto_cop == int(q):
            hits.append(m)
    return hits


def _mensaje_confirmacion(
    hits: list[Movimiento],
    consulta: str,
    comando: Comando,
    user_id: int,
) -> str:
    _PENDIENTES[user_id] = _Pendiente(
        accion=comando.accion,
        ids=tuple(m.id for m in hits),
        monto=comando.monto,
        categoria=comando.categoria,
        fecha_gasto=comando.fecha_gasto,
        descripcion_nueva=comando.descripcion_nueva,
    )
    verbo = "borrar" if comando.accion == "borrar" else "actualizar"
    ejemplo_id = hits[0].id
    if len(hits) == 1:
        pregunta = "¿Lo borro?" if comando.accion == "borrar" else "¿Lo actualizo?"
        lineas = [
            f"Encontré este gasto de «{consulta}». {pregunta}",
            _linea(hits[0]),
        ]
    else:
        lineas = [
            f"Hay varios ({len(hits)}) registros de {consulta}",
            *(_viñeta(m) for m in hits[:8]),
            f"¿Cuál quieres {verbo}?",
        ]
    lineas.append(f"Responde {ejemplo_id}, #{ejemplo_id} o {verbo} el {ejemplo_id}.")
    return "\n".join(lineas)


def _buscar_categoria_flexible(db: Session, nombre: str) -> Categoria | None:
    objetivo = _normalizar(nombre)
    for cat in db.query(Categoria).all():
        if _normalizar(cat.nombre) == objetivo:
            return cat
    return None


def _viñeta(movimiento: Movimiento) -> str:
    return f"- {_linea(movimiento)}"


def _linea(movimiento: Movimiento) -> str:
    fecha = movimiento.fecha_gasto.isoformat() if movimiento.fecha_gasto else "sin fecha"
    tipo = movimiento.categoria.tipo if movimiento.categoria else "gasto"
    descripcion = movimiento.descripcion or (
        movimiento.categoria.nombre if movimiento.categoria else "sin descripción"
    )
    return f"{movimiento.id} - {fecha} - {tipo} - {descripcion} - {format_cop(movimiento.monto_cop)}"


def _resumen(movimiento: Movimiento) -> str:
    cat = movimiento.categoria.nombre if movimiento.categoria else "Sin categoría"
    desc = f" ({movimiento.descripcion})" if movimiento.descripcion else ""
    return f"{format_cop(movimiento.monto_cop)} en {cat}{desc}"


def _normalizar(texto: str) -> str:
    sin = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )
    sin = re.sub(r"[:.,;!?]+", " ", sin)
    return re.sub(r"\s+", " ", sin).strip()
