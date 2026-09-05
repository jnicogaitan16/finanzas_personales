from __future__ import annotations

from calendar import monthrange
from datetime import date

from sqlalchemy.orm import Session, joinedload

from db.models import Categoria, IngresoRecurrente, Movimiento, User
from tiempo import ahora_bogota


def crear_ingreso(
    db: Session,
    *,
    user_id: int,
    nombre: str,
    tipo: str = "fijo",
    frecuencia: str = "mensual",
    monto_cop: int = 0,
    dia_pago_1: int | None = None,
    dia_pago_2: int | None = None,
) -> IngresoRecurrente:
    if db.query(User).filter_by(id=user_id).one_or_none() is None:
        raise ValueError("Usuario no existe")
    if tipo not in ("fijo", "variable"):
        raise ValueError("Tipo debe ser 'fijo' o 'variable'")
    if frecuencia not in ("mensual", "quincenal", "semanal", "anual"):
        raise ValueError("Frecuencia no valida")
    if monto_cop <= 0:
        raise ValueError("El monto debe ser mayor a 0")

    ingreso = IngresoRecurrente(
        user_id=user_id,
        nombre=nombre.strip(),
        tipo=tipo,
        frecuencia=frecuencia,
        monto_cop=monto_cop,
        dia_pago_1=dia_pago_1,
        dia_pago_2=dia_pago_2,
    )
    db.add(ingreso)
    db.commit()
    db.refresh(ingreso)
    return ingreso


def listar_ingresos(
    db: Session,
    *,
    user_id: int | None = None,
    user_ids: list[int] | None = None,
    solo_activos: bool = True,
) -> list[IngresoRecurrente]:
    q = db.query(IngresoRecurrente).options(joinedload(IngresoRecurrente.user))
    if user_id:
        q = q.filter(IngresoRecurrente.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(IngresoRecurrente.user_id.in_(user_ids))
    if solo_activos:
        q = q.filter(IngresoRecurrente.activo == True)  # noqa: E712
    return q.order_by(IngresoRecurrente.nombre).all()


def obtener_ingreso(db: Session, ingreso_id: int) -> IngresoRecurrente | None:
    return (
        db.query(IngresoRecurrente)
        .options(joinedload(IngresoRecurrente.user))
        .filter(IngresoRecurrente.id == ingreso_id)
        .one_or_none()
    )


def actualizar_ingreso(
    db: Session,
    ingreso: IngresoRecurrente,
    *,
    nombre: str | None = None,
    tipo: str | None = None,
    frecuencia: str | None = None,
    monto_cop: int | None = None,
    dia_pago_1: int | None = None,
    dia_pago_2: int | None = None,
    activo: bool | None = None,
) -> IngresoRecurrente:
    if nombre is not None:
        ingreso.nombre = nombre.strip()
    if tipo is not None:
        if tipo not in ("fijo", "variable"):
            raise ValueError("Tipo debe ser 'fijo' o 'variable'")
        ingreso.tipo = tipo
    if frecuencia is not None:
        if frecuencia not in ("mensual", "quincenal", "semanal", "anual"):
            raise ValueError("Frecuencia no valida")
        ingreso.frecuencia = frecuencia
    if monto_cop is not None:
        if monto_cop <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        ingreso.monto_cop = monto_cop
    if dia_pago_1 is not None:
        ingreso.dia_pago_1 = dia_pago_1
    if dia_pago_2 is not None:
        ingreso.dia_pago_2 = dia_pago_2
    if activo is not None:
        ingreso.activo = activo
    db.commit()
    db.refresh(ingreso)
    return ingreso


def eliminar_ingreso(db: Session, ingreso: IngresoRecurrente) -> None:
    ingreso.activo = False
    db.commit()


def serializar_ingreso(i: IngresoRecurrente) -> dict:
    return {
        "id": i.id,
        "user_id": i.user_id,
        "usuario": i.user.nombre if i.user else None,
        "nombre": i.nombre,
        "tipo": i.tipo,
        "frecuencia": i.frecuencia,
        "monto_cop": i.monto_cop,
        "dia_pago_1": i.dia_pago_1,
        "dia_pago_2": i.dia_pago_2,
        "activo": i.activo,
    }


def ingreso_esperado_mes(i: IngresoRecurrente) -> int:
    """Calcula el ingreso esperado mensual de un ingreso recurrente."""
    if i.frecuencia == "quincenal":
        return i.monto_cop * 2
    if i.frecuencia == "semanal":
        return i.monto_cop * 4
    if i.frecuencia == "anual":
        return i.monto_cop // 12
    return i.monto_cop  # mensual


def resumen_ingresos(
    db: Session,
    *,
    mes: str,
    user_id: int | None = None,
    user_ids: list[int] | None = None,
) -> dict:
    """Resumen de ingresos esperados vs recibidos para un mes.

    Args:
        mes: formato "YYYY-MM"
    """
    ingresos_cfg = listar_ingresos(db, user_id=user_id, user_ids=user_ids, solo_activos=True)

    esperado_fijo = 0
    esperado_variable = 0
    for i in ingresos_cfg:
        monto_mes = ingreso_esperado_mes(i)
        if i.tipo == "fijo":
            esperado_fijo += monto_mes
        else:
            esperado_variable += monto_mes

    # Calcular recibido real del mes (movimientos tipo ingreso)
    q = (
        db.query(Movimiento)
        .join(User, Movimiento.user_id == User.id)
        .filter(
            Movimiento.eliminado_en.is_(None),
            Movimiento.fecha_gasto.isnot(None),
        )
    )
    if user_id:
        q = q.filter(Movimiento.user_id == user_id)
    elif user_ids is not None:
        q = q.filter(Movimiento.user_id.in_(user_ids))

    recibido = 0
    from db.models import Categoria
    for mov in q.all():
        if mov.fecha_gasto and mov.fecha_gasto.strftime("%Y-%m") == mes:
            cat = db.query(Categoria).filter_by(id=mov.categoria_id).one_or_none()
            if cat and cat.tipo == "ingreso":
                recibido += mov.monto_cop

    return {
        "mes": mes,
        "esperado_fijo": esperado_fijo,
        "esperado_variable": esperado_variable,
        "esperado_total": esperado_fijo + esperado_variable,
        "recibido": recibido,
        "diferencia": recibido - (esperado_fijo + esperado_variable),
        "ingresos": [serializar_ingreso(i) for i in ingresos_cfg],
    }


# ── Auto-registro de ingresos fijos ─────────────────────────────────


def _marca_ingreso(ingreso_id: int, mes: str) -> str:
    """Genera un identificador único para evitar duplicados."""
    return f"ingreso_fijo:{ingreso_id}:{mes}"


def sincronizar_ingresos_fijos(
    db: Session,
    *,
    mes: str | None = None,
) -> int:
    """Crea Movimientos para ingresos fijos que no se han registrado en el mes.

    Para cada IngresoRecurrente tipo='fijo' activo, verifica si ya existe
    un Movimiento con marca_dedup marcado. Si no, lo crea.

    Si es quincenal, crea 2 movimientos (dia_pago_1 y dia_pago_2).

    Returns: cantidad de movimientos creados.
    """
    if not mes:
        mes = ahora_bogota().strftime("%Y-%m")

    year, month = int(mes[:4]), int(mes[5:7])
    max_dia = monthrange(year, month)[1]

    ingresos_fijos = (
        db.query(IngresoRecurrente)
        .filter(
            IngresoRecurrente.tipo == "fijo",
            IngresoRecurrente.activo == True,  # noqa: E712
        )
        .all()
    )

    cat_salario = db.query(Categoria).filter_by(nombre="Salario").one_or_none()
    cat_id = cat_salario.id if cat_salario else None

    creados = 0
    for ing in ingresos_fijos:
        if ing.frecuencia == "quincenal":
            pagos = []
            if ing.dia_pago_1:
                pagos.append((ing.dia_pago_1, f"{ing.nombre} (1ra quincena)"))
            if ing.dia_pago_2:
                pagos.append((ing.dia_pago_2, f"{ing.nombre} (2da quincena)"))
            if not pagos:
                pagos = [(15, f"{ing.nombre} (1ra quincena)"), (max_dia, f"{ing.nombre} (2da quincena)")]
        else:
            dia = min(ing.dia_pago_1 or max_dia, max_dia)
            pagos = [(dia, ing.nombre)]

        for dia_pago, descripcion in pagos:
            marca = _marca_ingreso(ing.id, f"{mes}-{dia_pago}")

            # Verificar si ya existe
            existe = (
                db.query(Movimiento)
                .filter(
                    Movimiento.marca_dedup == marca,
                    Movimiento.eliminado_en.is_(None),
                )
                .one_or_none()
            )
            if existe:
                continue

            dia_real = min(dia_pago, max_dia)
            mov = Movimiento(
                user_id=ing.user_id,
                categoria_id=cat_id,
                monto_cop=ing.monto_cop,
                descripcion=descripcion,
                marca_dedup=marca,
                fecha_registro=ahora_bogota(),
                fecha_gasto=date(year, month, dia_real),
            )
            db.add(mov)
            creados += 1

    if creados:
        db.commit()
    return creados
