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
    TarjetaCredito,
)
from services.ingresos import ingreso_esperado_mes
from tiempo import ahora_bogota


# ── Flujo de caja ────────────────────────────────────────────────────


def flujo_de_caja(
    db: Session,
    *,
    mes: str | None = None,
    user_id: int | None = None,
    user_ids: list[int] | None = None,
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
    elif user_ids is not None:
        q_ing = q_ing.filter(IngresoRecurrente.user_id.in_(user_ids))
    ingresos_cfg = q_ing.all()
    ingresos_esperados = sum(ingreso_esperado_mes(i) for i in ingresos_cfg)

    # 2. Gastos fijos
    q_gf = db.query(GastoFijo).filter(GastoFijo.activo == True)  # noqa: E712
    if user_id:
        q_gf = q_gf.filter(GastoFijo.user_id == user_id)
    elif user_ids is not None:
        q_gf = q_gf.filter(GastoFijo.user_id.in_(user_ids))
    gastos_fijos = sum(gf.monto_cop for gf in q_gf.all())

    # 3. Cuotas tarjetas del mes
    q_cuotas = db.query(CompraCuotas).filter(
        CompraCuotas.liquidada == False,  # noqa: E712
        CompraCuotas.eliminado_en.is_(None),
    )
    if user_id:
        q_cuotas = q_cuotas.filter(CompraCuotas.user_id == user_id)
    elif user_ids is not None:
        q_cuotas = q_cuotas.filter(CompraCuotas.user_id.in_(user_ids))
    cuotas_mes = sum(c.valor_cuota_cop for c in q_cuotas.all())

    # 4. Gasto flexible = promedio últimos 3 meses de gastos no fijos
    gasto_flex = _promedio_gasto_flexible(db, user_id=user_id, user_ids=user_ids, meses=3)

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
    user_ids: list[int] | None = None,
    meses: int = 3,
) -> int:
    """Promedio mensual de gastos no fijos de los últimos N meses."""
    hoy = ahora_bogota().date()

    # Categorías fijas (scoped to same users)
    q_gf = db.query(GastoFijo).filter(GastoFijo.activo == True)  # noqa: E712
    if user_id:
        q_gf = q_gf.filter(GastoFijo.user_id == user_id)
    elif user_ids is not None:
        q_gf = q_gf.filter(GastoFijo.user_id.in_(user_ids))
    cats_fijos = {
        gf.categoria_id
        for gf in q_gf.all()
        if gf.categoria_id
    }

    q = db.query(Movimiento).filter(
        Movimiento.eliminado_en.is_(None),
        Movimiento.fecha_gasto.isnot(None),
    )
    if user_id:
        q = q.filter(Movimiento.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(Movimiento.user_id.in_(user_ids))

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
    user_ids: list[int] | None = None,
) -> list[dict]:
    """Genera alertas activas para el usuario."""
    alertas: list[dict] = []
    hoy = ahora_bogota().date()
    mes_actual = hoy.strftime("%Y-%m")

    # 1. Presupuestos al 80%+
    q_ppto = db.query(Presupuesto).filter(Presupuesto.mes_vigente == mes_actual)
    if user_id:
        q_ppto = q_ppto.filter(Presupuesto.user_id == user_id)
    elif user_ids is not None:
        q_ppto = q_ppto.filter(Presupuesto.user_id.in_(user_ids))

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
    elif user_ids is not None:
        q_tj = q_tj.filter(TarjetaCredito.user_id.in_(user_ids))

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

    # 3. Deudas activas vencidas
    q_deudas = db.query(Deuda).filter(Deuda.activa == True)  # noqa: E712
    if user_id:
        q_deudas = q_deudas.filter(Deuda.user_id == user_id)
    elif user_ids is not None:
        q_deudas = q_deudas.filter(Deuda.user_id.in_(user_ids))

    for d in q_deudas.all():
        if d.fecha_limite and d.fecha_limite <= hoy:
            alertas.append({
                "tipo": "deuda_vencida",
                "nivel": "critico",
                "titulo": f"Deuda vencida: {d.nombre}",
                "detalle": f"Saldo: {d.saldo_cop:,} COP, venció {d.fecha_limite.isoformat()}",
            })

    # 4. Gasto inusual: gasto individual > 2x promedio de la categoría
    _alertas_gasto_inusual(db, alertas, hoy, mes_actual, user_id, user_ids)

    # 5. Tendencia alcista: gasto del mes subió > 20% vs mes anterior
    _alertas_tendencia_alcista(db, alertas, hoy, mes_actual, user_id, user_ids)

    # 6. Ingreso no recibido: día de pago pasó sin registro
    _alertas_ingreso_no_recibido(db, alertas, hoy, mes_actual, user_id, user_ids)

    # 7. Cupo TC bajo: cuotas > 80% del cupo
    _alertas_cupo_tc_bajo(db, alertas, user_id, user_ids)

    # 8. Oportunidad de ahorro: gasto en Ocio > 30% del total
    _alertas_oportunidad_ahorro(db, alertas, mes_actual, user_id, user_ids)

    return alertas


def _alertas_gasto_inusual(
    db: Session,
    alertas: list[dict],
    hoy: date,
    mes_actual: str,
    user_id: int | None,
    user_ids: list[int] | None,
) -> None:
    """Gasto individual > 2x el promedio de su categoría en los últimos 3 meses."""
    # Obtener movimientos del mes actual
    q = db.query(Movimiento).filter(
        Movimiento.eliminado_en.is_(None),
        Movimiento.fecha_gasto.isnot(None),
    )
    if user_id:
        q = q.filter(Movimiento.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(Movimiento.user_id.in_(user_ids))

    movs_mes = [m for m in q.all() if m.fecha_gasto and m.fecha_gasto.strftime("%Y-%m") == mes_actual]

    # Promedios por categoría de los últimos 3 meses (excluyendo actual)
    promedios: dict[int, int] = {}
    for m in q.all():
        if not m.fecha_gasto or not m.categoria_id:
            continue
        mes_key = m.fecha_gasto.strftime("%Y-%m")
        mes_date = date(int(mes_key[:4]), int(mes_key[5:7]), 1)
        diff = (hoy.year - mes_date.year) * 12 + (hoy.month - mes_date.month)
        if 1 <= diff <= 3:
            promedios.setdefault(m.categoria_id, []).append(m.monto_cop)  # type: ignore[arg-type]

    prom_cat: dict[int, int] = {}
    for cat_id, montos in promedios.items():  # type: ignore[assignment]
        prom_cat[cat_id] = sum(montos) // len(montos) if montos else 0  # type: ignore[arg-type]

    for m in movs_mes:
        if not m.categoria_id or m.categoria_id not in prom_cat:
            continue
        prom = prom_cat[m.categoria_id]
        if prom > 0 and m.monto_cop > prom * 2:
            cat = db.query(Categoria).filter_by(id=m.categoria_id).one_or_none()
            cat_nombre = cat.nombre if cat else "?"
            alertas.append({
                "tipo": "gasto_inusual",
                "nivel": "advertencia",
                "titulo": f"Gasto inusual en {cat_nombre}",
                "detalle": f"{m.monto_cop:,} COP (promedio: {prom:,} COP)",
            })
            break  # Solo una alerta por categoría para no saturar


def _alertas_tendencia_alcista(
    db: Session,
    alertas: list[dict],
    hoy: date,
    mes_actual: str,
    user_id: int | None,
    user_ids: list[int] | None,
) -> None:
    """Gasto total del mes subió > 20% vs mes anterior."""
    gasto_actual = _gasto_total_mes(db, mes_actual, user_id, user_ids=user_ids)

    # Mes anterior
    if hoy.month == 1:
        mes_anterior = f"{hoy.year - 1}-12"
    else:
        mes_anterior = f"{hoy.year}-{hoy.month - 1:02d}"

    gasto_anterior = _gasto_total_mes(db, mes_anterior, user_id, user_ids=user_ids)

    if gasto_anterior > 0:
        cambio = (gasto_actual - gasto_anterior) / gasto_anterior
        if cambio > 0.2:
            alertas.append({
                "tipo": "tendencia_alcista",
                "nivel": "info",
                "titulo": f"Gasto subió {cambio:.0%} vs mes anterior",
                "detalle": f"Este mes: {gasto_actual:,} COP vs {gasto_anterior:,} COP",
            })


def _alertas_ingreso_no_recibido(
    db: Session,
    alertas: list[dict],
    hoy: date,
    mes_actual: str,
    user_id: int | None,
    user_ids: list[int] | None,
) -> None:
    """Día de pago pasó sin registro de ingreso este mes."""
    q = db.query(IngresoRecurrente).filter(IngresoRecurrente.activo == True)  # noqa: E712
    if user_id:
        q = q.filter(IngresoRecurrente.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(IngresoRecurrente.user_id.in_(user_ids))

    for ing in q.all():
        dias_pago = [d for d in [ing.dia_pago_1, ing.dia_pago_2] if d]
        if not dias_pago:
            continue

        for dia in dias_pago:
            if hoy.day <= dia:
                continue  # Aún no ha llegado el día

            # Verificar si hay un ingreso registrado este mes
            q_mov = db.query(Movimiento).filter(
                Movimiento.user_id == ing.user_id,
                Movimiento.eliminado_en.is_(None),
                Movimiento.fecha_gasto.isnot(None),
            )
            tiene_ingreso = False
            for m in q_mov.all():
                if not m.fecha_gasto:
                    continue
                cat = db.query(Categoria).filter_by(id=m.categoria_id).one_or_none()
                if cat and cat.tipo == "ingreso" and m.fecha_gasto.strftime("%Y-%m") == mes_actual:
                    tiene_ingreso = True
                    break

            if not tiene_ingreso:
                alertas.append({
                    "tipo": "ingreso_no_recibido",
                    "nivel": "advertencia",
                    "titulo": f"¿Recibiste {ing.nombre}?",
                    "detalle": f"Día de pago ({dia}) ya pasó sin registro este mes",
                })
                break  # Una alerta por ingreso recurrente


def _alertas_cupo_tc_bajo(
    db: Session,
    alertas: list[dict],
    user_id: int | None,
    user_ids: list[int] | None,
) -> None:
    """Cuotas pendientes > 80% del cupo total de la tarjeta."""
    q_tc = db.query(TarjetaCredito).filter(TarjetaCredito.activa == True)  # noqa: E712
    if user_id:
        q_tc = q_tc.filter(TarjetaCredito.user_id == user_id)
    elif user_ids is not None:
        q_tc = q_tc.filter(TarjetaCredito.user_id.in_(user_ids))

    for t in q_tc.all():
        if not t.cupo_total_cop or t.cupo_total_cop <= 0:
            continue
        saldo = sum(
            c.saldo_pendiente_cop
            for c in db.query(CompraCuotas).filter(
                CompraCuotas.tarjeta_id == t.id,
                CompraCuotas.liquidada == False,  # noqa: E712
                CompraCuotas.eliminado_en.is_(None),
            ).all()
        )
        uso = saldo / t.cupo_total_cop
        if uso > 0.8:
            alertas.append({
                "tipo": "cupo_tc_bajo",
                "nivel": "critico",
                "titulo": f"Cupo bajo: {t.nombre}",
                "detalle": f"Usando {uso:.0%} del cupo ({saldo:,} de {t.cupo_total_cop:,} COP)",
            })


def _alertas_oportunidad_ahorro(
    db: Session,
    alertas: list[dict],
    mes_actual: str,
    user_id: int | None,
    user_ids: list[int] | None,
) -> None:
    """Gasto en categoría 'Ocio' o 'Entretenimiento' > 30% del gasto total."""
    gasto_total = _gasto_total_mes(db, mes_actual, user_id, user_ids=user_ids)
    if gasto_total <= 0:
        return

    cats_ocio = db.query(Categoria).filter(
        Categoria.tipo == "gasto",
        Categoria.nombre.in_(["Ocio", "Entretenimiento", "Salidas"]),
    ).all()

    gasto_ocio = 0
    for cat in cats_ocio:
        q = db.query(Movimiento).filter(
            Movimiento.categoria_id == cat.id,
            Movimiento.eliminado_en.is_(None),
            Movimiento.fecha_gasto.isnot(None),
        )
        if user_id:
            q = q.filter(Movimiento.user_id == user_id)
        elif user_ids is not None:
            q = q.filter(Movimiento.user_id.in_(user_ids))

        for m in q.all():
            if m.fecha_gasto and m.fecha_gasto.strftime("%Y-%m") == mes_actual:
                gasto_ocio += m.monto_cop

    if gasto_ocio > 0:
        pct = gasto_ocio / gasto_total
        if pct > 0.3:
            alertas.append({
                "tipo": "oportunidad_ahorro",
                "nivel": "info",
                "titulo": f"Ocio es {pct:.0%} de tus gastos",
                "detalle": f"{gasto_ocio:,} COP en ocio de {gasto_total:,} COP total",
            })


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
    user_ids: list[int] | None = None,
) -> dict:
    """Score 0-100 de salud financiera con 8 criterios ponderados.

    Criterios y pesos:
    1. Gastos < 90% ingresos            (15 pts)
    2. Fondo de emergencia              (15 pts)
    3. Deuda < 30% ingreso anual        (15 pts)
    4. Presupuestos cumplidos ≥80%      (10 pts)
    5. Uso de crédito < 50%             (10 pts)
    6. Ingreso diversificado ≥2 fuentes (10 pts)
    7. Tendencia de gasto ≤ prom 3 meses(15 pts)
    8. Consistencia de registro ≥15/mes (10 pts)
    """
    hoy = ahora_bogota().date()
    mes_actual = hoy.strftime("%Y-%m")
    score = 0
    detalles: list[dict] = []

    # ── Datos base ──────────────────────────────────────
    # Ingresos
    q_ing = db.query(IngresoRecurrente).filter(IngresoRecurrente.activo == True)  # noqa: E712
    if user_id:
        q_ing = q_ing.filter(IngresoRecurrente.user_id == user_id)
    elif user_ids is not None:
        q_ing = q_ing.filter(IngresoRecurrente.user_id.in_(user_ids))
    ingresos_cfg = q_ing.all()
    ingreso_mensual = sum(ingreso_esperado_mes(i) for i in ingresos_cfg)

    # Gastos fijos
    q_gf = db.query(GastoFijo).filter(GastoFijo.activo == True)  # noqa: E712
    if user_id:
        q_gf = q_gf.filter(GastoFijo.user_id == user_id)
    elif user_ids is not None:
        q_gf = q_gf.filter(GastoFijo.user_id.in_(user_ids))
    gastos_fijos = sum(gf.monto_cop for gf in q_gf.all())

    # Gasto total mes actual
    gasto_mes = _gasto_total_mes(db, mes_actual, user_id, user_ids=user_ids)

    # ── 1. Gastos controlados (15 pts) ──────────────────
    if ingreso_mensual > 0:
        ratio_gasto = gasto_mes / ingreso_mensual
        if ratio_gasto < 0.9:
            score += 15
            detalles.append({"criterio": "Gastos controlados", "cumple": True, "peso": 15, "detalle": f"Gastos son {ratio_gasto:.0%} del ingreso"})
        else:
            detalles.append({"criterio": "Gastos controlados", "cumple": False, "peso": 15, "detalle": f"Gastos son {ratio_gasto:.0%} del ingreso (meta: <90%)"})
    else:
        detalles.append({"criterio": "Gastos controlados", "cumple": False, "peso": 15, "detalle": "Sin ingresos configurados"})

    # ── 2. Fondo de emergencia (15 pts) ─────────────────
    # Cumple si el balance mensual acumulable >= 3 meses de gastos fijos
    balance_mes = ingreso_mensual - gasto_mes
    fondo_meta = gastos_fijos * 3
    if fondo_meta > 0 and balance_mes >= fondo_meta:
        score += 15
        detalles.append({"criterio": "Fondo de emergencia", "cumple": True, "peso": 15, "detalle": f"Balance cubre {balance_mes // gastos_fijos} meses de gastos fijos"})
    elif balance_mes > gastos_fijos:
        score += 8
        detalles.append({"criterio": "Fondo de emergencia", "cumple": False, "peso": 15, "detalle": f"Balance cubre ~1 mes (meta: 3 meses)"})
    elif balance_mes > 0:
        score += 4
        detalles.append({"criterio": "Fondo de emergencia", "cumple": False, "peso": 15, "detalle": "Balance positivo pero insuficiente"})
    else:
        detalles.append({"criterio": "Fondo de emergencia", "cumple": False, "peso": 15, "detalle": "Balance negativo" if ingreso_mensual > 0 else "Sin ingresos configurados"})

    # ── 3. Deuda saludable (15 pts) ─────────────────────
    q_deuda = db.query(CompraCuotas).filter(
        CompraCuotas.liquidada == False,  # noqa: E712
        CompraCuotas.eliminado_en.is_(None),
    )
    if user_id:
        q_deuda = q_deuda.filter(CompraCuotas.user_id == user_id)
    elif user_ids is not None:
        q_deuda = q_deuda.filter(CompraCuotas.user_id.in_(user_ids))
    deuda_total = sum(c.saldo_pendiente_cop for c in q_deuda.all())

    q_deudas_ext = db.query(Deuda).filter(Deuda.activa == True)  # noqa: E712
    if user_id:
        q_deudas_ext = q_deudas_ext.filter(Deuda.user_id == user_id)
    elif user_ids is not None:
        q_deudas_ext = q_deudas_ext.filter(Deuda.user_id.in_(user_ids))
    deuda_total += sum(d.saldo_cop for d in q_deudas_ext.all())

    ingreso_anual = ingreso_mensual * 12
    if ingreso_anual > 0:
        ratio_deuda = deuda_total / ingreso_anual
        if ratio_deuda < 0.3:
            score += 15
            detalles.append({"criterio": "Deuda saludable", "cumple": True, "peso": 15, "detalle": f"Deuda es {ratio_deuda:.0%} del ingreso anual"})
        else:
            detalles.append({"criterio": "Deuda saludable", "cumple": False, "peso": 15, "detalle": f"Deuda es {ratio_deuda:.0%} del ingreso anual (meta: <30%)"})
    else:
        if deuda_total == 0:
            score += 15
            detalles.append({"criterio": "Deuda saludable", "cumple": True, "peso": 15, "detalle": "Sin deudas"})
        else:
            detalles.append({"criterio": "Deuda saludable", "cumple": False, "peso": 15, "detalle": "Deuda activa sin ingresos configurados"})

    # ── 4. Presupuestos cumplidos (10 pts) ──────────────
    q_ppto = db.query(Presupuesto).filter(Presupuesto.mes_vigente == mes_actual)
    if user_id:
        q_ppto = q_ppto.filter(Presupuesto.user_id == user_id)
    elif user_ids is not None:
        q_ppto = q_ppto.filter(Presupuesto.user_id.in_(user_ids))
    presupuestos = q_ppto.all()

    if presupuestos:
        cumplidos = 0
        for p in presupuestos:
            gastado = _gastado_categoria_mes(db, p.user_id, p.categoria_id, mes_actual)
            if gastado <= p.monto_limite_cop:
                cumplidos += 1
        pct_cumple = cumplidos / len(presupuestos)
        if pct_cumple >= 0.8:
            score += 10
            detalles.append({"criterio": "Presupuestos", "cumple": True, "peso": 10, "detalle": f"{cumplidos}/{len(presupuestos)} dentro del límite"})
        else:
            detalles.append({"criterio": "Presupuestos", "cumple": False, "peso": 10, "detalle": f"{cumplidos}/{len(presupuestos)} dentro del límite (meta: 80%+)"})
    else:
        detalles.append({"criterio": "Presupuestos", "cumple": False, "peso": 10, "detalle": "Sin presupuestos configurados"})

    # ── 5. Uso de crédito < 50% (10 pts) ────────────────
    q_tc = db.query(TarjetaCredito).filter(TarjetaCredito.activa == True)  # noqa: E712
    if user_id:
        q_tc = q_tc.filter(TarjetaCredito.user_id == user_id)
    elif user_ids is not None:
        q_tc = q_tc.filter(TarjetaCredito.user_id.in_(user_ids))
    tarjetas = q_tc.all()

    cupo_total = sum(t.cupo_total_cop or 0 for t in tarjetas)
    saldo_cuotas_tc = sum(
        c.saldo_pendiente_cop
        for t in tarjetas
        for c in db.query(CompraCuotas).filter(
            CompraCuotas.tarjeta_id == t.id,
            CompraCuotas.liquidada == False,  # noqa: E712
            CompraCuotas.eliminado_en.is_(None),
        ).all()
    )

    if cupo_total > 0:
        uso_credito = saldo_cuotas_tc / cupo_total
        if uso_credito < 0.5:
            score += 10
            detalles.append({"criterio": "Uso de crédito", "cumple": True, "peso": 10, "detalle": f"Usando {uso_credito:.0%} del cupo total"})
        else:
            detalles.append({"criterio": "Uso de crédito", "cumple": False, "peso": 10, "detalle": f"Usando {uso_credito:.0%} del cupo (meta: <50%)"})
    else:
        if saldo_cuotas_tc == 0:
            score += 10
            detalles.append({"criterio": "Uso de crédito", "cumple": True, "peso": 10, "detalle": "Sin tarjetas de crédito"})
        else:
            detalles.append({"criterio": "Uso de crédito", "cumple": False, "peso": 10, "detalle": "Cuotas activas sin cupo configurado"})

    # ── 6. Ingreso diversificado (10 pts) ───────────────
    fuentes = len(ingresos_cfg)
    if fuentes >= 2:
        score += 10
        detalles.append({"criterio": "Ingreso diversificado", "cumple": True, "peso": 10, "detalle": f"{fuentes} fuentes de ingreso"})
    elif fuentes == 1:
        score += 5
        detalles.append({"criterio": "Ingreso diversificado", "cumple": False, "peso": 10, "detalle": "Solo 1 fuente (meta: 2+)"})
    else:
        detalles.append({"criterio": "Ingreso diversificado", "cumple": False, "peso": 10, "detalle": "Sin ingresos configurados"})

    # ── 7. Tendencia de gasto (15 pts) ──────────────────
    promedio_3m = _promedio_gasto_flexible(db, user_id=user_id, user_ids=user_ids, meses=3)
    gasto_flex_actual = gasto_mes - gastos_fijos if gasto_mes > gastos_fijos else 0

    if promedio_3m > 0:
        tendencia = gasto_flex_actual / promedio_3m
        if tendencia <= 1.0:
            score += 15
            detalles.append({"criterio": "Tendencia de gasto", "cumple": True, "peso": 15, "detalle": f"Gasto flexible es {tendencia:.0%} del promedio 3 meses"})
        elif tendencia <= 1.2:
            score += 8
            detalles.append({"criterio": "Tendencia de gasto", "cumple": False, "peso": 15, "detalle": f"Gasto flexible subió {tendencia:.0%} vs promedio (tolerable)"})
        else:
            detalles.append({"criterio": "Tendencia de gasto", "cumple": False, "peso": 15, "detalle": f"Gasto flexible subió {tendencia:.0%} vs promedio (meta: ≤100%)"})
    else:
        if gasto_flex_actual == 0:
            score += 15
            detalles.append({"criterio": "Tendencia de gasto", "cumple": True, "peso": 15, "detalle": "Sin gastos flexibles este mes"})
        else:
            detalles.append({"criterio": "Tendencia de gasto", "cumple": False, "peso": 15, "detalle": "Sin historial para comparar"})

    # ── 8. Consistencia de registro (10 pts) ────────────
    registros_mes = _contar_registros_mes(db, mes_actual, user_id, user_ids=user_ids)
    if registros_mes >= 15:
        score += 10
        detalles.append({"criterio": "Consistencia de registro", "cumple": True, "peso": 10, "detalle": f"{registros_mes} registros este mes"})
    elif registros_mes >= 8:
        score += 5
        detalles.append({"criterio": "Consistencia de registro", "cumple": False, "peso": 10, "detalle": f"{registros_mes} registros (meta: 15+)"})
    else:
        detalles.append({"criterio": "Consistencia de registro", "cumple": False, "peso": 10, "detalle": f"{registros_mes} registros (meta: 15+)"})

    return {
        "score": score,
        "max_score": 100,
        "nivel": _nivel_score(score),
        "detalles": detalles,
    }


def _gasto_total_mes(
    db: Session,
    mes: str,
    user_id: int | None,
    *,
    user_ids: list[int] | None = None,
) -> int:
    q = db.query(Movimiento).filter(
        Movimiento.eliminado_en.is_(None),
        Movimiento.fecha_gasto.isnot(None),
    )
    if user_id:
        q = q.filter(Movimiento.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(Movimiento.user_id.in_(user_ids))

    total = 0
    for m in q.all():
        if not m.fecha_gasto or m.fecha_gasto.strftime("%Y-%m") != mes:
            continue
        cat = db.query(Categoria).filter_by(id=m.categoria_id).one_or_none()
        if cat and cat.tipo == "gasto":
            total += m.monto_cop
    return total


def _contar_registros_mes(
    db: Session,
    mes: str,
    user_id: int | None,
    *,
    user_ids: list[int] | None = None,
) -> int:
    """Cuenta movimientos registrados en el mes (no eliminados)."""
    q = db.query(Movimiento).filter(
        Movimiento.eliminado_en.is_(None),
        Movimiento.fecha_gasto.isnot(None),
    )
    if user_id:
        q = q.filter(Movimiento.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(Movimiento.user_id.in_(user_ids))

    count = 0
    for m in q.all():
        if m.fecha_gasto and m.fecha_gasto.strftime("%Y-%m") == mes:
            count += 1
    return count


def _nivel_score(score: int) -> str:
    if score >= 75:
        return "excelente"
    if score >= 50:
        return "bueno"
    if score >= 25:
        return "regular"
    return "critico"
