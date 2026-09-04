from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import AuditLog, Movimiento
from tiempo import ahora_bogota


def _movimiento_a_dict(m: Movimiento) -> dict:
    return {
        "user_id": m.user_id,
        "categoria_id": m.categoria_id,
        "monto_cop": m.monto_cop,
        "descripcion": m.descripcion,
        "mensaje_original": m.mensaje_original,
        "fue_audio": m.fue_audio,
        "fecha_gasto": m.fecha_gasto.isoformat() if m.fecha_gasto else None,
    }


def registrar_creacion(
    db: Session,
    movimiento: Movimiento,
    *,
    origen: str = "admin",
) -> None:
    db.add(AuditLog(
        tabla="movimientos",
        registro_id=movimiento.id,
        accion="crear",
        valores_anteriores=None,
        valores_nuevos=_movimiento_a_dict(movimiento),
        origen=origen,
        user_id=movimiento.user_id,
        timestamp=ahora_bogota(),
    ))
    db.commit()


def registrar_edicion(
    db: Session,
    movimiento: Movimiento,
    valores_anteriores: dict,
    *,
    origen: str = "admin",
) -> None:
    db.add(AuditLog(
        tabla="movimientos",
        registro_id=movimiento.id,
        accion="editar",
        valores_anteriores=valores_anteriores,
        valores_nuevos=_movimiento_a_dict(movimiento),
        origen=origen,
        user_id=movimiento.user_id,
        timestamp=ahora_bogota(),
    ))
    db.commit()


def registrar_borrado(
    db: Session,
    movimiento: Movimiento,
    *,
    origen: str = "admin",
) -> None:
    db.add(AuditLog(
        tabla="movimientos",
        registro_id=movimiento.id,
        accion="borrar",
        valores_anteriores=_movimiento_a_dict(movimiento),
        valores_nuevos=None,
        origen=origen,
        user_id=movimiento.user_id,
        timestamp=ahora_bogota(),
    ))
    db.commit()
