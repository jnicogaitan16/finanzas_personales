"""Inteligencia financiera: flujo de caja, alertas y score de salud."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from db.models import (
    Categoria,
    CompraCuotas,
    Deuda,
    GastoFijo,
    IngresoRecurrente,
    Movimiento,
    Presupuesto,
)
from services.ingresos import ingreso_esperado_mes
from tiempo import ahora_bogota


# ── Flujo de caja ────────────────────────────────────────────────────


def flujo_de_caja(
    db: Session,
    *,
    mes: str | None = None,
    user_id: int | None = None,
) -> dict:
    """Proyección de flujo de caja mensual.

    Returns:
        ingresos_esperados, gastos_fijos, cuotas_tarjetas,
        gasto_flexible_promedio, disponible_estimado
    """
    hoy = ahora_bogota().date()
    if not mes:
        mes = hoy.strftime("%Y-%m")

    # 1. Ingresos esperados
    q_ing = db.query(IngresoRecurrente).filter(IngresoRecurrente.activo == True)  # noqa: E712
    if user_id:
        q_ing = q_ing.filter(IngresoRecurrente.user_id == user_id)
    ingresos_cfg = q_ing.all()
    ingresos_esperados = sum(ingreso_esperado_mes(i) for i in ingresos_cfg)

    # 2. Gastos fijos
    q_gf = db.query(GastoFijo).filter(GastoFijo.activo == True)  # noqa: E712
    if user_id:
        q_gf = q_gf.filter(GastoFijo.user_id == user_id)
    gastos_fijos = sum(gf.monto_cop for gf in q_gf.all())

    # 3. Cuotas tarjetas del mes
    q_cuotas = db.query(CompraCuotas).filter(
        CompraCuotas.liquidada == False,  # noqa: E712
        CompraCuotas.eliminado_en.is_(None),
    )
    if user_id:
        q_cuotas = q_cuotas.filter(CompraCuotas.user_id == user_id)
    cuotas_mes = sum(c.valor_cuota_cop for c in q_cuotas.all())

    # 4. Gasto flexible = promedio últimos 3 meses de gastos no fijos
    gasto_flex = _promedio_gasto_flexible(db, user_id=user_id, meses=3)

    disponible = ingresos_esperados - gastos_fijos - cuotas_mes - gasto_flex

    return {
        "mes": mes,
        "ingresos_esperados": ingresos_esperados,
        "gastos_fijos": gastos_fijos,
        "cuotas_tarjetas": cuotas_mes,
        "gasto_flexible_promedio": gasto_flex,
        "disponible_estimado": disponible,
    }


def _promedio_gasto_flexible(
    db: Session,
    *,
    user_id: int | None = None,
    meses: int = 3,
) -> int:
    """Promedio mensual de gastos no fijos de los últimos N meses."""
    hoy = ahora_bogota().date()

    # Categorías fijas
    cats_fijos = {
        gf.categoria_id
        for gf in db.query(GastoFijo).filter(GastoFijo.activo == True).all()  # noqa: E712
        if gf.categoria_id
    }

    q = db.query(Movimiento).filter(
        Movimiento.eliminado_en.is_(None),
        Movimiento.fecha_gasto.isnot(None),
    )
    if user_id:
        q = q.filter(Movimiento.user_id == user_id)

    total = 0
    meses_con_datos = set()
    for m in q.all():
        if not m.fecha_gasto:
            continue
        cat = db.query(Categoria).filter_by(id=m.categoria_id).one_or_none()
        if not cat or cat.tipo != "gasto":
            continue
        # Excluir categorías fijas
        if m.categoria_id in cats_fijos:
            continue
        mes_key = m.fecha_gasto.strftime("%Y-%m")
        # Solo últimos N meses (no el actual)
        mes_date = date(int(mes_key[:4]), int(mes_key[5:7]), 1)
        diff = (hoy.year - mes_date.year) * 12 + (hoy.month - mes_date.month)
        if 1 <= diff <= meses:
            total += m.monto_cop
            meses_con_datos.add(mes_key)

    if not meses_con_datos:
        return 0
    return total // len(meses_con_datos)


# ── Alertas ──────────────────────────────────────────────────────────


def obtener_alertas(
    db: Session,
    *,
    user_id: int | None = None,
) -> list[dict]:
    """Genera alertas activas para el usuario."""
    alertas: list[dict] = []
    hoy = ahora_bogota().date()
    mes_actual = hoy.strftime("%Y-%m")

    # 1. Presupuestos al 80%+
    q_ppto = db.query(Presupuesto).filter(Presupuesto.mes_vigente == mes_actual)
    if user_id:
        q_ppto = q_ppto.filter(Presupuesto.user_id == user_id)

    for p in q_ppto.all():
        gastado = _gastado_categoria_mes(db, p.user_id, p.categoria_id, mes_actual)
        porcentaje = round(gastado / p.monto_limite_cop * 100) if p.monto_limite_cop > 0 else 0
        if porcentaje >= 80:
            cat = db.query(Categoria).filter_by(id=p.categoria_id).one_or_none()
            cat_nombre = cat.nombre if cat else "?"
            nivel = "critico" if porcentaje >= 100 else "advertencia"
            alertas.append({
                "tipo": "presupuesto",
                "nivel": nivel,
                "titulo": f"{cat_nombre}: {porcentaje}% del presupuesto",
                "detalle": f"Gastado {gastado:,} de {p.monto_limite_cop:,} COP",
            })

    # 2. Próximo pago de tarjeta (≤ 5 días)
    from db.models import TarjetaCredito
    q_tj = db.query(TarjetaCredito).filter(TarjetaCredito.activa == True)  # noqa: E712
    if user_id:
        q_tj = q_tj.filter(TarjetaCredito.user_id == user_id)

    for t in q_tj.all():
        # Calcular próximo pago
        pago_dia = min(t.fecha_pago, 28)
        try:
            prox_pago = date(hoy.year, hoy.month, pago_dia)
            if prox_pago < hoy:
                # Ya pasó este mes, buscar siguiente
                if hoy.month == 12:
                    prox_pago = date(hoy.year + 1, 1, pago_dia)
                else:
                    prox_pago = date(hoy.year, hoy.month + 1, pago_dia)
        except ValueError:
            continue

        dias_faltan = (prox_pago - hoy).days
        if 0 <= dias_faltan <= 5:
            # Calcular total cuotas de esta tarjeta
            total = sum(
                c.valor_cuota_cop
                for c in db.query(CompraCuotas).filter(
                    CompraCuotas.tarjeta_id == t.id,
                    CompraCuotas.liquidada == False,  # noqa: E712
                    CompraCuotas.eliminado_en.is_(None),
                ).all()
            )
            if total > 0:
                alertas.append({
                    "tipo": "pago_tarjeta",
                    "nivel": "info" if dias_faltan > 2 else "advertencia",
                    "titulo": f"{t.nombre}: pago en {dias_faltan} días",
                    "detalle": f"Total cuotas: {total:,} COP (día {t.fecha_pago})",
                })

    # 3. Deudas activas con saldo alto
    q_deudas = db.query(Deuda).filter(Deuda.activa == True)  # noqa: E712
    if user_id:
        q_deudas = q_deudas.filter(Deuda.user_id == user_id)

    for d in q_deudas.all():
        if d.fecha_limite and d.fecha_limite <= hoy:
            alertas.append({
                "tipo": "deuda_vencida",
                "nivel": "critico",
                "titulo": f"Deuda vencida: {d.nombre}",
                "detalle": f"Saldo: {d.saldo_cop:,} COP, venció {d.fecha_limite.isoformat()}",
            })

    return alertas


def _gastado_categoria_mes(db: Session, user_id: int, categoria_id: int, mes: str) -> int:
    total = 0
    for m in (
        db.query(Movimiento)
        .filter(
            Movimiento.user_id == user_id,
            Movimiento.categoria_id == categoria_id,
            Movimiento.eliminado_en.is_(None),
            Movimiento.fecha_gasto.isnot(None),
        )
        .all()
    ):
        if m.fecha_gasto and m.fecha_gasto.strftime("%Y-%m") == mes:
            total += m.monto_cop
    return total


# ── Score de salud financiera ────────────────────────────────────────


def salud_financiera(
    db: Session,
    *,
    user_id: int | None = None,
) -> dict:
    """Score 0-100 de salud financiera.

    Criterios (25 pts cada uno):
    - Gastos < 90% de ingresos
    - Tiene fondo emergencia (≥ 3 meses gastos fijos)
    - Deuda total < 30% ingreso anual
    - Cumple presupuestos (≥ 80% dentro de límites)
    """
    hoy = ahora_bogota().date()
    mes_actual = hoy.strftime("%Y-%m")
    score = 0
    detalles: list[dict] = []

    # Ingresos
    q_ing = db.query(IngresoRecurrente).filter(IngresoRecurrente.activo == True)  # noqa: E712
    if user_id:
        q_ing = q_ing.filter(IngresoRecurrente.user_id == user_id)
    ingreso_mensual = sum(ingreso_esperado_mes(i) for i in q_ing.all())

    # Gastos fijos
    q_gf = db.query(GastoFijo).filter(GastoFijo.activo == True)  # noqa: E712
    if user_id:
        q_gf = q_gf.filter(GastoFijo.user_id == user_id)
    gastos_fijos = sum(gf.monto_cop for gf in q_gf.all())

    # Gasto total mes actual
    gasto_mes = _gasto_total_mes(db, mes_actual, user_id)

    # 1. Gastos < 90% ingresos
    if ingreso_mensual > 0:
        ratio_gasto = gasto_mes / ingreso_mensual
        if ratio_gasto < 0.9:
            score += 25
            detalles.append({"criterio": "Gastos controlados", "cumple": True, "detalle": f"Gastos son {ratio_gasto:.0%} del ingreso"})
        else:
            detalles.append({"criterio": "Gastos controlados", "cumple": False, "detalle": f"Gastos son {ratio_gasto:.0%} del ingreso (meta: <90%)"})
    else:
        detalles.append({"criterio": "Gastos controlados", "cumple": False, "detalle": "Sin ingresos configurados"})

    # 2. Fondo de emergencia (placeholder — no hay modelo de ahorro aún)
    # Por ahora: si balance mes es positivo, +25
    balance_mes = ingreso_mensual - gasto_mes
    if balance_mes > gastos_fijos:
        score += 25
        detalles.append({"criterio": "Capacidad de ahorro", "cumple": True, "detalle": "Balance positivo mayor a gastos fijos"})
    elif balance_mes > 0:
        score += 12
        detalles.append({"criterio": "Capacidad de ahorro", "cumple": False, "detalle": "Balance positivo pero bajo"})
    else:
        detalles.append({"criterio": "Capacidad de ahorro", "cumple": False, "detalle": "Balance negativo"})

    # 3. Deuda < 30% ingreso anual
    q_deuda = db.query(CompraCuotas).filter(
        CompraCuotas.liquidada == False,  # noqa: E712
        CompraCuotas.eliminado_en.is_(None),
    )
    if user_id:
        q_deuda = q_deuda.filter(CompraCuotas.user_id == user_id)
    deuda_total = sum(c.saldo_pendiente_cop for c in q_deuda.all())

    q_deudas_ext = db.query(Deuda).filter(Deuda.activa == True)  # noqa: E712
    if user_id:
        q_deudas_ext = q_deudas_ext.filter(Deuda.user_id == user_id)
    deuda_total += sum(d.saldo_cop for d in q_deudas_ext.all())

    ingreso_anual = ingreso_mensual * 12
    if ingreso_anual > 0:
        ratio_deuda = deuda_total / ingreso_anual
        if ratio_deuda < 0.3:
            score += 25
            detalles.append({"criterio": "Deuda saludable", "cumple": True, "detalle": f"Deuda es {ratio_deuda:.0%} del ingreso anual"})
        else:
            detalles.append({"criterio": "Deuda saludable", "cumple": False, "detalle": f"Deuda es {ratio_deuda:.0%} del ingreso anual (meta: <30%)"})
    else:
        if deuda_total == 0:
            score += 25
            detalles.append({"criterio": "Deuda saludable", "cumple": True, "detalle": "Sin deudas"})
        else:
            detalles.append({"criterio": "Deuda saludable", "cumple": False, "detalle": "Deuda activa sin ingresos configurados"})

    # 4. Cumple presupuestos
    q_ppto = db.query(Presupuesto).filter(Presupuesto.mes_vigente == mes_actual)
    if user_id:
        q_ppto = q_ppto.filter(Presupuesto.user_id == user_id)
    presupuestos = q_ppto.all()

    if presupuestos:
        cumplidos = 0
        for p in presupuestos:
            gastado = _gastado_categoria_mes(db, p.user_id, p.categoria_id, mes_actual)
            if gastado <= p.monto_limite_cop:
                cumplidos += 1
        pct_cumple = cumplidos / len(presupuestos)
        if pct_cumple >= 0.8:
            score += 25
            detalles.append({"criterio": "Presupuestos", "cumple": True, "detalle": f"{cumplidos}/{len(presupuestos)} dentro del limite"})
        else:
            detalles.append({"criterio": "Presupuestos", "cumple": False, "detalle": f"{cumplidos}/{len(presupuestos)} dentro del limite (meta: 80%+)"})
    else:
        detalles.append({"criterio": "Presupuestos", "cumple": False, "detalle": "Sin presupuestos configurados"})

    return {
        "score": score,
        "max_score": 100,
        "nivel": _nivel_score(score),
        "detalles": detalles,
    }


def _gasto_total_mes(db: Session, mes: str, user_id: int | None) -> int:
    q = db.query(Movimiento).filter(
        Movimiento.eliminado_en.is_(None),
        Movimiento.fecha_gasto.isnot(None),
    )
    if user_id:
        q = q.filter(Movimiento.user_id == user_id)

    total = 0
    for m in q.all():
        if not m.fecha_gasto or m.fecha_gasto.strftime("%Y-%m") != mes:
            continue
        cat = db.query(Categoria).filter_by(id=m.categoria_id).one_or_none()
        if cat and cat.tipo == "gasto":
            total += m.monto_cop
    return total


def _nivel_score(score: int) -> str:
    if score >= 75:
        return "excelente"
    if score >= 50:
        return "bueno"
    if score >= 25:
        return "regular"
    return "critico"
