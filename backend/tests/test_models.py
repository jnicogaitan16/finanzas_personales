from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import Categoria, Movimiento, Presupuesto, User


def test_crear_movimiento_completo(seeded_session: Session) -> None:
    user = seeded_session.query(User).one()
    categoria = seeded_session.query(Categoria).filter_by(nombre="Mercado").one()

    movimiento = Movimiento(
        user_id=user.id,
        categoria_id=categoria.id,
        monto_cop=15300,
        descripcion="almuerzo",
        fecha_gasto=date(2026, 8, 31),
    )
    seeded_session.add(movimiento)
    seeded_session.commit()

    guardado = seeded_session.query(Movimiento).one()
    assert guardado.monto_cop == 15300
    assert guardado.user.nombre == "Nico"
    assert guardado.categoria is not None
    assert guardado.categoria.nombre == "Mercado"
    assert guardado.descripcion == "almuerzo"
    assert guardado.fecha_registro is not None


def test_movimiento_sin_categoria_es_valido(seeded_session: Session) -> None:
    user = seeded_session.query(User).one()
    seeded_session.add(
        Movimiento(
            user_id=user.id,
            categoria_id=None,
            monto_cop=5000,
            descripcion="gasté 5 mil no sé en qué",
        )
    )
    seeded_session.commit()
    assert seeded_session.query(Movimiento).count() == 1


def test_nombre_usuario_unico(seeded_session: Session) -> None:
    seeded_session.add(User(nombre="Nico"))
    with pytest.raises(IntegrityError):
        seeded_session.commit()


def test_categoria_nombre_unico(seeded_session: Session) -> None:
    seeded_session.add(Categoria(nombre="Mercado", tipo="gasto"))
    with pytest.raises(IntegrityError):
        seeded_session.commit()


def test_categoria_tipo_invalido(seeded_session: Session) -> None:
    seeded_session.add(Categoria(nombre="Inventada", tipo="transferencia"))
    with pytest.raises(IntegrityError):
        seeded_session.commit()


def test_movimiento_exige_usuario(seeded_session: Session) -> None:
    seeded_session.add(
        Movimiento(
            user_id=None,  # type: ignore[arg-type]
            monto_cop=1000,
            descripcion="sin usuario",
        )
    )
    with pytest.raises(IntegrityError):
        seeded_session.commit()


def test_fk_usuario_inexistente(seeded_session: Session) -> None:
    seeded_session.add(
        Movimiento(
            user_id=999,
            monto_cop=1000,
            descripcion="usuario fantasma",
        )
    )
    with pytest.raises(IntegrityError):
        seeded_session.commit()


def test_presupuesto_unico_por_usuario_categoria_mes(seeded_session: Session) -> None:
    user = seeded_session.query(User).one()
    categoria = seeded_session.query(Categoria).filter_by(nombre="Mercado").one()
    seeded_session.add(
        Presupuesto(
            user_id=user.id,
            categoria_id=categoria.id,
            monto_limite_cop=400_000,
            mes_vigente="2026-08",
        )
    )
    seeded_session.commit()

    seeded_session.add(
        Presupuesto(
            user_id=user.id,
            categoria_id=categoria.id,
            monto_limite_cop=500_000,
            mes_vigente="2026-08",
        )
    )
    with pytest.raises(IntegrityError):
        seeded_session.commit()


def test_seed_incluye_gastos_e_ingreso(seeded_session: Session) -> None:
    cats = seeded_session.query(Categoria).all()
    nombres = {c.nombre for c in cats}
    assert "Mercado" in nombres
    assert "Hogar" in nombres
    assert "Salario" in nombres
    assert "Freelance" in nombres
    assert len(nombres) == 17
    ingresos = [c for c in cats if c.tipo == "ingreso"]
    assert len(ingresos) == 2
