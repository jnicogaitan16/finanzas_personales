import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from admin.auth import COOKIE_NAME, clear_all_sessions, hash_password, login
from db.models import Categoria, Movimiento, User


def _create_test_user(db: Session) -> User:
    """Create a test user with a password for auth tests."""
    user = db.query(User).filter_by(nombre="Nico").one_or_none()
    if user and not user.password_hash:
        user.password_hash = hash_password("secreto")
        db.commit()
    return user


def _login(client: TestClient, seeded_session: Session) -> None:
    user = _create_test_user(seeded_session)
    clear_all_sessions()
    token = login(seeded_session, "Nico", "secreto")
    assert token is not None
    client.cookies.set(COOKIE_NAME, token)


def _ids(seeded_session: Session) -> tuple[int, int, int]:
    user = seeded_session.query(User).filter_by(nombre="Nico").one()
    mercado = seeded_session.query(Categoria).filter_by(nombre="Mercado").one()
    transporte = seeded_session.query(Categoria).filter_by(nombre="Transporte").one()
    return user.id, mercado.id, transporte.id


def test_admin_exige_auth(client: TestClient, seeded_session: Session) -> None:
    clear_all_sessions()
    assert client.get("/admin/api/movimientos").status_code == 401
    _login(client, seeded_session)
    ok = client.get("/admin")
    assert ok.status_code == 200


def test_admin_crud_movimiento(client: TestClient, seeded_session: Session) -> None:
    _login(client, seeded_session)
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

    borrado = client.delete(f"/admin/api/movimientos/{mov_id}")
    assert borrado.status_code == 200
    mov = seeded_session.query(Movimiento).filter_by(id=mov_id).one()
    assert mov.eliminado_en is not None


def test_admin_no_borra_categoria_en_uso(client: TestClient, seeded_session: Session) -> None:
    _login(client, seeded_session)
    user_id, cat_mercado, _ = _ids(seeded_session)
    client.post(
        "/admin/api/movimientos",
        json={"user_id": user_id, "categoria_id": cat_mercado, "monto_cop": 1000},
    )
    res = client.delete(f"/admin/api/categorias/{cat_mercado}")
    assert res.status_code == 409


def test_login_page_renders(client: TestClient) -> None:
    res = client.get("/admin/login")
    assert res.status_code == 200


def test_login_wrong_password(client: TestClient, seeded_session: Session) -> None:
    _create_test_user(seeded_session)
    res = client.post(
        "/admin/login",
        data={"username": "Nico", "password": "mal"},
        follow_redirects=False,
    )
    assert res.status_code == 401


def test_login_success_sets_cookie(client: TestClient, seeded_session: Session) -> None:
    _create_test_user(seeded_session)
    clear_all_sessions()
    res = client.post(
        "/admin/login",
        data={"username": "Nico", "password": "secreto"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert COOKIE_NAME in res.cookies


def test_logout_clears_session(client: TestClient, seeded_session: Session) -> None:
    _login(client, seeded_session)
    assert client.get("/admin").status_code == 200
    client.get("/admin/logout", follow_redirects=False)
    client.cookies.clear()
    assert client.get("/admin/api/movimientos").status_code == 401
