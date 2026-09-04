from sqlalchemy.orm import Session

from db.models import User
from services.ingresos import (
    crear_ingreso,
    listar_ingresos,
    actualizar_ingreso,
    eliminar_ingreso,
    ingreso_esperado_mes,
    resumen_ingresos,
)


def _user_id(db: Session) -> int:
    return db.query(User).first().id


def test_crear_ingreso_fijo(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    i = crear_ingreso(
        seeded_session,
        user_id=uid,
        nombre="Salario",
        tipo="fijo",
        frecuencia="mensual",
        monto_cop=4_500_000,
        dia_pago_1=30,
    )
    assert i.id is not None
    assert i.tipo == "fijo"
    assert i.frecuencia == "mensual"
    assert i.monto_cop == 4_500_000
    assert i.activo is True


def test_crear_ingreso_quincenal(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    i = crear_ingreso(
        seeded_session,
        user_id=uid,
        nombre="Salario Quincenal",
        tipo="fijo",
        frecuencia="quincenal",
        monto_cop=2_250_000,
        dia_pago_1=15,
        dia_pago_2=30,
    )
    assert i.frecuencia == "quincenal"
    assert i.dia_pago_2 == 30
    assert ingreso_esperado_mes(i) == 4_500_000


def test_crear_ingreso_variable(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    i = crear_ingreso(
        seeded_session,
        user_id=uid,
        nombre="Freelance",
        tipo="variable",
        frecuencia="mensual",
        monto_cop=1_000_000,
    )
    assert i.tipo == "variable"


def test_listar_ingresos(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    crear_ingreso(seeded_session, user_id=uid, nombre="Salario", monto_cop=4_000_000)
    crear_ingreso(seeded_session, user_id=uid, nombre="Freelance", tipo="variable", monto_cop=1_000_000)
    ingresos = listar_ingresos(seeded_session)
    assert len(ingresos) == 2


def test_actualizar_ingreso(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    i = crear_ingreso(seeded_session, user_id=uid, nombre="Salario", monto_cop=4_000_000)
    actualizar_ingreso(seeded_session, i, monto_cop=4_500_000)
    seeded_session.refresh(i)
    assert i.monto_cop == 4_500_000


def test_eliminar_ingreso(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    i = crear_ingreso(seeded_session, user_id=uid, nombre="Salario", monto_cop=4_000_000)
    eliminar_ingreso(seeded_session, i)
    seeded_session.refresh(i)
    assert i.activo is False
    assert len(listar_ingresos(seeded_session, solo_activos=True)) == 0


def test_ingreso_esperado_mes_semanal(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    i = crear_ingreso(seeded_session, user_id=uid, nombre="Domicilios", frecuencia="semanal", monto_cop=200_000)
    assert ingreso_esperado_mes(i) == 800_000


def test_ingreso_esperado_mes_anual(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    i = crear_ingreso(seeded_session, user_id=uid, nombre="Prima", frecuencia="anual", monto_cop=4_500_000)
    assert ingreso_esperado_mes(i) == 375_000


def test_resumen_ingresos(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    crear_ingreso(seeded_session, user_id=uid, nombre="Salario", tipo="fijo", monto_cop=4_000_000)
    crear_ingreso(seeded_session, user_id=uid, nombre="Freelance", tipo="variable", monto_cop=1_000_000)
    resumen = resumen_ingresos(seeded_session, mes="2026-09")
    assert resumen["esperado_fijo"] == 4_000_000
    assert resumen["esperado_variable"] == 1_000_000
    assert resumen["esperado_total"] == 5_000_000
    assert resumen["recibido"] == 0
    assert len(resumen["ingresos"]) == 2
