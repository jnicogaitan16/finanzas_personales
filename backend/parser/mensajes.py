from __future__ import annotations

from parser.schemas import Extraccion


def format_cop(monto: int) -> str:
    agrupado = f"{monto:,}".replace(",", ".")
    return f"${agrupado}"


def mensaje_confirmacion(extraccion: Extraccion) -> str:
    monto = format_cop(extraccion.monto_cop or 0)
    categoria = extraccion.categoria or "Otros"
    compartido = " (compartido)" if extraccion.compartido else ""
    if extraccion.tipo == "ingreso":
        return f"✅ Ingreso registrado: {monto} en {categoria}"
    return f"✅ Registrado: {monto} en {categoria}{compartido}"


def mensaje_aclaracion() -> str:
    return (
        "No pude leer el monto. Prueba algo como: "
        '"gasté 15.300 en almuerzo" o "15 mil en uber".'
    )
