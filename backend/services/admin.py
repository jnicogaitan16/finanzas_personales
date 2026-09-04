from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

from db.models import Categoria, Movimiento, User
from parser.mensajes import format_cop
from services.audit import (
    _movimiento_a_dict,
    registrar_borrado,
    registrar_creacion,
    registrar_edicion,
)
from tiempo import a_bogota, ahora_bogota


def serializar_movimiento(m: Movimiento) -> dict:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "usuario": m.user.nombre if m.user else None,
        "categoria_id": m.categoria_id,
        "categoria": m.categoria.nombre if m.categoria else None,
        "tipo": m.categoria.tipo if m.categoria else None,
        "monto_cop": m.monto_cop,
        "monto_fmt": format_cop(m.monto_cop),
        "descripcion": m.descripcion,
        "mensaje_original": m.mensaje_original,
        "fue_audio": m.fue_audio,
        "fecha_gasto": m.fecha_gasto.isoformat() if m.fecha_gasto else None,
        "fecha_registro": m.fecha_registro.isoformat(sep=" ", timespec="seconds")
        if m.fecha_registro
        else None,
        "medio_pago": m.medio_pago,
        "es_compartido": m.es_compartido,
        "porcentaje_compartido": m.porcentaje_compartido,
        "compra_cuotas_id": m.compra_cuotas_id,
    }


def _activos() -> Any:
    return Movimiento.eliminado_en.is_(None)


def listar_movimientos(
    db: Session,
    *,
    limit: int = 100,
    user_id: int | None = None,
    user_ids: list[int] | None = None,
) -> list[Movimiento]:
    q = db.query(Movimiento).options(joinedload(Movimiento.user), joinedload(Movimiento.categoria)).filter(_activos())
    if user_id is not None:
        q = q.filter(Movimiento.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(Movimiento.user_id.in_(user_ids))
    return q.order_by(Movimiento.id.desc()).limit(limit).all()


def obtener_movimiento(db: Session, movimiento_id: int) -> Movimiento | None:
    return (
        db.query(Movimiento)
        .options(joinedload(Movimiento.user), joinedload(Movimiento.categoria))
        .filter(Movimiento.id == movimiento_id, _activos())
        .one_or_none()
    )


def ultimo_movimiento(db: Session, user_id: int) -> Movimiento | None:
    return (
        db.query(Movimiento)
        .options(joinedload(Movimiento.user), joinedload(Movimiento.categoria))
        .filter(Movimiento.user_id == user_id, _activos())
        .order_by(Movimiento.id.desc())
        .first()
    )


def crear_movimiento(
    db: Session,
    *,
    user_id: int,
    categoria_id: int | None,
    monto_cop: int,
    descripcion: str | None,
    mensaje_original: str,
    fecha_gasto: date | None,
    fecha_registro: datetime | None = None,
    medio_pago: str | None = None,
    es_compartido: bool = False,
    porcentaje_compartido: int | None = None,
) -> Movimiento:
    if monto_cop <= 0:
        raise ValueError("El monto debe ser mayor a 0")
    if db.query(User).filter(User.id == user_id).one_or_none() is None:
        raise ValueError("Usuario no existe")
    if categoria_id is not None and db.query(Categoria).filter(Categoria.id == categoria_id).one_or_none() is None:
        raise ValueError("Categoría no existe")
    movimiento = Movimiento(
        user_id=user_id,
        categoria_id=categoria_id,
        monto_cop=monto_cop,
        descripcion=descripcion,
        mensaje_original=mensaje_original or descripcion or "carga manual",
        fue_audio=False,
        fecha_gasto=fecha_gasto,
        fecha_registro=a_bogota(fecha_registro) if fecha_registro else ahora_bogota(),
        medio_pago=medio_pago,
        es_compartido=es_compartido,
        porcentaje_compartido=porcentaje_compartido if es_compartido else None,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    registrar_creacion(db, movimiento, origen="admin")
    return obtener_movimiento(db, movimiento.id) or movimiento


def actualizar_movimiento(
    db: Session,
    movimiento: Movimiento,
    *,
    user_id: int | None = None,
    categoria_id: int | None = None,
    monto_cop: int | None = None,
    descripcion: str | None = None,
    mensaje_original: str | None = None,
    fecha_gasto: date | None = None,
    limpiar_categoria: bool = False,
    origen: str = "admin",
    medio_pago: str | None = None,
    es_compartido: bool | None = None,
    porcentaje_compartido: int | None = None,
) -> Movimiento:
    antes = _movimiento_a_dict(movimiento)
    if user_id is not None:
        if db.query(User).filter(User.id == user_id).one_or_none() is None:
            raise ValueError("Usuario no existe")
        movimiento.user_id = user_id
    if limpiar_categoria:
        movimiento.categoria_id = None
    elif categoria_id is not None:
        if db.query(Categoria).filter(Categoria.id == categoria_id).one_or_none() is None:
            raise ValueError("Categoría no existe")
        movimiento.categoria_id = categoria_id
    if monto_cop is not None:
        if monto_cop <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        movimiento.monto_cop = monto_cop
    if descripcion is not None:
        movimiento.descripcion = descripcion or None
    if mensaje_original is not None:
        movimiento.mensaje_original = mensaje_original
    if fecha_gasto is not None:
        movimiento.fecha_gasto = fecha_gasto
    if medio_pago is not None:
        movimiento.medio_pago = medio_pago
    if es_compartido is not None:
        movimiento.es_compartido = es_compartido
        movimiento.porcentaje_compartido = porcentaje_compartido if es_compartido else None
    # Cascada: sincronizar cambios a la cuota vinculada
    if movimiento.compra_cuotas_id:
        from db.models import CompraCuotas

        cuota = db.query(CompraCuotas).filter_by(id=movimiento.compra_cuotas_id).one_or_none()
        if cuota:
            if monto_cop is not None:
                cuota.valor_total_cop = movimiento.monto_cop
                if cuota.num_cuotas > 0:
                    cuota.valor_cuota_cop = cuota.valor_total_cop // cuota.num_cuotas
                cuota.saldo_pendiente_cop = max(0, cuota.valor_total_cop - (cuota.cuotas_pagadas * cuota.valor_cuota_cop))
            if descripcion is not None:
                cuota.establecimiento = movimiento.descripcion or cuota.establecimiento
            if fecha_gasto is not None:
                cuota.fecha_compra = movimiento.fecha_gasto or cuota.fecha_compra
    db.commit()
    db.refresh(movimiento)
    registrar_edicion(db, movimiento, antes, origen=origen)
    return obtener_movimiento(db, movimiento.id) or movimiento


def eliminar_movimiento(db: Session, movimiento: Movimiento, *, origen: str = "admin") -> None:
    registrar_borrado(db, movimiento, origen=origen)
    ahora = ahora_bogota()
    movimiento.eliminado_en = ahora
    # Cascada: si tiene cuota vinculada, soft-delete la cuota también
    if movimiento.compra_cuotas_id:
        from db.models import CompraCuotas

        cuota = db.query(CompraCuotas).filter_by(id=movimiento.compra_cuotas_id).one_or_none()
        if cuota and cuota.eliminado_en is None:
            cuota.eliminado_en = ahora
    db.commit()


def crear_categoria(db: Session, *, nombre: str, tipo: str) -> Categoria:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre es obligatorio")
    if tipo not in {"gasto", "ingreso"}:
        raise ValueError("El tipo debe ser gasto o ingreso")
    if db.query(Categoria).filter(Categoria.nombre == nombre).one_or_none():
        raise ValueError("Ya existe una categoría con ese nombre")
    cat = Categoria(nombre=nombre, tipo=tipo)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def actualizar_categoria(
    db: Session,
    categoria: Categoria,
    *,
    nombre: str | None = None,
    tipo: str | None = None,
) -> Categoria:
    if nombre is not None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio")
        otra = db.query(Categoria).filter(Categoria.nombre == nombre).one_or_none()
        if otra and otra.id != categoria.id:
            raise ValueError("Ya existe una categoría con ese nombre")
        categoria.nombre = nombre
    if tipo is not None:
        if tipo not in {"gasto", "ingreso"}:
            raise ValueError("El tipo debe ser gasto o ingreso")
        categoria.tipo = tipo
    db.commit()
    db.refresh(categoria)
    return categoria


def eliminar_categoria(db: Session, categoria: Categoria) -> None:
    usados = db.query(Movimiento).filter(Movimiento.categoria_id == categoria.id).count()
    if usados:
        raise ValueError(f"No se puede borrar: hay {usados} movimiento(s) en esta categoría")
    db.delete(categoria)
    db.commit()


def crear_usuario(db: Session, *, nombre: str, numero_whatsapp: str) -> User:
    nombre = nombre.strip()
    numero = "".join(ch for ch in numero_whatsapp if ch.isdigit())
    if not nombre or not numero:
        raise ValueError("Nombre y número son obligatorios")
    if db.query(User).filter(User.numero_whatsapp == numero).one_or_none():
        raise ValueError("Ese número de WhatsApp ya está registrado")
    user = User(nombre=nombre, numero_whatsapp=numero)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def actualizar_usuario(
    db: Session,
    user: User,
    *,
    nombre: str | None = None,
    numero_whatsapp: str | None = None,
) -> User:
    if nombre is not None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio")
        user.nombre = nombre
    if numero_whatsapp is not None:
        numero = "".join(ch for ch in numero_whatsapp if ch.isdigit())
        if not numero:
            raise ValueError("El número es obligatorio")
        otro = db.query(User).filter(User.numero_whatsapp == numero).one_or_none()
        if otro and otro.id != user.id:
            raise ValueError("Ese número de WhatsApp ya está registrado")
        user.numero_whatsapp = numero
    db.commit()
    db.refresh(user)
    return user


def eliminar_usuario(db: Session, user: User) -> None:
    usados = db.query(Movimiento).filter(Movimiento.user_id == user.id).count()
    if usados:
        raise ValueError(f"No se puede borrar: hay {usados} movimiento(s) de este usuario")
    db.delete(user)
    db.commit()
