import pytest
from fastapi.testclient import TestClient

from admin.auth import COOKIE_NAME, clear_all_sessions, login
from config import settings


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_listar_categorias_semilla(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_password", "secreto")
    monkeypatch.setattr(settings, "admin_user", "admin")
    monkeypatch.setattr(settings, "admin_totp_secret", "")
    clear_all_sessions()
    token = login("admin", "secreto")
    assert token is not None
    client.cookies.set(COOKIE_NAME, token)
    response = client.get("/admin/api/categorias")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 17
    assert payload[0]["nombre"] == "Mercado"
    assert any(item["nombre"] == "Salario" and item["tipo"] == "ingreso" for item in payload)
