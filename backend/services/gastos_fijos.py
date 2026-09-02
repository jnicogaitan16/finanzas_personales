from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from db.models import Categoria, GastoFijo, User


def crear_gasto_fijo(
    db: Session,
    *,
    user_id: int,
    categoria_id: int,
    nombre: str,
    monto_cop: int,
    es_compartido: bool = False,
    porcentaje_compartido: int | None = None,
    dia_esperado: int | None = None,
) -> GastoFijo:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre es obligatorio")
    if monto_cop <= 0:
        raise ValueError("El monto debe ser mayor a 0")
    if db.query(User).filter_by(id=user_id).one_or_none() is None:
        raise ValueError("Usuario no existe")
    if db.query(Categoria).filter_by(id=categoria_id).one_or_none() is None:
        raise ValueError("Categoria no existe")
    existente = db.query(GastoFijo).filter_by(user_id=user_id, nombre=nombre).one_or_none()
    if existente:
        raise ValueError("Ya existe un gasto fijo con ese nombre para este usuario")
    gf = GastoFijo(
        user_id=user_id,
        categoria_id=categoria_id,
        nombre=nombre,
        monto_cop=monto_cop,
        es_compartido=es_compartido,
        porcentaje_compartido=porcentaje_compartido if es_compartido else None,
        dia_esperado=dia_esperado,
    )
    db.add(gf)
    db.commit()
    db.refresh(gf)
    return gf


def listar_gastos_fijos(
    db: Session,
    *,
    user_id: int | None = None,
    solo_activos: bool = True,
) -> list[GastoFijo]:
    q = db.query(GastoFijo).options(
        joinedload(GastoFijo.user), joinedload(GastoFijo.categoria)
    )
    if user_id:
        q = q.filter(GastoFijo.user_id == user_id)
    if solo_activos:
        q = q.filter(GastoFijo.activo == True)  # noqa: E712
    return q.order_by(GastoFijo.id).all()


def actualizar_gasto_fijo(
    db: Session,
    gf: GastoFijo,
    *,
    nombre: str | None = None,
    monto_cop: int | None = None,
    categoria_id: int | None = None,
    es_compartido: bool | None = None,
    porcentaje_compartido: int | None = None,
    activo: bool | None = None,
    dia_esperado: int | None = None,
) -> GastoFijo:
    if nombre is not None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio")
        gf.nombre = nombre
    if monto_cop is not None:
        if monto_cop <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        gf.monto_cop = monto_cop
    if categoria_id is not None:
        gf.categoria_id = categoria_id
    if es_compartido is not None:
        gf.es_compartido = es_compartido
    if porcentaje_compartido is not None:
        gf.porcentaje_compartido = porcentaje_compartido
    if activo is not None:
        gf.activo = activo
    if dia_esperado is not None:
        gf.dia_esperado = dia_esperado
    db.commit()
    db.refresh(gf)
    return gf


def eliminar_gasto_fijo(db: Session, gf: GastoFijo) -> None:
    db.delete(gf)
    db.commit()


def serializar_gasto_fijo(gf: GastoFijo) -> dict:
    return {
        "id": gf.id,
        "user_id": gf.user_id,
        "usuario": gf.user.nombre if gf.user else None,
        "categoria_id": gf.categoria_id,
        "categoria": gf.categoria.nombre if gf.categoria else None,
        "nombre": gf.nombre,
        "monto_cop": gf.monto_cop,
        "es_compartido": gf.es_compartido,
        "porcentaje_compartido": gf.porcentaje_compartido,
        "activo": gf.activo,
        "dia_esperado": gf.dia_esperado,
    }
