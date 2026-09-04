from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from admin.auth import COOKIE_NAME, clear_all_sessions, hash_password, login
from db.models import User


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_listar_categorias_semilla(client: TestClient, seeded_session: Session) -> None:
    user = seeded_session.query(User).filter_by(nombre="Nico").one()
    user.password_hash = hash_password("secreto")
    seeded_session.commit()
    clear_all_sessions()
    token = login(seeded_session, "Nico", "secreto")
    assert token is not None
    client.cookies.set(COOKIE_NAME, token)
    response = client.get("/admin/api/categorias")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 17
    assert payload[0]["nombre"] == "Mercado"
    assert any(item["nombre"] == "Salario" and item["tipo"] == "ingreso" for item in payload)
