from datetime import date

from sqlalchemy.orm import Session

from db.models import Categoria, Movimiento, User
from services.inteligencia import flujo_de_caja, obtener_alertas, salud_financiera
from services.ingresos import crear_ingreso
from services.gastos_fijos import crear_gasto_fijo
from tiempo import ahora_bogota


def _user_id(db: Session) -> int:
    return db.query(User).first().id


def _cat_id(db: Session, nombre: str) -> int:
    cat = db.query(Categoria).filter_by(nombre=nombre).one_or_none()
    assert cat is not None, f"Categoria {nombre!r} no encontrada"
    return cat.id


def test_flujo_caja_basico(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    crear_ingreso(seeded_session, user_id=uid, nombre="Salario", monto_cop=4_000_000)
    crear_gasto_fijo(
        seeded_session, user_id=uid, nombre="Arriendo",
        monto_cop=1_500_000, categoria_id=_cat_id(seeded_session, "Hogar"),
    )

    flujo = flujo_de_caja(seeded_session)
    assert flujo["ingresos_esperados"] == 4_000_000
    assert flujo["gastos_fijos"] == 1_500_000
    assert flujo["disponible_estimado"] <= 4_000_000


def test_flujo_caja_sin_datos(seeded_session: Session) -> None:
    flujo = flujo_de_caja(seeded_session)
    assert flujo["ingresos_esperados"] == 0
    assert flujo["disponible_estimado"] == 0


def test_alertas_vacia_sin_config(seeded_session: Session) -> None:
    alertas = obtener_alertas(seeded_session)
    assert isinstance(alertas, list)


def test_salud_financiera_sin_datos(seeded_session: Session) -> None:
    salud = salud_financiera(seeded_session)
    assert salud["score"] >= 0
    assert salud["max_score"] == 100
    assert salud["nivel"] in ("excelente", "bueno", "regular", "critico")
    assert len(salud["detalles"]) == 4


def test_salud_financiera_con_ingresos(seeded_session: Session) -> None:
    uid = _user_id(seeded_session)
    crear_ingreso(seeded_session, user_id=uid, nombre="Salario", monto_cop=4_000_000)
    salud = salud_financiera(seeded_session)
    # Sin gastos y con ingresos → debería tener buen score
    assert salud["score"] >= 50


def test_salud_retorna_detalles_criterios(seeded_session: Session) -> None:
    salud = salud_financiera(seeded_session)
    criterios = [d["criterio"] for d in salud["detalles"]]
    assert "Gastos controlados" in criterios
    assert "Capacidad de ahorro" in criterios
    assert "Deuda saludable" in criterios
    assert "Presupuestos" in criterios
