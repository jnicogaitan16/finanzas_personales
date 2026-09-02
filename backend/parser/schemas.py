from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Extraccion:
    monto_cop: int | None
    categoria: str | None
    descripcion: str | None
    fecha_gasto: date | None
    tipo: str
    confianza: float
    necesita_aclaracion: bool
    compartido: bool = False

    @property
    def es_valida(self) -> bool:
        return self.monto_cop is not None and self.monto_cop > 0 and not self.necesita_aclaracion
