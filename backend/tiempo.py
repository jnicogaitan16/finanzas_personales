from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TZ_BOGOTA = ZoneInfo("America/Bogota")


def ahora_bogota() -> datetime:
    """Fecha y hora actuales en Bogotá, sin tzinfo (naive)."""
    return datetime.now(TZ_BOGOTA).replace(tzinfo=None)


def a_bogota(valor: datetime | int | float) -> datetime:
    """Convierte un datetime o unix timestamp a hora local de Bogotá (naive)."""
    if isinstance(valor, (int, float)):
        segundos = valor / 1000.0 if valor > 1e12 else float(valor)
        utc = datetime.fromtimestamp(segundos, tz=timezone.utc)
        return utc.astimezone(TZ_BOGOTA).replace(tzinfo=None)
    if valor.tzinfo is None:
        return valor
    return valor.astimezone(TZ_BOGOTA).replace(tzinfo=None)
