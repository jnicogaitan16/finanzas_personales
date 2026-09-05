from datetime import date

from sqlalchemy.orm import Session

from db.models import TarjetaCredito, User
from services.tarjetas import (
    calcular_fecha_primera_cuota,
    crear_tarjeta,
    listar_tarjetas,
    actualizar_tarjeta,
    eliminar_tarjeta,
    proyectar_cuotas_por_mes,
)
from services.cuotas import crear_compra


def _user_id(db: Session) -> int:
    return db.query(User).first().id


def test_crear_tarjeta(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    t = crear_tarjeta(
        seeded_session,
        user_id=uid,
        banco="Bancolombia",
        nombre="Visa Gold",
        fecha_corte=8,
        fecha_pago=25,
        ultimos_4="1234",
        tasa_ea=28.5,
        cupo_total_cop=5_000_000,
    )
    assert t.id is not None
    assert t.banco == "Bancolombia"
    assert t.nombre == "Visa Gold"
    assert t.ultimos_4 == "1234"
    assert t.fecha_corte == 8
    assert t.fecha_pago == 25
    assert t.activa is True


def test_listar_tarjetas(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    crear_tarjeta(seeded_session, user_id=uid, banco="Nu", nombre="Nu", fecha_corte=15, fecha_pago=5)
    crear_tarjeta(seeded_session, user_id=uid, banco="BBVA", nombre="BBVA", fecha_corte=10, fecha_pago=28)
    tarjetas = listar_tarjetas(seeded_session)
    assert len(tarjetas) == 2


def test_actualizar_tarjeta(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    t = crear_tarjeta(seeded_session, user_id=uid, banco="Nu", nombre="Nu", fecha_corte=15, fecha_pago=5)
    actualizar_tarjeta(seeded_session, t, banco="Nu Colombia", tasa_ea=24.0)
    seeded_session.refresh(t)
    assert t.banco == "Nu Colombia"
    assert t.tasa_ea == 24.0


def test_eliminar_tarjeta(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    t = crear_tarjeta(seeded_session, user_id=uid, banco="Nu", nombre="Nu", fecha_corte=15, fecha_pago=5)
    eliminar_tarjeta(seeded_session, t)
    seeded_session.refresh(t)
    assert t.activa is False
    assert len(listar_tarjetas(seeded_session, solo_activas=True)) == 0


def test_fecha_primera_cuota_antes_del_corte() -> None:
    fecha = calcular_fecha_primera_cuota(date(2026, 9, 3), fecha_corte=8, fecha_pago=25)
    assert fecha == date(2026, 9, 25)


def test_fecha_primera_cuota_despues_del_corte() -> None:
    fecha = calcular_fecha_primera_cuota(date(2026, 9, 10), fecha_corte=8, fecha_pago=25)
    assert fecha == date(2026, 10, 25)


def test_fecha_primera_cuota_diciembre() -> None:
    fecha = calcular_fecha_primera_cuota(date(2026, 12, 20), fecha_corte=15, fecha_pago=5)
    assert fecha == date(2027, 1, 5)


def test_crear_compra_con_tarjeta(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    t = crear_tarjeta(
        seeded_session, user_id=uid, banco="Nu", nombre="Nu Card",
        fecha_corte=8, fecha_pago=25, tasa_ea=28.0,
    )
    compra = crear_compra(
        seeded_session,
        user_id=uid,
        fecha_compra=date(2026, 9, 3),
        establecimiento="Exito",
        valor_total_cop=1_000_000,
        num_cuotas=10,
        tarjeta_id=t.id,
    )
    assert compra.tarjeta_id == t.id
    assert compra.tasa_ea == 28.0
    assert compra.fecha_primera_cuota == date(2026, 9, 25)
    assert compra.valor_cuota_cop == 100_000


def test_proyeccion_cuotas(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    t = crear_tarjeta(
        seeded_session, user_id=uid, banco="Nu", nombre="Nu",
        fecha_corte=8, fecha_pago=25,
    )
    crear_compra(
        seeded_session,
        user_id=uid,
        fecha_compra=date(2026, 9, 3),
        establecimiento="Compra A",
        valor_total_cop=300_000,
        num_cuotas=3,
        tarjeta_id=t.id,
    )
    proy = proyectar_cuotas_por_mes(seeded_session, tarjeta_id=t.id, meses=6)
    assert len(proy) > 0
    first_month = list(proy.values())[0]
    assert first_month["total"] == 100_000
    assert len(first_month["compras"]) == 1
