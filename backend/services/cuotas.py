from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload, subqueryload

from db.models import Categoria, CompraCuotas, Movimiento, TarjetaCredito, User
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
    tarjeta_id: int | None = None,
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

    # Calcular fecha primera cuota si hay tarjeta vinculada
    fecha_primera_cuota = None
    if tarjeta_id:
        t = db.query(TarjetaCredito).filter_by(id=tarjeta_id).one_or_none()
        if t:
            from services.tarjetas import calcular_fecha_primera_cuota
            fecha_primera_cuota = calcular_fecha_primera_cuota(
                fecha_compra, t.fecha_corte, t.fecha_pago,
            )
            if not tarjeta:
                tarjeta = t.nombre
            if tasa_ea is None and t.tasa_ea:
                tasa_ea = t.tasa_ea

    compra = CompraCuotas(
        user_id=user_id,
        tarjeta_id=tarjeta_id,
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
        fecha_primera_cuota=fecha_primera_cuota,
    )
    db.add(compra)
    db.commit()
    db.refresh(compra)

    # Vincular movimiento existente si viene de /movimientos
    if movimiento_id:
        mov = db.query(Movimiento).filter_by(id=movimiento_id).one_or_none()
        if mov:
            mov.compra_cuotas_id = compra.id
            # Ajustar monto del movimiento a la cuota mensual (no el total)
            mov.monto_cop = valor_cuota
            mov.descripcion = f"{establecimiento.strip()} (1/{num_cuotas})"
            db.commit()

    # No crear Movimiento por el monto total. Las cuotas mensuales se
    # registran individualmente con registrar_pago() cuando se pagan.

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
    user_ids: list[int] | None = None,
    solo_activas: bool = True,
) -> list[CompraCuotas]:
    q = (
        db.query(CompraCuotas)
        .options(joinedload(CompraCuotas.user), joinedload(CompraCuotas.tarjeta_rel), subqueryload(CompraCuotas.pagos))
        .filter(CompraCuotas.eliminado_en.is_(None))
    )
    if user_id:
        q = q.filter(CompraCuotas.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(CompraCuotas.user_id.in_(user_ids))
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
    tarjeta_nombre = c.tarjeta
    if c.tarjeta_rel:
        tarjeta_nombre = c.tarjeta_rel.nombre
    return {
        "id": c.id,
        "user_id": c.user_id,
        "usuario": c.user.nombre if c.user else None,
        "tarjeta_id": c.tarjeta_id,
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
        "tarjeta": tarjeta_nombre,
        "saldo_pendiente_cop": c.saldo_pendiente_cop,
        "liquidada": c.liquidada,
        "cuotas_restantes": c.cuotas_restantes,
        "es_compartido": es_compartido,
    }
