"""Utilidades compartidas del backend."""


def format_cop(monto: int) -> str:
    """Formatea un monto en COP: 15300 → '$15.300'"""
    agrupado = f"{monto:,}".replace(",", ".")
    return f"${agrupado}"
