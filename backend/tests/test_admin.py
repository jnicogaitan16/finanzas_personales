from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from admin.auth import COOKIE_NAME, clear_all_sessions, login
from config import settings
from db.models import Categoria, Movimiento, User


def _login(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_password", "secreto")
    monkeypatch.setattr(settings, "admin_user", "admin")
    monkeypatch.setattr(settings, "admin_totp_secret", "")
    clear_all_sessions()
    token = login("admin", "secreto")
    assert token is not None
    client.cookies.set(COOKIE_NAME, token)


def _ids(seeded_session: Session) -> tuple[int, int, int]:
    """Retorna (user_id, cat_id_mercado, cat_id_transporte) del seed."""
    user = seeded_session.query(User).filter_by(nombre="Nico").one()
    mercado = seeded_session.query(Categoria).filter_by(nombre="Mercado").one()
    transporte = seeded_session.query(Categoria).filter_by(nombre="Transporte").one()
    return user.id, mercado.id, transporte.id


def test_admin_exige_auth(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_password", "secreto")
    clear_all_sessions()
    assert client.get("/admin/api/movimientos").status_code == 401
    _login(client, monkeypatch)
    ok = client.get("/admin")
    assert ok.status_code == 200
    assert "Finanzas" in ok.text


def test_admin_crud_movimiento(client: TestClient, seeded_session: Session, monkeypatch) -> None:
    _login(client, monkeypatch)
    user_id, cat_mercado, cat_transporte = _ids(seeded_session)

    creado = client.post(
        "/admin/api/movimientos",
        json={
            "user_id": user_id,
            "categoria_id": cat_mercado,
            "monto_cop": 9900,
            "descripcion": "prueba admin",
            "fecha_gasto": "2026-08-31",
        },
    )
    assert creado.status_code == 201
    mov_id = creado.json()["id"]

    patch = client.patch(
        f"/admin/api/movimientos/{mov_id}",
        json={
            "monto_cop": 12000,
            "categoria_id": cat_transporte,
            "descripcion": "uber",
            "fecha_gasto": "2026-08-30",
        },
    )
    assert patch.status_code == 200
    assert patch.json()["monto_cop"] == 12000
    assert patch.json()["categoria"] == "Transporte"
    assert patch.json()["descripcion"] == "uber"
    assert patch.json()["fecha_gasto"] == "2026-08-30"

    put = client.put(
        f"/admin/api/movimientos/{mov_id}",
        json={"descripcion": "didi", "fecha_gasto": "2026-08-29"},
    )
    assert put.status_code == 200
    assert put.json()["descripcion"] == "didi"
    assert put.json()["fecha_gasto"] == "2026-08-29"

    lista = client.get("/admin/api/movimientos")
    assert any(item["id"] == mov_id for item in lista.json())

    borrado = client.delete(f"/admin/api/movimientos/{mov_id}")
    assert borrado.status_code == 200
    # soft delete: el registro sigue en DB pero con eliminado_en
    mov = seeded_session.query(Movimiento).filter_by(id=mov_id).one()
    assert mov.eliminado_en is not None
    # ya no aparece en la lista
    lista2 = client.get("/admin/api/movimientos")
    assert not any(item["id"] == mov_id for item in lista2.json())


def test_admin_no_borra_categoria_en_uso(client: TestClient, seeded_session: Session, monkeypatch) -> None:
    _login(client, monkeypatch)
    user_id, cat_mercado, _ = _ids(seeded_session)
    client.post(
        "/admin/api/movimientos",
        json={"user_id": user_id, "categoria_id": cat_mercado, "monto_cop": 1000},
    )
    res = client.delete(f"/admin/api/categorias/{cat_mercado}")
    assert res.status_code == 409


def test_login_page_renders(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_password", "secreto")
    res = client.get("/admin/login")
    assert res.status_code == 200
    assert "Entrar" in res.text


def test_login_wrong_password(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_password", "secreto")
    monkeypatch.setattr(settings, "admin_totp_secret", "")
    res = client.post(
        "/admin/login",
        data={"username": "admin", "password": "mal"},
        follow_redirects=False,
    )
    assert res.status_code == 401


def test_login_success_sets_cookie(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_password", "secreto")
    monkeypatch.setattr(settings, "admin_user", "admin")
    monkeypatch.setattr(settings, "admin_totp_secret", "")
    clear_all_sessions()
    res = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secreto"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert COOKIE_NAME in res.cookies


def test_logout_clears_session(client: TestClient, monkeypatch) -> None:
    _login(client, monkeypatch)
    assert client.get("/admin").status_code == 200
    client.get("/admin/logout", follow_redirects=False)
    client.cookies.clear()
    assert client.get("/admin/api/movimientos").status_code == 401


def test_totp_required_when_configured(client: TestClient, monkeypatch) -> None:
    import pyotp

    secret = pyotp.random_base32()
    monkeypatch.setattr(settings, "admin_password", "secreto")
    monkeypatch.setattr(settings, "admin_user", "admin")
    monkeypatch.setattr(settings, "admin_totp_secret", secret)
    clear_all_sessions()

    # sin codigo TOTP falla
    res = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secreto"},
        follow_redirects=False,
    )
    assert res.status_code == 401

    # con codigo TOTP valido funciona
    code = pyotp.TOTP(secret).now()
    res = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secreto", "totp_code": code},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert COOKIE_NAME in res.cookies
