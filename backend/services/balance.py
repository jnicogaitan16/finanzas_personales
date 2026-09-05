from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import CompraCuotas, Deuda, GastoFijo, Movimiento, User
from utils import format_cop


def calcular_balance(db: Session, *, mes: str | None = None, grupo_id: int | None = None) -> dict:
    """Calcula el balance de gastos compartidos entre los 2 usuarios.

    Fuentes:
    1. Gastos fijos compartidos (activos, se aplican cada mes)
    2. Movimientos compartidos del mes seleccionado
    3. Deudas personales activas (tipo='personal')

    Retorna:
    {
        "usuarios": {"1": "Nico", "2": "Day"},
        "detalles": [
            {"concepto": "Energia", "total": 125700, "mitad": 62850, "paga": "Nico", "debe": "Day", "fuente": "fijo"},
            {"concepto": "Carulla compartido", "total": 28000, "mitad": 14000, "paga": "Nico", "debe": "Day", "fuente": "movimiento"},
            {"concepto": "TDC Nico antigua", "total": 120000, "mitad": 120000, "paga": "Nico", "debe": "Day", "fuente": "deuda"},
        ],
        "resumen_por_usuario": {
            "1": {"nombre": "Nico", "pago_total": X, "debe_total": Y},
            "2": {"nombre": "Day", "pago_total": A, "debe_total": B},
        },
        "balance_neto": Z,  # positive = user2 owes user1
        "quien_debe": "Day debe a Nico $129.535",
    }
    """
    q_users = db.query(User).order_by(User.id)
    if grupo_id:
        q_users = q_users.filter(User.grupo_id == grupo_id)
    users = q_users.all()
    if len(users) < 2:
        return {"detalles": [], "balance_neto": 0, "quien_debe": ""}

    user_map = {u.id: u.nombre for u in users}
    user_ids = list(user_map.keys())
    detalles = []

    # 1. Gastos fijos compartidos (solo del grupo)
    fijos = db.query(GastoFijo).filter(
        GastoFijo.es_compartido == True,  # noqa: E712
        GastoFijo.activo == True,  # noqa: E712
        GastoFijo.user_id.in_(user_ids),
    ).all()
    for gf in fijos:
        pct = (gf.porcentaje_compartido or 50) / 100
        mitad = int(gf.monto_cop * pct)
        # The person who PAYS owns the gf. The OTHER person owes them.
        otros = [u for u in users if u.id != gf.user_id]
        if otros:
            detalles.append({
                "concepto": gf.nombre,
                "total": gf.monto_cop,
                "mitad": mitad,
                "paga_id": gf.user_id,
                "paga": user_map.get(gf.user_id, "?"),
                "debe_id": otros[0].id,
                "debe": otros[0].nombre,
                "fuente": "fijo",
                "porcentaje": gf.porcentaje_compartido or 50,
            })

    # 2a. Movimientos compartidos SIN cuotas (solo del grupo)
    q_simple = db.query(Movimiento).filter(
        Movimiento.es_compartido == True,  # noqa: E712
        Movimiento.eliminado_en.is_(None),
        Movimiento.compra_cuotas_id.is_(None),
        Movimiento.user_id.in_(user_ids),
    )
    if mes:
        q_simple = q_simple.filter(func.to_char(Movimiento.fecha_gasto, 'YYYY-MM') == mes)
    for m in q_simple.all():
        pct = (m.porcentaje_compartido or 50) / 100
        mitad = int(m.monto_cop * pct)
        otros = [u for u in users if u.id != m.user_id]
        if otros:
            detalles.append({
                "concepto": m.descripcion or "Gasto compartido",
                "valor_compra": None,
                "total": m.monto_cop,
                "mitad": mitad,
                "paga_id": m.user_id,
                "paga": user_map.get(m.user_id, "?"),
                "debe_id": otros[0].id,
                "debe": otros[0].nombre,
                "fuente": "movimiento",
                "porcentaje": m.porcentaje_compartido or 50,
                "fecha": m.fecha_gasto.isoformat() if m.fecha_gasto else None,
            })

    # 2b. Cuotas compartidas activas (aparecen cada mes hasta liquidarse)
    # Una compra a cuotas compartida genera deuda mensual desde el mes de compra
    # hasta que se liquide (cuotas_pagadas >= num_cuotas)
    cuotas_compartidas = (
        db.query(CompraCuotas)
        .join(Movimiento, Movimiento.compra_cuotas_id == CompraCuotas.id)
        .filter(
            Movimiento.es_compartido == True,  # noqa: E712
            Movimiento.eliminado_en.is_(None),
            CompraCuotas.eliminado_en.is_(None),
            CompraCuotas.liquidada == False,  # noqa: E712
            CompraCuotas.user_id.in_(user_ids),
        )
        .all()
    )
    # Deduplicar por id (el join puede dar duplicados)
    seen_cuota_ids: set[int] = set()
    for cc in cuotas_compartidas:
        if cc.id in seen_cuota_ids:
            continue
        seen_cuota_ids.add(cc.id)
        # Verificar que el mes seleccionado cae dentro del rango de cuotas
        if mes and cc.fecha_compra:
            from datetime import date

            compra_y = cc.fecha_compra.year
            compra_m = cc.fecha_compra.month
            try:
                sel_y, sel_m = int(mes[:4]), int(mes[5:7])
            except (ValueError, IndexError):
                continue
            # Meses transcurridos desde la compra
            meses_desde = (sel_y - compra_y) * 12 + (sel_m - compra_m)
            if meses_desde < 0 or meses_desde >= cc.num_cuotas:
                continue
            cuota_num = meses_desde + 1  # 1-indexed
        else:
            cuota_num = cc.cuotas_pagadas + 1

        # Buscar el movimiento vinculado para obtener user_id y porcentaje
        mov = (
            db.query(Movimiento)
            .filter(
                Movimiento.compra_cuotas_id == cc.id,
                Movimiento.es_compartido == True,  # noqa: E712
                Movimiento.eliminado_en.is_(None),
            )
            .first()
        )
        if not mov:
            continue
        pct = (mov.porcentaje_compartido or 50) / 100
        mitad = int(cc.valor_cuota_cop * pct)
        otros = [u for u in users if u.id != mov.user_id]
        if otros:
            detalles.append({
                "concepto": f"{cc.establecimiento} ({cuota_num}/{cc.num_cuotas})",
                "valor_compra": cc.valor_total_cop,
                "total": cc.valor_cuota_cop,
                "mitad": mitad,
                "paga_id": mov.user_id,
                "paga": user_map.get(mov.user_id, "?"),
                "debe_id": otros[0].id,
                "debe": otros[0].nombre,
                "fuente": "cuota",
                "porcentaje": mov.porcentaje_compartido or 50,
                "fecha": cc.fecha_compra.isoformat() if cc.fecha_compra else None,
            })

    # 2c. Movimientos compartidos CON cuota de 1 sola cuota (ya liquidadas)
    q_tc1 = db.query(Movimiento).filter(
        Movimiento.es_compartido == True,  # noqa: E712
        Movimiento.eliminado_en.is_(None),
        Movimiento.compra_cuotas_id.isnot(None),
        Movimiento.user_id.in_(user_ids),
    )
    if mes:
        q_tc1 = q_tc1.filter(func.to_char(Movimiento.fecha_gasto, 'YYYY-MM') == mes)
    for m in q_tc1.all():
        cc = db.query(CompraCuotas).filter_by(id=m.compra_cuotas_id).one_or_none()
        if not cc or cc.num_cuotas > 1:
            continue  # Multi-cuota ya se maneja arriba
        if cc.id in seen_cuota_ids:
            continue
        pct = (m.porcentaje_compartido or 50) / 100
        mitad = int(m.monto_cop * pct)
        otros = [u for u in users if u.id != m.user_id]
        if otros:
            detalles.append({
                "concepto": m.descripcion or cc.establecimiento,
                "valor_compra": None,
                "total": m.monto_cop,
                "mitad": mitad,
                "paga_id": m.user_id,
                "paga": user_map.get(m.user_id, "?"),
                "debe_id": otros[0].id,
                "debe": otros[0].nombre,
                "fuente": "movimiento",
                "porcentaje": m.porcentaje_compartido or 50,
                "fecha": m.fecha_gasto.isoformat() if m.fecha_gasto else None,
            })

    # 3. Deudas personales activas
    deudas = db.query(Deuda).filter(Deuda.activa == True, Deuda.user_id.in_(user_ids)).all()  # noqa: E712
    for d in deudas:
        # For personal debts, the user_id is who OWES, acreedor is who they owe TO
        # But in our context, we'll treat it as: user_id registered the debt,
        # and the "other" user owes them the saldo
        otros = [u for u in users if u.id != d.user_id]
        if otros and d.saldo_cop > 0:
            detalles.append({
                "concepto": d.nombre,
                "total": d.saldo_cop,
                "mitad": d.saldo_cop,  # debts are full amount, not split
                "paga_id": d.user_id,
                "paga": user_map.get(d.user_id, "?"),
                "debe_id": otros[0].id,
                "debe": otros[0].nombre,
                "fuente": "deuda",
                "porcentaje": 100,
            })

    # Calculate totals per user
    resumen = {}
    for u in users:
        pago = sum(d["mitad"] for d in detalles if d["paga_id"] == u.id)
        debe = sum(d["mitad"] for d in detalles if d["debe_id"] == u.id)
        resumen[str(u.id)] = {"nombre": u.nombre, "pago_total": pago, "debe_total": debe}

    # Net balance between the two users
    if len(users) >= 2:
        u1, u2 = users[0], users[1]
        # What u2 owes u1 minus what u1 owes u2
        balance = resumen[str(u1.id)]["pago_total"] - resumen[str(u2.id)]["pago_total"]
        if balance > 0:
            quien_debe = f"{u2.nombre} debe a {u1.nombre} {format_cop(balance)}"
        elif balance < 0:
            quien_debe = f"{u1.nombre} debe a {u2.nombre} {format_cop(abs(balance))}"
        else:
            quien_debe = "Estan a mano"
    else:
        balance = 0
        quien_debe = ""

    return {
        "usuarios": user_map,
        "detalles": detalles,
        "resumen_por_usuario": resumen,
        "balance_neto": balance,
        "quien_debe": quien_debe,
    }
