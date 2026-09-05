from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Categoria, Movimiento, Presupuesto, User
from tiempo import ahora_bogota


def crear_presupuesto(
    db: Session,
    *,
    user_id: int,
    categoria_id: int,
    monto_limite_cop: int,
    mes_vigente: str,
) -> Presupuesto:
    if monto_limite_cop <= 0:
        raise ValueError("El limite debe ser mayor a 0")
    existente = (
        db.query(Presupuesto)
        .filter_by(user_id=user_id, categoria_id=categoria_id, mes_vigente=mes_vigente)
        .one_or_none()
    )
    if existente:
        existente.monto_limite_cop = monto_limite_cop
        db.commit()
        db.refresh(existente)
        return existente
    p = Presupuesto(
        user_id=user_id,
        categoria_id=categoria_id,
        monto_limite_cop=monto_limite_cop,
        mes_vigente=mes_vigente,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def listar_presupuestos(
    db: Session,
    *,
    user_id: int | None = None,
    user_ids: list[int] | None = None,
    mes: str | None = None,
) -> list[Presupuesto]:
    q = db.query(Presupuesto)
    if user_id:
        q = q.filter(Presupuesto.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(Presupuesto.user_id.in_(user_ids))
    if mes:
        q = q.filter(Presupuesto.mes_vigente == mes)
    return q.order_by(Presupuesto.id).all()


def eliminar_presupuesto(db: Session, presupuesto: Presupuesto) -> None:
    db.delete(presupuesto)
    db.commit()


def presupuesto_vs_real(db: Session, *, user_id: int, mes: str) -> list[dict]:
    presupuestos = (
        db.query(Presupuesto).filter_by(user_id=user_id, mes_vigente=mes).all()
    )
    resultado = []
    for p in presupuestos:
        gastado = (
            db.query(func.coalesce(func.sum(Movimiento.monto_cop), 0))
            .filter(
                Movimiento.user_id == user_id,
                Movimiento.categoria_id == p.categoria_id,
                Movimiento.eliminado_en.is_(None),
                func.to_char(Movimiento.fecha_gasto, "YYYY-MM") == mes,
            )
            .scalar()
            or 0
        )
        cat = db.query(Categoria).filter_by(id=p.categoria_id).one_or_none()
        porcentaje = (
            round(gastado / p.monto_limite_cop * 100) if p.monto_limite_cop > 0 else 0
        )
        resultado.append(
            {
                "categoria_id": p.categoria_id,
                "categoria": cat.nombre if cat else "?",
                "limite": p.monto_limite_cop,
                "gastado": int(gastado),
                "porcentaje": porcentaje,
                "restante": p.monto_limite_cop - int(gastado),
            }
        )
    return resultado


def alerta_presupuesto(
    db: Session, user_id: int, categoria_id: int | None, monto_nuevo: int
) -> str | None:
    if not categoria_id:
        return None
    mes = ahora_bogota().strftime("%Y-%m")
    p = (
        db.query(Presupuesto)
        .filter_by(user_id=user_id, categoria_id=categoria_id, mes_vigente=mes)
        .one_or_none()
    )
    if not p:
        return None
    gastado = (
        db.query(func.coalesce(func.sum(Movimiento.monto_cop), 0))
        .filter(
            Movimiento.user_id == user_id,
            Movimiento.categoria_id == categoria_id,
            Movimiento.eliminado_en.is_(None),
            func.to_char(Movimiento.fecha_gasto, "YYYY-MM") == mes,
        )
        .scalar()
        or 0
    )
    total = int(gastado) + monto_nuevo
    porcentaje = (
        round(total / p.monto_limite_cop * 100) if p.monto_limite_cop > 0 else 0
    )
    if porcentaje >= 80:
        from utils import format_cop

        cat = db.query(Categoria).filter_by(id=categoria_id).one_or_none()
        cat_nombre = cat.nombre if cat else "esta categoria"
        return (
            f"\u26a0\ufe0f Llevas {format_cop(total)} de "
            f"{format_cop(p.monto_limite_cop)} en {cat_nombre} ({porcentaje}%)"
        )
    return None


def serializar_presupuesto(p: Presupuesto) -> dict:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "usuario": p.user.nombre if p.user else None,
        "categoria_id": p.categoria_id,
        "categoria": p.categoria.nombre if p.categoria else None,
        "monto_limite_cop": p.monto_limite_cop,
        "mes_vigente": p.mes_vigente,
    }
