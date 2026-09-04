from __future__ import annotations

from datetime import date
from calendar import monthrange

from sqlalchemy.orm import Session, joinedload

from db.models import CompraCuotas, TarjetaCredito, User


def crear_tarjeta(
    db: Session,
    *,
    user_id: int,
    banco: str,
    nombre: str,
    fecha_corte: int,
    fecha_pago: int,
    ultimos_4: str | None = None,
    tasa_ea: float | None = None,
    cupo_total_cop: int | None = None,
) -> TarjetaCredito:
    if db.query(User).filter_by(id=user_id).one_or_none() is None:
        raise ValueError("Usuario no existe")
    if not 1 <= fecha_corte <= 31:
        raise ValueError("Fecha de corte debe estar entre 1 y 31")
    if not 1 <= fecha_pago <= 31:
        raise ValueError("Fecha de pago debe estar entre 1 y 31")

    tarjeta = TarjetaCredito(
        user_id=user_id,
        banco=banco.strip(),
        nombre=nombre.strip(),
        ultimos_4=ultimos_4.strip()[-4:] if ultimos_4 else None,
        fecha_corte=fecha_corte,
        fecha_pago=fecha_pago,
        tasa_ea=tasa_ea,
        cupo_total_cop=cupo_total_cop,
    )
    db.add(tarjeta)
    db.commit()
    db.refresh(tarjeta)
    return tarjeta


def listar_tarjetas(
    db: Session,
    *,
    user_id: int | None = None,
    user_ids: list[int] | None = None,
    solo_activas: bool = True,
) -> list[TarjetaCredito]:
    q = db.query(TarjetaCredito).options(joinedload(TarjetaCredito.user))
    if user_id:
        q = q.filter(TarjetaCredito.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(TarjetaCredito.user_id.in_(user_ids))
    if solo_activas:
        q = q.filter(TarjetaCredito.activa == True)  # noqa: E712
    return q.order_by(TarjetaCredito.banco, TarjetaCredito.nombre).all()


def obtener_tarjeta(db: Session, tarjeta_id: int) -> TarjetaCredito | None:
    return (
        db.query(TarjetaCredito)
        .options(joinedload(TarjetaCredito.user))
        .filter(TarjetaCredito.id == tarjeta_id)
        .one_or_none()
    )


def actualizar_tarjeta(
    db: Session,
    tarjeta: TarjetaCredito,
    *,
    banco: str | None = None,
    nombre: str | None = None,
    ultimos_4: str | None = None,
    fecha_corte: int | None = None,
    fecha_pago: int | None = None,
    tasa_ea: float | None = None,
    cupo_total_cop: int | None = None,
    activa: bool | None = None,
) -> TarjetaCredito:
    if banco is not None:
        tarjeta.banco = banco.strip()
    if nombre is not None:
        tarjeta.nombre = nombre.strip()
    if ultimos_4 is not None:
        tarjeta.ultimos_4 = ultimos_4.strip()[-4:] if ultimos_4 else None
    if fecha_corte is not None:
        if not 1 <= fecha_corte <= 31:
            raise ValueError("Fecha de corte debe estar entre 1 y 31")
        tarjeta.fecha_corte = fecha_corte
    if fecha_pago is not None:
        if not 1 <= fecha_pago <= 31:
            raise ValueError("Fecha de pago debe estar entre 1 y 31")
        tarjeta.fecha_pago = fecha_pago
    if tasa_ea is not None:
        tarjeta.tasa_ea = tasa_ea
    if cupo_total_cop is not None:
        tarjeta.cupo_total_cop = cupo_total_cop
    if activa is not None:
        tarjeta.activa = activa
    db.commit()
    db.refresh(tarjeta)
    return tarjeta


def eliminar_tarjeta(db: Session, tarjeta: TarjetaCredito) -> None:
    tarjeta.activa = False
    db.commit()


def serializar_tarjeta(t: TarjetaCredito) -> dict:
    return {
        "id": t.id,
        "user_id": t.user_id,
        "usuario": t.user.nombre if t.user else None,
        "banco": t.banco,
        "nombre": t.nombre,
        "ultimos_4": t.ultimos_4,
        "fecha_corte": t.fecha_corte,
        "fecha_pago": t.fecha_pago,
        "tasa_ea": t.tasa_ea,
        "cupo_total_cop": t.cupo_total_cop,
        "activa": t.activa,
    }


def calcular_fecha_primera_cuota(
    fecha_compra: date,
    fecha_corte: int,
    fecha_pago: int,
) -> date:
    """Calcula cuándo se paga la primera cuota según el ciclo de facturación.

    Si la compra es antes del corte del mes, la primera cuota se paga en el
    fecha_pago de ese mismo mes. Si es después del corte, se paga en el
    fecha_pago del mes siguiente.
    """
    y, m = fecha_compra.year, fecha_compra.month
    # Ajustar fecha_corte al máximo del mes si excede
    max_dia = monthrange(y, m)[1]
    corte_real = min(fecha_corte, max_dia)

    if fecha_compra.day <= corte_real:
        # Compra antes del corte → pago este mes
        pago_dia = min(fecha_pago, max_dia)
        return date(y, m, pago_dia)
    else:
        # Compra después del corte → pago el mes siguiente
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
        max_dia = monthrange(y, m)[1]
        pago_dia = min(fecha_pago, max_dia)
        return date(y, m, pago_dia)


def proyectar_cuotas_por_mes(
    db: Session,
    *,
    tarjeta_id: int | None = None,
    user_id: int | None = None,
    user_ids: list[int] | None = None,
    meses: int = 6,
) -> dict[str, dict]:
    """Proyecta cuotas pendientes agrupadas por mes para los próximos N meses.

    Returns dict con keys "YYYY-MM" y valores:
      {"total": int, "compras": [{"id", "establecimiento", "valor_cuota", "cuota_num", "num_cuotas"}]}
    """
    q = (
        db.query(CompraCuotas)
        .filter(
            CompraCuotas.liquidada == False,  # noqa: E712
            CompraCuotas.eliminado_en.is_(None),
        )
    )
    if tarjeta_id:
        q = q.filter(CompraCuotas.tarjeta_id == tarjeta_id)
    if user_id:
        q = q.filter(CompraCuotas.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(CompraCuotas.user_id.in_(user_ids))
    compras = q.all()

    from tiempo import ahora_bogota
    hoy = ahora_bogota().date()
    projection: dict[str, dict] = {}

    for compra in compras:
        # Determinar fecha de primera cuota
        primera = compra.fecha_primera_cuota
        if not primera and compra.tarjeta_id:
            tarjeta = db.query(TarjetaCredito).get(compra.tarjeta_id)
            if tarjeta:
                primera = calcular_fecha_primera_cuota(
                    compra.fecha_compra, tarjeta.fecha_corte, tarjeta.fecha_pago,
                )
        if not primera:
            # Fallback: asumir primer pago un mes después de la compra
            y, m = compra.fecha_compra.year, compra.fecha_compra.month
            if m == 12:
                primera = date(y + 1, 1, compra.fecha_compra.day)
            else:
                max_dia = monthrange(y, m + 1)[1]
                primera = date(y, m + 1, min(compra.fecha_compra.day, max_dia))

        for i in range(compra.num_cuotas):
            cuota_num = i + 1
            # Solo cuotas no pagadas
            if cuota_num <= compra.cuotas_pagadas:
                continue
            # Calcular mes de esta cuota
            cuota_month_offset = i
            y = primera.year + (primera.month - 1 + cuota_month_offset) // 12
            m = (primera.month - 1 + cuota_month_offset) % 12 + 1
            mes_key = f"{y}-{m:02d}"

            # Solo proyectar meses futuros dentro del rango
            mes_date = date(y, m, 1)
            mes_hoy = date(hoy.year, hoy.month, 1)
            diff_months = (mes_date.year - mes_hoy.year) * 12 + (mes_date.month - mes_hoy.month)
            if diff_months < 0 or diff_months >= meses:
                continue

            if mes_key not in projection:
                projection[mes_key] = {"total": 0, "compras": []}
            projection[mes_key]["total"] += compra.valor_cuota_cop
            projection[mes_key]["compras"].append({
                "id": compra.id,
                "establecimiento": compra.establecimiento,
                "valor_cuota": compra.valor_cuota_cop,
                "cuota_num": cuota_num,
                "num_cuotas": compra.num_cuotas,
            })

    return dict(sorted(projection.items()))
