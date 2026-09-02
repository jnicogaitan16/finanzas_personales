from __future__ import annotations

from dataclasses import dataclass

from parser.schemas import Extraccion


@dataclass(frozen=True)
class ResultadoRegistro:
    status: str
    mensaje_respuesta: str
    movimiento_id: int | None = None
    extraccion: Extraccion | None = None
