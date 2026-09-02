from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload, subqueryload

from db.models import Categoria, CompraCuotas, Movimiento, User
from services.audit import registrar_creacion
from tiempo import ahora_bogota


def crear_compra(
    db: Session,
    *,
    user_id: int,
    fecha_compra: date,
    establecimiento: str,
    valor_total_cop: int,
    num_cuotas: int,
    tarjeta: str | None = None,
    tasa_ea: float | None = None,
    es_compartido: bool = False,
    descripcion: str | None = None,
    numero_transaccion: str | None = None,
    movimiento_id: int | None = None,
) -> CompraCuotas:
    if valor_total_cop <= 0:
        raise ValueError("El valor debe ser mayor a 0")
    if num_cuotas <= 0:
        raise ValueError("El numero de cuotas debe ser mayor a 0")
    if db.query(User).filter_by(id=user_id).one_or_none() is None:
        raise ValueError("Usuario no existe")
    valor_cuota = valor_total_cop // num_cuotas
    compra = CompraCuotas(
        user_id=user_id,
        fecha_compra=fecha_compra,
        establecimiento=establecimiento.strip(),
        descripcion=descripcion,
        valor_total_cop=valor_total_cop,
        num_cuotas=num_cuotas,
        valor_cuota_cop=valor_cuota,
        tasa_ea=tasa_ea,
        numero_transaccion=numero_transaccion,
        tarjeta=tarjeta,
        saldo_pendiente_cop=valor_total_cop,
    )
    db.add(compra)
    db.commit()
    db.refresh(compra)

    # Vincular o crear movimiento
    if movimiento_id:
        # Vincular movimiento existente (creado desde /movimientos)
        mov = db.query(Movimiento).filter_by(id=movimiento_id).one_or_none()
        if mov:
            mov.compra_cuotas_id = compra.id
            db.commit()
    else:
        # Crear movimiento nuevo (creado desde /cuotas)
        cat_tarjeta = db.query(Categoria).filter_by(nombre="Tarjeta").one_or_none()
        mov = Movimiento(
            user_id=user_id,
            categoria_id=cat_tarjeta.id if cat_tarjeta else None,
            monto_cop=valor_total_cop,
            descripcion=establecimiento.strip(),
            mensaje_original=f"Compra TC: {establecimiento.strip()}",
            fue_audio=False,
            fecha_registro=ahora_bogota(),
            fecha_gasto=fecha_compra,
            medio_pago="tarjeta_credito",
            es_compartido=es_compartido,
            porcentaje_compartido=50 if es_compartido else None,
            compra_cuotas_id=compra.id,
        )
        db.add(mov)
        db.commit()
        db.refresh(mov)
        registrar_creacion(db, mov, origen="admin")

    return compra


def registrar_pago(db: Session, compra: CompraCuotas) -> Movimiento:
    if compra.liquidada:
        raise ValueError("Esta compra ya esta liquidada")
    compra.cuotas_pagadas += 1
    compra.saldo_pendiente_cop = max(0, compra.saldo_pendiente_cop - compra.valor_cuota_cop)
    compra.fecha_ultima_cuota = ahora_bogota().date()
    if compra.cuotas_pagadas >= compra.num_cuotas:
        compra.liquidada = True
        compra.saldo_pendiente_cop = 0
    mov = Movimiento(
        user_id=compra.user_id,
        monto_cop=compra.valor_cuota_cop,
        descripcion=f"{compra.establecimiento} ({compra.cuotas_pagadas}/{compra.num_cuotas})",
        mensaje_original=f"Cuota {compra.cuotas_pagadas}/{compra.num_cuotas} - {compra.establecimiento}",
        fecha_registro=ahora_bogota(),
        fecha_gasto=ahora_bogota().date(),
        compra_cuotas_id=compra.id,
    )
    db.add(mov)
    db.commit()
    db.refresh(compra)
    db.refresh(mov)
    registrar_creacion(db, mov, origen="admin")
    return mov


def listar_compras(
    db: Session,
    *,
    user_id: int | None = None,
    solo_activas: bool = True,
) -> list[CompraCuotas]:
    q = (
        db.query(CompraCuotas)
        .options(joinedload(CompraCuotas.user), subqueryload(CompraCuotas.pagos))
        .filter(CompraCuotas.eliminado_en.is_(None))
    )
    if user_id:
        q = q.filter(CompraCuotas.user_id == user_id)
    if solo_activas:
        q = q.filter(CompraCuotas.liquidada == False)  # noqa: E712
    return q.order_by(CompraCuotas.fecha_compra.desc()).all()


def obtener_compra(db: Session, compra_id: int) -> CompraCuotas | None:
    return (
        db.query(CompraCuotas)
        .options(joinedload(CompraCuotas.user), subqueryload(CompraCuotas.pagos))
        .filter(CompraCuotas.id == compra_id, CompraCuotas.eliminado_en.is_(None))
        .one_or_none()
    )


def eliminar_compra(db: Session, compra: CompraCuotas) -> None:
    compra.eliminado_en = ahora_bogota()
    db.commit()


def serializar_compra(c: CompraCuotas, db: Session | None = None) -> dict:
    # Verificar si el movimiento vinculado es compartido
    es_compartido = False
    try:
        if c.pagos:
            for p in c.pagos:
                if p.es_compartido and p.eliminado_en is None:
                    es_compartido = True
                    break
    except Exception:
        pass
    return {
        "id": c.id,
        "user_id": c.user_id,
        "usuario": c.user.nombre if c.user else None,
        "fecha_compra": c.fecha_compra.isoformat() if c.fecha_compra else None,
        "establecimiento": c.establecimiento,
        "descripcion": c.descripcion,
        "valor_total_cop": c.valor_total_cop,
        "num_cuotas": c.num_cuotas,
        "cuotas_pagadas": c.cuotas_pagadas,
        "valor_cuota_cop": c.valor_cuota_cop,
        "valor_intereses_cop": c.valor_intereses_cop,
        "tasa_ea": c.tasa_ea,
        "numero_transaccion": c.numero_transaccion,
        "tarjeta": c.tarjeta,
        "saldo_pendiente_cop": c.saldo_pendiente_cop,
        "liquidada": c.liquidada,
        "cuotas_restantes": c.cuotas_restantes,
        "es_compartido": es_compartido,
    }
