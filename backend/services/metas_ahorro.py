"""CRUD para metas de ahorro."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from db.models import MetaAhorro, User


def crear_meta(
    db: Session,
    *,
    user_id: int,
    nombre: str,
    monto_objetivo_cop: int,
    monto_actual_cop: int = 0,
    fecha_limite: date | None = None,
) -> MetaAhorro:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre es obligatorio")
    if monto_objetivo_cop <= 0:
        raise ValueError("El monto objetivo debe ser mayor a 0")
    if db.query(User).filter_by(id=user_id).one_or_none() is None:
        raise ValueError("Usuario no existe")
    existente = db.query(MetaAhorro).filter_by(user_id=user_id, nombre=nombre).one_or_none()
    if existente:
        raise ValueError("Ya existe una meta con ese nombre")
    meta = MetaAhorro(
        user_id=user_id,
        nombre=nombre,
        monto_objetivo_cop=monto_objetivo_cop,
        monto_actual_cop=monto_actual_cop,
        fecha_limite=fecha_limite,
    )
    db.add(meta)
    db.commit()
    db.refresh(meta)
    return meta


def listar_metas(
    db: Session,
    *,
    user_id: int | None = None,
    user_ids: list[int] | None = None,
    solo_activas: bool = True,
) -> list[MetaAhorro]:
    q = db.query(MetaAhorro)
    if solo_activas:
        q = q.filter(MetaAhorro.activa == True)  # noqa: E712
    if user_id:
        q = q.filter(MetaAhorro.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(MetaAhorro.user_id.in_(user_ids))
    return q.order_by(MetaAhorro.id.desc()).all()


def actualizar_meta(
    db: Session,
    meta: MetaAhorro,
    *,
    nombre: str | None = None,
    monto_objetivo_cop: int | None = None,
    monto_actual_cop: int | None = None,
    fecha_limite: date | None = ...,  # type: ignore[assignment]
    activa: bool | None = None,
) -> MetaAhorro:
    if nombre is not None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio")
        meta.nombre = nombre
    if monto_objetivo_cop is not None:
        if monto_objetivo_cop <= 0:
            raise ValueError("El monto objetivo debe ser mayor a 0")
        meta.monto_objetivo_cop = monto_objetivo_cop
    if monto_actual_cop is not None:
        if monto_actual_cop < 0:
            raise ValueError("El monto actual no puede ser negativo")
        meta.monto_actual_cop = monto_actual_cop
    if fecha_limite is not ...:
        meta.fecha_limite = fecha_limite  # type: ignore[assignment]
    if activa is not None:
        meta.activa = activa
    db.commit()
    db.refresh(meta)
    return meta


def eliminar_meta(db: Session, meta: MetaAhorro) -> None:
    db.delete(meta)
    db.commit()


def serializar_meta(meta: MetaAhorro) -> dict:
    progreso = 0
    if meta.monto_objetivo_cop > 0:
        progreso = round(meta.monto_actual_cop / meta.monto_objetivo_cop * 100)
    return {
        "id": meta.id,
        "user_id": meta.user_id,
        "nombre": meta.nombre,
        "monto_objetivo_cop": meta.monto_objetivo_cop,
        "monto_actual_cop": meta.monto_actual_cop,
        "fecha_limite": meta.fecha_limite.isoformat() if meta.fecha_limite else None,
        "activa": meta.activa,
        "progreso": min(progreso, 100),
    }
