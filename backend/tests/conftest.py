import os
os.environ["TESTING"] = "1"

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from config import settings
from db.models import Base, Categoria, User
from db.seed import CATEGORIAS_INICIALES
from db.session import get_db
from main import app

TEST_DATABASE_URL = settings.database_url


@pytest.fixture(autouse=True)
def _desactivar_apis_externas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    session.begin_nested()

    # Limpiar tablas dentro del savepoint (orden por FK)
    session.execute(text("DELETE FROM audit_log"))
    session.execute(text("DELETE FROM gastos_fijos"))
    session.execute(text("DELETE FROM deudas"))
    session.execute(text("DELETE FROM presupuestos"))
    session.execute(text("DELETE FROM movimientos"))
    session.execute(text("DELETE FROM compras_cuotas"))
    session.execute(text("DELETE FROM tarjetas_credito"))
    session.execute(text("DELETE FROM ingresos_recurrentes"))
    session.execute(text("DELETE FROM categorias"))
    session.execute(text("DELETE FROM users"))
    session.execute(text("DELETE FROM grupos"))
    session.flush()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):  # noqa: ARG001
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


@pytest.fixture()
def seeded_session(db_session: Session) -> Session:
    for item in CATEGORIAS_INICIALES:
        db_session.add(Categoria(
            nombre=item["nombre"],
            tipo=item["tipo"],
            es_fijo=item.get("es_fijo", False),
        ))
    db_session.add(User(nombre="Nico"))
    db_session.commit()
    return db_session


@pytest.fixture()
def client(seeded_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield seeded_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
