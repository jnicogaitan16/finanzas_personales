from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from admin.auth import (
    COOKIE_NAME,
    create_session_for_user,
    get_session,
    get_visible_user_ids,
    hash_password,
    login,
    logout,
    require_admin,
)

limiter = Limiter(key_func=get_remote_address)
from config import settings
from db.models import Categoria, CompraCuotas, Deuda, GastoFijo, MetaAhorro, Presupuesto, User
from db.session import get_db
from services import admin as svc
from services import balance as svc_balance
from services import cuotas as svc_cuotas
from services import ingresos as svc_ingresos
from services import inteligencia as svc_intel
from services import tarjetas as svc_tarjetas
from services import gastos_fijos as svc_gf
from services import metas_ahorro as svc_metas
from services import presupuesto as svc_ppto

router = APIRouter(prefix="/admin", tags=["admin"])
PAGE = Path(__file__).parent / "index.html"
LOGIN_PAGE = Path(__file__).parent / "login.html"


def _filter_user_id(session: dict, db: Session, user_id: int | None) -> int | None:
    """Retorna el user_id a filtrar, validando que sea visible.
    Retorna None SOLO cuando es modo hogar (debe usarse con _visible_ids)."""
    visible = get_visible_user_ids(session, db)
    if user_id is not None:
        if user_id not in visible:
            return -1
        return user_id
    if len(visible) == 1:
        return visible[0]
    return None  # hogar — el caller DEBE usar _visible_ids para filtrar


def _visible_ids(session: dict, db: Session) -> list[int]:
    return get_visible_user_ids(session, db)


def _safe_user_filter(session: dict, db: Session, user_id: int | None) -> tuple[int | None, list[int]]:
    """Retorna (uid, visible_ids). Si uid es None, usar visible_ids para filtrar."""
    uid = _filter_user_id(session, db, user_id)
    visible = _visible_ids(session, db)
    return uid, visible


class MovimientoIn(BaseModel):
    user_id: int
    categoria_id: int | None = None
    monto_cop: int
    descripcion: str | None = None
    fecha_gasto: date | None = None
    medio_pago: str | None = None
    es_compartido: bool = False
    porcentaje_compartido: int | None = None


class MovimientoPatch(BaseModel):
    user_id: int | None = None
    categoria_id: int | None = None
    limpiar_categoria: bool = False
    monto_cop: int | None = None
    descripcion: str | None = None
    fecha_gasto: date | None = None
    medio_pago: str | None = None
    es_compartido: bool | None = None
    porcentaje_compartido: int | None = None


class CategoriaIn(BaseModel):
    nombre: str
    tipo: str = "gasto"


class UsuarioIn(BaseModel):
    nombre: str
    email: str | None = None


class PresupuestoIn(BaseModel):
    user_id: int
    categoria_id: int
    monto_limite_cop: int
    mes_vigente: str


class GastoFijoIn(BaseModel):
    user_id: int
    categoria_id: int
    nombre: str
    monto_cop: int
    es_compartido: bool = False
    porcentaje_compartido: int | None = None
    dia_esperado: int | None = None


class GastoFijoPatch(BaseModel):
    nombre: str | None = None
    monto_cop: int | None = None
    categoria_id: int | None = None
    es_compartido: bool | None = None
    porcentaje_compartido: int | None = None
    activo: bool | None = None
    dia_esperado: int | None = None


class CompraIn(BaseModel):
    user_id: int
    fecha_compra: date
    establecimiento: str
    valor_total_cop: int
    num_cuotas: int
    tarjeta_id: int | None = None
    tasa_ea: float | None = None
    descripcion: str | None = None
    numero_transaccion: str | None = None
    es_compartido: bool = False
    movimiento_id: int | None = None


class CompraPatch(BaseModel):
    establecimiento: str | None = None
    fecha_compra: date | None = None
    valor_total_cop: int | None = None
    num_cuotas: int | None = None
    cuotas_pagadas: int | None = None
    valor_cuota_cop: int | None = None
    valor_intereses_cop: int | None = None
    tasa_ea: float | None = None
    numero_transaccion: str | None = None
    descripcion: str | None = None
    es_compartido: bool | None = None


class DeudaIn(BaseModel):
    user_id: int
    nombre: str
    tipo: str = "personal"
    acreedor: str | None = None
    monto_original_cop: int
    saldo_cop: int
    cuota_mensual_cop: int | None = None
    tasa_ea: float | None = None
    notas: str | None = None


@router.get("/login", response_class=HTMLResponse, response_model=None)
def login_page(request: Request) -> HTMLResponse | RedirectResponse:
    token = request.cookies.get(COOKIE_NAME)
    if get_session(token):
        return RedirectResponse("/admin", status_code=302)
    html = LOGIN_PAGE.read_text(encoding="utf-8")
    return HTMLResponse(html.replace("{error}", "").replace("{totp_field}", ""))


@router.post("/login", response_model=None)
@limiter.limit("5/minute")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    client_ip = request.client.host if request.client else ""
    token = login(db, username, password, client_ip=client_ip)
    if token is None:
        html = LOGIN_PAGE.read_text(encoding="utf-8")
        return HTMLResponse(
            html.replace("{error}", "Usuario o contrasena incorrectos").replace("{totp_field}", ""),
            status_code=401,
        )
    response = RedirectResponse("/admin", status_code=302)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="strict",
        path="/",
        max_age=86400,
    )
    return response


@router.get("/logout")
def logout_endpoint(request: Request) -> RedirectResponse:
    token = request.cookies.get(COOKIE_NAME)
    logout(token)
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


# ── Registro y Grupos ────────────────────────────────────────────────


class RegisterIn(BaseModel):
    nombre: str
    password: str
    codigo_invitacion: str | None = None


@router.post("/api/register", status_code=201)
@limiter.limit("10/minute")
def api_register(
    request: Request,
    payload: RegisterIn,
    db: Session = Depends(get_db),
) -> dict:
    from db.models import Grupo

    nombre = payload.nombre.strip()
    if not nombre or len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="Nombre y password (min 4 chars) requeridos")

    # Si registro cerrado, solo se permite con código de invitación
    if not settings.registro_abierto and not payload.codigo_invitacion:
        raise HTTPException(status_code=403, detail="El registro requiere un codigo de invitacion")

    if db.query(User).filter(User.nombre == nombre).one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre")

    MAX_MIEMBROS_GRUPO = 2

    grupo_id = None
    if payload.codigo_invitacion:
        grupo = (
            db.query(Grupo)
            .filter(Grupo.codigo_invitacion == payload.codigo_invitacion.strip())
            .one_or_none()
        )
        if not grupo:
            raise HTTPException(status_code=400, detail="Codigo de invitacion invalido")
        now = datetime.now(UTC).replace(tzinfo=None)
        if grupo.codigo_expira and grupo.codigo_expira < now:
            raise HTTPException(status_code=400, detail="Codigo de invitacion expirado")
        miembros = db.query(User).filter(User.grupo_id == grupo.id).count()
        if miembros >= MAX_MIEMBROS_GRUPO:
            raise HTTPException(status_code=400, detail=f"El grupo ya tiene {MAX_MIEMBROS_GRUPO} miembros (limite alcanzado)")
        grupo_id = grupo.id
        grupo.codigo_invitacion = None
        grupo.codigo_expira = None

    user = User(
        nombre=nombre,
        password_hash=hash_password(payload.password),
        grupo_id=grupo_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Si no se vinculó a grupo, crear uno nuevo
    if not grupo_id:
        grupo = Grupo(nombre=f"Hogar de {nombre}")
        db.add(grupo)
        db.commit()
        db.refresh(grupo)
        user.grupo_id = grupo.id
        db.commit()

    return {"id": user.id, "nombre": user.nombre, "grupo_id": user.grupo_id}


@router.get("/api/auth-config")
def api_auth_config() -> dict:
    """Public endpoint: returns auth configuration for the login page."""
    return {
        "registro_abierto": settings.registro_abierto,
        "google_enabled": bool(settings.google_client_id),
    }


# ── Google OAuth ─────────────────────────────────────────────────────


@router.get("/api/oauth/google/url")
def api_oauth_google_url() -> dict:
    """Returns the Google OAuth consent URL."""
    from urllib.parse import urlencode

    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth no configurado")

    params = urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    })
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}"}


class OAuthCallbackIn(BaseModel):
    code: str


@router.post("/api/oauth/google/callback")
def api_oauth_google_callback(
    payload: OAuthCallbackIn,
    db: Session = Depends(get_db),
) -> dict:
    """Exchange Google auth code for user info, create/find user, return session token."""
    import httpx

    from db.models import Grupo

    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=501, detail="Google OAuth no configurado")

    # 1. Exchange code for tokens
    token_res = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": payload.code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if token_res.status_code != 200:
        raise HTTPException(status_code=401, detail="Error al autenticar con Google")

    tokens = token_res.json()
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No se recibio access_token de Google")

    # 2. Get user info
    userinfo_res = httpx.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if userinfo_res.status_code != 200:
        raise HTTPException(status_code=401, detail="Error al obtener info de Google")

    ginfo = userinfo_res.json()
    google_id = ginfo.get("id")
    email = ginfo.get("email")
    name = ginfo.get("name") or email

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Google no retorno email o id")

    # 3. Find or create user
    user = db.query(User).filter(User.google_id == google_id).one_or_none()

    if not user:
        # Check if there's an existing user with same email
        user = db.query(User).filter(User.email == email).one_or_none()
        if user:
            # Link existing account to Google
            user.google_id = google_id
            db.commit()
        else:
            # Registro cerrado: no se crean cuentas nuevas sin invitación
            if not settings.registro_abierto:
                raise HTTPException(
                    status_code=403,
                    detail="No hay una cuenta asociada a este correo. Pide una invitacion al administrador.",
                )

            # Create new user
            base_name = name
            nombre = base_name
            counter = 1
            while db.query(User).filter(User.nombre == nombre).one_or_none():
                nombre = f"{base_name} {counter}"
                counter += 1

            user = User(
                nombre=nombre,
                email=email,
                google_id=google_id,
                password_hash=None,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Create personal group
            grupo = Grupo(nombre=f"Hogar de {nombre}")
            db.add(grupo)
            db.commit()
            db.refresh(grupo)
            user.grupo_id = grupo.id
            db.commit()

    # 4. Create session
    token = create_session_for_user(user)

    return {"token": token, "user": {"id": user.id, "nombre": user.nombre}}


MAX_MIEMBROS_GRUPO = 2


class UnirseGrupoIn(BaseModel):
    codigo_invitacion: str


class CambiarPasswordIn(BaseModel):
    password_actual: str
    password_nueva: str


@router.post("/api/grupo/invitar")
def api_generar_invitacion(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Genera un código de invitación para el grupo del usuario logueado."""
    from db.models import Grupo
    import secrets as _secrets

    grupo_id = session.get("grupo_id")
    if not grupo_id:
        raise HTTPException(status_code=400, detail="No perteneces a un grupo")

    grupo = db.query(Grupo).filter_by(id=grupo_id).one_or_none()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    miembros = db.query(User).filter(User.grupo_id == grupo.id).count()
    if miembros >= MAX_MIEMBROS_GRUPO:
        raise HTTPException(status_code=400, detail=f"Tu grupo ya tiene {MAX_MIEMBROS_GRUPO} miembros")

    codigo = _secrets.token_urlsafe(6)[:8].upper()
    grupo.codigo_invitacion = codigo
    grupo.codigo_expira = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=24)
    db.commit()

    return {"codigo": codigo, "expira_en": "24 horas"}


@router.get("/api/me")
def api_me(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    from db.models import Grupo
    user = db.query(User).filter_by(id=session["user_id"]).one_or_none()
    if not user:
        raise HTTPException(status_code=404)

    grupo = None
    miembros = []
    codigo_activo = None
    if user.grupo_id:
        g = db.query(Grupo).filter_by(id=user.grupo_id).one_or_none()
        if g:
            grupo = {"id": g.id, "nombre": g.nombre}
            miembros = [
                {"id": m.id, "nombre": m.nombre}
                for m in db.query(User).filter_by(grupo_id=g.id).all()
            ]
            if g.codigo_invitacion and g.codigo_expira and g.codigo_expira > datetime.now(UTC).replace(tzinfo=None):
                codigo_activo = g.codigo_invitacion

    return {
        "id": user.id,
        "nombre": user.nombre,
        "grupo": grupo,
        "miembros": miembros,
        "codigo_invitacion_activo": codigo_activo,
        "max_miembros": MAX_MIEMBROS_GRUPO,
    }


@router.post("/api/grupo/unirse")
def api_unirse_grupo(
    payload: UnirseGrupoIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    from db.models import Grupo

    user = db.query(User).filter_by(id=session["user_id"]).one()

    # Verificar que no esté ya en un grupo con otros miembros
    if user.grupo_id:
        otros = db.query(User).filter(User.grupo_id == user.grupo_id, User.id != user.id).count()
        if otros > 0:
            raise HTTPException(status_code=400, detail="Ya perteneces a un grupo familiar")

    grupo = (
        db.query(Grupo)
        .filter(Grupo.codigo_invitacion == payload.codigo_invitacion.strip())
        .one_or_none()
    )
    if not grupo:
        raise HTTPException(status_code=400, detail="Codigo invalido")
    now = datetime.now(UTC).replace(tzinfo=None)
    if grupo.codigo_expira and grupo.codigo_expira < now:
        raise HTTPException(status_code=400, detail="Codigo expirado")
    miembros = db.query(User).filter(User.grupo_id == grupo.id).count()
    if miembros >= MAX_MIEMBROS_GRUPO:
        raise HTTPException(status_code=400, detail=f"El grupo ya tiene {MAX_MIEMBROS_GRUPO} miembros")

    # Eliminar grupo anterior si estaba solo
    old_grupo_id = user.grupo_id
    user.grupo_id = grupo.id
    grupo.codigo_invitacion = None
    grupo.codigo_expira = None
    db.commit()

    # Limpiar grupo vacío
    if old_grupo_id:
        remaining = db.query(User).filter(User.grupo_id == old_grupo_id).count()
        if remaining == 0:
            db.query(Grupo).filter_by(id=old_grupo_id).delete()
            db.commit()

    return {"status": "ok", "grupo": grupo.nombre}


@router.post("/api/cambiar-password")
@limiter.limit("5/minute")
def api_cambiar_password(
    request: Request,
    payload: CambiarPasswordIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    from admin.auth import _verify_password
    user = db.query(User).filter_by(id=session["user_id"]).one()
    if not _verify_password(payload.password_actual, user.password_hash):
        raise HTTPException(status_code=400, detail="Contrasena actual incorrecta")
    if len(payload.password_nueva) < 4:
        raise HTTPException(status_code=400, detail="La nueva contrasena debe tener al menos 4 caracteres")
    user.password_hash = hash_password(payload.password_nueva)
    db.commit()
    return {"status": "ok"}


@router.get("", response_class=HTMLResponse, response_model=None)
def panel(request: Request) -> str | RedirectResponse:
    token = request.cookies.get(COOKIE_NAME)
    if not get_session(token):
        return RedirectResponse("/admin/login", status_code=302)
    return PAGE.read_text(encoding="utf-8")


@router.get("/api/movimientos")
def api_listar_movimientos(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        # "Hogar" mode — filter by group members only
        visible = _visible_ids(session, db)
        return [svc.serializar_movimiento(m) for m in svc.listar_movimientos(db, limit=limit, user_ids=visible)]
    return [svc.serializar_movimiento(m) for m in svc.listar_movimientos(db, limit=limit, user_id=uid)]


@router.get("/api/movimientos/export-csv")
def api_exportar_csv(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
    mes: str | None = None,
) -> StreamingResponse:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        movs = svc.listar_movimientos(db, limit=10000, user_ids=_visible_ids(session, db))
    else:
        movs = svc.listar_movimientos(db, limit=10000, user_id=uid)
    if mes:
        movs = [m for m in movs if m.fecha_gasto and str(m.fecha_gasto).startswith(mes)]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Fecha", "Usuario", "Categoria", "Tipo", "Monto", "Descripcion", "Medio de pago", "Compartido"])
    for m in movs:
        s = svc.serializar_movimiento(m)
        writer.writerow([
            s.get("fecha_gasto", ""),
            s.get("usuario", ""),
            s.get("categoria", ""),
            s.get("tipo", ""),
            s.get("monto_cop", 0),
            s.get("descripcion", ""),
            s.get("medio_pago", ""),
            "Si" if s.get("es_compartido") else "No",
        ])
    buf.seek(0)
    filename = f"movimientos_{mes or 'todos'}.csv"
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/movimientos", status_code=201)
def api_crear_movimiento(
    payload: MovimientoIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        creado = svc.crear_movimiento(
            db,
            user_id=payload.user_id,
            categoria_id=payload.categoria_id,
            monto_cop=payload.monto_cop,
            descripcion=payload.descripcion,
            fecha_gasto=payload.fecha_gasto,
            medio_pago=payload.medio_pago,
            es_compartido=payload.es_compartido,
            porcentaje_compartido=payload.porcentaje_compartido,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.serializar_movimiento(creado)


@router.patch("/api/movimientos/{movimiento_id}")
@router.put("/api/movimientos/{movimiento_id}")
def api_actualizar_movimiento(
    movimiento_id: int,
    payload: MovimientoPatch,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    movimiento = svc.obtener_movimiento(db, movimiento_id)
    if movimiento is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if movimiento.user_id != session["user_id"]:
        raise HTTPException(status_code=403, detail="Solo puedes editar tus propios registros")
    try:
        actualizado = svc.actualizar_movimiento(
            db,
            movimiento,
            user_id=payload.user_id,
            categoria_id=payload.categoria_id,
            monto_cop=payload.monto_cop,
            descripcion=payload.descripcion,
            fecha_gasto=payload.fecha_gasto,
            limpiar_categoria=payload.limpiar_categoria,
            medio_pago=payload.medio_pago,
            es_compartido=payload.es_compartido,
            porcentaje_compartido=payload.porcentaje_compartido,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.serializar_movimiento(actualizado)


@router.delete("/api/movimientos/{movimiento_id}")
def api_eliminar_movimiento(
    movimiento_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    movimiento = svc.obtener_movimiento(db, movimiento_id)
    if movimiento is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if movimiento.user_id != session["user_id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propios registros")
    svc.eliminar_movimiento(db, movimiento)
    return {"status": "ok"}


@router.get("/api/categorias")
def api_listar_categorias(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, int | str]]:
    cats = db.query(Categoria).order_by(Categoria.id).all()
    return [{"id": c.id, "nombre": c.nombre, "tipo": c.tipo} for c in cats]


@router.post("/api/categorias", status_code=201)
def api_crear_categoria(
    payload: CategoriaIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    try:
        cat = svc.crear_categoria(db, nombre=payload.nombre, tipo=payload.tipo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": cat.id, "nombre": cat.nombre, "tipo": cat.tipo}


@router.patch("/api/categorias/{categoria_id}")
def api_actualizar_categoria(
    categoria_id: int,
    payload: CategoriaIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    cat = db.query(Categoria).filter(Categoria.id == categoria_id).one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    try:
        cat = svc.actualizar_categoria(db, cat, nombre=payload.nombre, tipo=payload.tipo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": cat.id, "nombre": cat.nombre, "tipo": cat.tipo}


@router.delete("/api/categorias/{categoria_id}")
def api_eliminar_categoria(
    categoria_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    cat = db.query(Categoria).filter(Categoria.id == categoria_id).one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    try:
        svc.eliminar_categoria(db, cat)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "ok"}


@router.get("/api/usuarios")
def api_listar_usuarios(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    visible = _visible_ids(session, db)
    users = db.query(User).filter(User.id.in_(visible)).order_by(User.id).all()
    return [{"id": u.id, "nombre": u.nombre, "email": u.email} for u in users]


@router.post("/api/usuarios", status_code=201)
def api_crear_usuario(
    payload: UsuarioIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    try:
        user = svc.crear_usuario(db, nombre=payload.nombre, email=payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": user.id, "nombre": user.nombre, "email": user.email}


@router.patch("/api/usuarios/{user_id}")
def api_actualizar_usuario(
    user_id: int,
    payload: UsuarioIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        user = svc.actualizar_usuario(
            db,
            user,
            nombre=payload.nombre,
            email=payload.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": user.id, "nombre": user.nombre, "email": user.email}


@router.delete("/api/usuarios/{user_id}")
def api_eliminar_usuario(
    user_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        svc.eliminar_usuario(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "ok"}


# ── Presupuestos ──────────────────────────────────────────────────────


@router.get("/api/presupuestos")
def api_listar_presupuestos(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
    mes: str | None = None,
) -> list[dict[str, Any]]:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        return [svc_ppto.serializar_presupuesto(p) for p in svc_ppto.listar_presupuestos(db, mes=mes, user_ids=_visible_ids(session, db))]
    return [svc_ppto.serializar_presupuesto(p) for p in svc_ppto.listar_presupuestos(db, user_id=uid, mes=mes)]


@router.get("/api/presupuestos/resumen")
def api_resumen_presupuestos(
    user_id: int,
    mes: str,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return svc_ppto.presupuesto_vs_real(db, user_id=user_id, mes=mes)


@router.post("/api/presupuestos", status_code=201)
def api_crear_presupuesto(
    payload: PresupuestoIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        p = svc_ppto.crear_presupuesto(
            db,
            user_id=payload.user_id,
            categoria_id=payload.categoria_id,
            monto_limite_cop=payload.monto_limite_cop,
            mes_vigente=payload.mes_vigente,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc_ppto.serializar_presupuesto(p)


@router.delete("/api/presupuestos/{presupuesto_id}")
def api_eliminar_presupuesto(
    presupuesto_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    p = db.query(Presupuesto).filter(Presupuesto.id == presupuesto_id).one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    svc_ppto.eliminar_presupuesto(db, p)
    return {"status": "ok"}


# ── Gastos fijos ──────────────────────────────────────────────────────


@router.get("/api/gastos-fijos")
def api_listar_gastos_fijos(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        return [svc_gf.serializar_gasto_fijo(gf) for gf in svc_gf.listar_gastos_fijos(db, user_ids=_visible_ids(session, db))]
    return [svc_gf.serializar_gasto_fijo(gf) for gf in svc_gf.listar_gastos_fijos(db, user_id=uid)]


@router.post("/api/gastos-fijos", status_code=201)
def api_crear_gasto_fijo(
    payload: GastoFijoIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        gf = svc_gf.crear_gasto_fijo(
            db,
            user_id=payload.user_id,
            categoria_id=payload.categoria_id,
            nombre=payload.nombre,
            monto_cop=payload.monto_cop,
            es_compartido=payload.es_compartido,
            porcentaje_compartido=payload.porcentaje_compartido,
            dia_esperado=payload.dia_esperado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc_gf.serializar_gasto_fijo(gf)


@router.patch("/api/gastos-fijos/{gasto_fijo_id}")
def api_actualizar_gasto_fijo(
    gasto_fijo_id: int,
    payload: GastoFijoPatch,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    gf = db.query(GastoFijo).filter(GastoFijo.id == gasto_fijo_id).one_or_none()
    if gf is None:
        raise HTTPException(status_code=404, detail="Gasto fijo no encontrado")
    try:
        gf = svc_gf.actualizar_gasto_fijo(
            db,
            gf,
            nombre=payload.nombre,
            monto_cop=payload.monto_cop,
            categoria_id=payload.categoria_id,
            es_compartido=payload.es_compartido,
            porcentaje_compartido=payload.porcentaje_compartido,
            activo=payload.activo,
            dia_esperado=payload.dia_esperado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc_gf.serializar_gasto_fijo(gf)


@router.delete("/api/gastos-fijos/{gasto_fijo_id}")
def api_eliminar_gasto_fijo(
    gasto_fijo_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    gf = db.query(GastoFijo).filter(GastoFijo.id == gasto_fijo_id).one_or_none()
    if gf is None:
        raise HTTPException(status_code=404, detail="Gasto fijo no encontrado")
    if gf.user_id != session["user_id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propios registros")
    svc_gf.eliminar_gasto_fijo(db, gf)
    return {"status": "ok"}


# ── Inteligencia Financiera ──────────────────────────────────────────


@router.get("/api/flujo-caja")
def api_flujo_caja(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    mes: str | None = None,
    user_id: int | None = None,
) -> dict:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        return svc_intel.flujo_de_caja(db, mes=mes, user_ids=_visible_ids(session, db))
    return svc_intel.flujo_de_caja(db, mes=mes, user_id=uid)


@router.get("/api/alertas")
def api_alertas(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict]:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        return svc_intel.obtener_alertas(db, user_ids=_visible_ids(session, db))
    return svc_intel.obtener_alertas(db, user_id=uid)


@router.get("/api/salud-financiera")
def api_salud_financiera(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> dict:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        return svc_intel.salud_financiera(db, user_ids=_visible_ids(session, db))
    return svc_intel.salud_financiera(db, user_id=uid)


# ── Ingresos Recurrentes ─────────────────────────────────────────────


class IngresoIn(BaseModel):
    user_id: int
    nombre: str
    tipo: str = "fijo"
    frecuencia: str = "mensual"
    monto_cop: int
    dia_pago_1: int | None = None
    dia_pago_2: int | None = None


class IngresoPatch(BaseModel):
    nombre: str | None = None
    tipo: str | None = None
    frecuencia: str | None = None
    monto_cop: int | None = None
    dia_pago_1: int | None = None
    dia_pago_2: int | None = None
    activo: bool | None = None


@router.get("/api/ingresos")
def api_listar_ingresos(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict]:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        return [svc_ingresos.serializar_ingreso(i) for i in svc_ingresos.listar_ingresos(db, user_ids=_visible_ids(session, db))]
    return [svc_ingresos.serializar_ingreso(i) for i in svc_ingresos.listar_ingresos(db, user_id=uid)]


@router.post("/api/ingresos", status_code=201)
def api_crear_ingreso(
    payload: IngresoIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    try:
        ingreso = svc_ingresos.crear_ingreso(
            db,
            user_id=payload.user_id,
            nombre=payload.nombre,
            tipo=payload.tipo,
            frecuencia=payload.frecuencia,
            monto_cop=payload.monto_cop,
            dia_pago_1=payload.dia_pago_1,
            dia_pago_2=payload.dia_pago_2,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc_ingresos.serializar_ingreso(ingreso)


@router.patch("/api/ingresos/{ingreso_id}")
def api_actualizar_ingreso(
    ingreso_id: int,
    payload: IngresoPatch,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    ingreso = svc_ingresos.obtener_ingreso(db, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado")
    try:
        actualizado = svc_ingresos.actualizar_ingreso(
            db,
            ingreso,
            nombre=payload.nombre,
            tipo=payload.tipo,
            frecuencia=payload.frecuencia,
            monto_cop=payload.monto_cop,
            dia_pago_1=payload.dia_pago_1,
            dia_pago_2=payload.dia_pago_2,
            activo=payload.activo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc_ingresos.serializar_ingreso(actualizado)


@router.delete("/api/ingresos/{ingreso_id}")
def api_eliminar_ingreso(
    ingreso_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ingreso = svc_ingresos.obtener_ingreso(db, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado")
    if ingreso.user_id != session["user_id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propios registros")
    svc_ingresos.eliminar_ingreso(db, ingreso)
    return {"status": "ok"}


@router.get("/api/ingresos/resumen")
def api_resumen_ingresos(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    mes: str | None = None,
    user_id: int | None = None,
) -> dict:
    if not mes:
        from tiempo import ahora_bogota
        mes = ahora_bogota().strftime("%Y-%m")
    # Auto-registrar ingresos fijos del mes consultado
    svc_ingresos.sincronizar_ingresos_fijos(db, mes=mes)
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        return svc_ingresos.resumen_ingresos(db, mes=mes, user_ids=_visible_ids(session, db))
    return svc_ingresos.resumen_ingresos(db, mes=mes, user_id=uid)


# ── Tarjetas de Crédito ──────────────────────────────────────────────


class TarjetaIn(BaseModel):
    user_id: int
    banco: str
    nombre: str
    ultimos_4: str | None = None
    fecha_corte: int
    fecha_pago: int
    tasa_ea: float | None = None
    cupo_total_cop: int | None = None


class TarjetaPatch(BaseModel):
    banco: str | None = None
    nombre: str | None = None
    ultimos_4: str | None = None
    fecha_corte: int | None = None
    fecha_pago: int | None = None
    tasa_ea: float | None = None
    cupo_total_cop: int | None = None
    activa: bool | None = None


@router.get("/api/tarjetas")
def api_listar_tarjetas(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict]:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        tarjetas = svc_tarjetas.listar_tarjetas(db, user_ids=_visible_ids(session, db))
    else:
        tarjetas = svc_tarjetas.listar_tarjetas(db, user_id=uid)
    return [svc_tarjetas.serializar_tarjeta(t) for t in tarjetas]


@router.post("/api/tarjetas", status_code=201)
def api_crear_tarjeta(
    payload: TarjetaIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    try:
        tarjeta = svc_tarjetas.crear_tarjeta(
            db,
            user_id=payload.user_id,
            banco=payload.banco,
            nombre=payload.nombre,
            ultimos_4=payload.ultimos_4,
            fecha_corte=payload.fecha_corte,
            fecha_pago=payload.fecha_pago,
            tasa_ea=payload.tasa_ea,
            cupo_total_cop=payload.cupo_total_cop,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc_tarjetas.serializar_tarjeta(tarjeta)


@router.patch("/api/tarjetas/{tarjeta_id}")
def api_actualizar_tarjeta(
    tarjeta_id: int,
    payload: TarjetaPatch,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    tarjeta = svc_tarjetas.obtener_tarjeta(db, tarjeta_id)
    if tarjeta is None:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    try:
        actualizada = svc_tarjetas.actualizar_tarjeta(
            db,
            tarjeta,
            banco=payload.banco,
            nombre=payload.nombre,
            ultimos_4=payload.ultimos_4,
            fecha_corte=payload.fecha_corte,
            fecha_pago=payload.fecha_pago,
            tasa_ea=payload.tasa_ea,
            cupo_total_cop=payload.cupo_total_cop,
            activa=payload.activa,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc_tarjetas.serializar_tarjeta(actualizada)


@router.delete("/api/tarjetas/{tarjeta_id}")
def api_eliminar_tarjeta(
    tarjeta_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    tarjeta = svc_tarjetas.obtener_tarjeta(db, tarjeta_id)
    if tarjeta is None:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    if tarjeta.user_id != session["user_id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propios registros")
    svc_tarjetas.eliminar_tarjeta(db, tarjeta)
    return {"status": "ok"}


@router.get("/api/tarjetas/{tarjeta_id}/proyeccion")
def api_proyeccion_tarjeta(
    tarjeta_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    meses: int = 6,
) -> dict:
    tarjeta = svc_tarjetas.obtener_tarjeta(db, tarjeta_id)
    if tarjeta is None:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    return svc_tarjetas.proyectar_cuotas_por_mes(db, tarjeta_id=tarjeta_id, meses=meses)


@router.get("/api/proyeccion-cuotas")
def api_proyeccion_cuotas_global(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
    meses: int = 6,
) -> dict:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        return svc_tarjetas.proyectar_cuotas_por_mes(db, user_ids=_visible_ids(session, db), meses=meses)
    return svc_tarjetas.proyectar_cuotas_por_mes(db, user_id=uid, meses=meses)


# ── Cuotas TDC ────────────────────────────────────────────────────────


@router.get("/api/cuotas")
def api_listar_cuotas(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        return [svc_cuotas.serializar_compra(c) for c in svc_cuotas.listar_compras(db, user_ids=_visible_ids(session, db))]
    return [svc_cuotas.serializar_compra(c) for c in svc_cuotas.listar_compras(db, user_id=uid)]


@router.post("/api/cuotas", status_code=201)
def api_crear_cuota(
    payload: CompraIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        c = svc_cuotas.crear_compra(
            db,
            user_id=payload.user_id,
            fecha_compra=payload.fecha_compra,
            establecimiento=payload.establecimiento,
            valor_total_cop=payload.valor_total_cop,
            num_cuotas=payload.num_cuotas,
            tarjeta_id=payload.tarjeta_id,
            tasa_ea=payload.tasa_ea,
            descripcion=payload.descripcion,
            numero_transaccion=payload.numero_transaccion,
            es_compartido=payload.es_compartido,
            movimiento_id=payload.movimiento_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc_cuotas.serializar_compra(c)


@router.post("/api/cuotas/{compra_id}/pago", status_code=201)
def api_registrar_pago_cuota(
    compra_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    compra = svc_cuotas.obtener_compra(db, compra_id)
    if compra is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    try:
        mov = svc_cuotas.registrar_pago(db, compra)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.serializar_movimiento(mov)


@router.patch("/api/cuotas/{compra_id}")
def api_actualizar_cuota(
    compra_id: int,
    payload: CompraPatch,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    compra = svc_cuotas.obtener_compra(db, compra_id)
    if compra is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    if payload.establecimiento is not None:
        compra.establecimiento = payload.establecimiento
    if payload.fecha_compra is not None:
        compra.fecha_compra = payload.fecha_compra
    if payload.valor_total_cop is not None:
        compra.valor_total_cop = payload.valor_total_cop
    if payload.num_cuotas is not None:
        compra.num_cuotas = payload.num_cuotas
    if payload.cuotas_pagadas is not None:
        compra.cuotas_pagadas = payload.cuotas_pagadas
    if payload.valor_cuota_cop is not None:
        compra.valor_cuota_cop = payload.valor_cuota_cop
    if payload.valor_intereses_cop is not None:
        compra.valor_intereses_cop = payload.valor_intereses_cop
    if payload.tasa_ea is not None:
        compra.tasa_ea = payload.tasa_ea
    if payload.numero_transaccion is not None:
        compra.numero_transaccion = payload.numero_transaccion
    if payload.descripcion is not None:
        compra.descripcion = payload.descripcion
    # Recalcular saldo y estado
    compra.saldo_pendiente_cop = max(0, compra.valor_total_cop - (compra.cuotas_pagadas * compra.valor_cuota_cop))
    compra.liquidada = compra.cuotas_pagadas >= compra.num_cuotas
    if compra.liquidada:
        compra.saldo_pendiente_cop = 0
    # Sincronizar cambios al movimiento vinculado
    from db.models import Movimiento as Mov

    mov_vinculado = db.query(Mov).filter(
        Mov.compra_cuotas_id == compra.id,
        Mov.eliminado_en.is_(None),
    ).first()
    if mov_vinculado:
        if payload.establecimiento is not None:
            mov_vinculado.descripcion = compra.establecimiento
        if payload.valor_total_cop is not None:
            mov_vinculado.monto_cop = compra.valor_total_cop
        if payload.fecha_compra is not None:
            mov_vinculado.fecha_gasto = compra.fecha_compra
        if payload.es_compartido is not None:
            mov_vinculado.es_compartido = payload.es_compartido
            mov_vinculado.porcentaje_compartido = 50 if payload.es_compartido else None
    db.commit()
    # Re-obtener con pagos frescos para serializar correctamente
    compra_fresh = svc_cuotas.obtener_compra(db, compra.id)
    return svc_cuotas.serializar_compra(compra_fresh or compra)


@router.delete("/api/cuotas/{compra_id}")
def api_eliminar_cuota(
    compra_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    compra = svc_cuotas.obtener_compra(db, compra_id)
    if compra is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    if compra.user_id != session["user_id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propios registros")
    svc_cuotas.eliminar_compra(db, compra)
    return {"status": "ok"}


# ── Balance compartido ────────────────────────────────────────────────


@router.get("/api/compartido")
def api_balance_compartido(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    mes: str | None = None,
) -> dict[str, Any]:
    grupo_id = session.get("grupo_id")
    return svc_balance.calcular_balance(db, mes=mes, grupo_id=grupo_id)


# ── Deudas ────────────────────────────────────────────────────────────


@router.get("/api/deudas")
def api_listar_deudas(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    visible = _visible_ids(session, db)
    q = db.query(Deuda).filter(Deuda.user_id.in_(visible))
    if user_id is not None:
        uid = _filter_user_id(session, db, user_id)
        q = db.query(Deuda).filter(Deuda.user_id == uid)
    deudas = q.order_by(Deuda.id).all()
    return [
        {
            "id": d.id,
            "user_id": d.user_id,
            "nombre": d.nombre,
            "tipo": d.tipo,
            "acreedor": d.acreedor,
            "monto_original_cop": d.monto_original_cop,
            "saldo_cop": d.saldo_cop,
            "cuota_mensual_cop": d.cuota_mensual_cop,
            "tasa_ea": d.tasa_ea,
            "activa": d.activa,
            "fecha_inicio": d.fecha_inicio.isoformat() if d.fecha_inicio else None,
            "fecha_limite": d.fecha_limite.isoformat() if d.fecha_limite else None,
            "notas": d.notas,
        }
        for d in deudas
    ]


@router.post("/api/deudas", status_code=201)
def api_crear_deuda(
    payload: DeudaIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if db.query(User).filter(User.id == payload.user_id).one_or_none() is None:
        raise HTTPException(status_code=400, detail="Usuario no existe")
    d = Deuda(
        user_id=payload.user_id,
        nombre=payload.nombre.strip(),
        tipo=payload.tipo,
        acreedor=payload.acreedor,
        monto_original_cop=payload.monto_original_cop,
        saldo_cop=payload.saldo_cop,
        cuota_mensual_cop=payload.cuota_mensual_cop,
        tasa_ea=payload.tasa_ea,
        notas=payload.notas,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {
        "id": d.id,
        "user_id": d.user_id,
        "nombre": d.nombre,
        "tipo": d.tipo,
        "acreedor": d.acreedor,
        "monto_original_cop": d.monto_original_cop,
        "saldo_cop": d.saldo_cop,
        "cuota_mensual_cop": d.cuota_mensual_cop,
        "tasa_ea": d.tasa_ea,
        "activa": d.activa,
        "notas": d.notas,
    }


@router.patch("/api/deudas/{deuda_id}")
def api_actualizar_deuda(
    deuda_id: int,
    payload: DeudaIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    d = db.query(Deuda).filter(Deuda.id == deuda_id).one_or_none()
    if d is None:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
    d.nombre = payload.nombre.strip()
    d.tipo = payload.tipo
    d.acreedor = payload.acreedor
    d.monto_original_cop = payload.monto_original_cop
    d.saldo_cop = payload.saldo_cop
    d.cuota_mensual_cop = payload.cuota_mensual_cop
    d.tasa_ea = payload.tasa_ea
    d.notas = payload.notas
    db.commit()
    db.refresh(d)
    return {
        "id": d.id,
        "user_id": d.user_id,
        "nombre": d.nombre,
        "tipo": d.tipo,
        "acreedor": d.acreedor,
        "monto_original_cop": d.monto_original_cop,
        "saldo_cop": d.saldo_cop,
        "cuota_mensual_cop": d.cuota_mensual_cop,
        "tasa_ea": d.tasa_ea,
        "activa": d.activa,
        "notas": d.notas,
    }


@router.delete("/api/deudas/{deuda_id}")
def api_eliminar_deuda(
    deuda_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    d = db.query(Deuda).filter(Deuda.id == deuda_id).one_or_none()
    if d is None:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
    if d.user_id != session["user_id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propios registros")
    db.delete(d)
    db.commit()
    return {"status": "ok"}


# ── Metas de Ahorro ──────────────────────────────────────────────────


class MetaAhorroIn(BaseModel):
    user_id: int
    nombre: str
    monto_objetivo_cop: int
    monto_actual_cop: int = 0
    fecha_limite: date | None = None


class MetaAhorroPatch(BaseModel):
    nombre: str | None = None
    monto_objetivo_cop: int | None = None
    monto_actual_cop: int | None = None
    fecha_limite: date | None = None
    activa: bool | None = None


@router.get("/api/metas-ahorro")
def api_listar_metas(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict]:
    uid = _filter_user_id(session, db, user_id)
    if uid is None:
        metas = svc_metas.listar_metas(db, user_ids=_visible_ids(session, db))
    else:
        metas = svc_metas.listar_metas(db, user_id=uid)
    return [svc_metas.serializar_meta(m) for m in metas]


@router.post("/api/metas-ahorro", status_code=201)
def api_crear_meta(
    data: MetaAhorroIn,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    data.user_id = session["user_id"]
    meta = svc_metas.crear_meta(
        db,
        user_id=data.user_id,
        nombre=data.nombre,
        monto_objetivo_cop=data.monto_objetivo_cop,
        monto_actual_cop=data.monto_actual_cop,
        fecha_limite=data.fecha_limite,
    )
    return svc_metas.serializar_meta(meta)


@router.patch("/api/metas-ahorro/{meta_id}")
def api_actualizar_meta(
    meta_id: int,
    data: MetaAhorroPatch,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    meta = db.query(MetaAhorro).filter(MetaAhorro.id == meta_id).one_or_none()
    if meta is None:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    if meta.user_id != session["user_id"]:
        raise HTTPException(status_code=403, detail="Solo puedes editar tus propias metas")
    kwargs: dict = {}
    if data.nombre is not None:
        kwargs["nombre"] = data.nombre
    if data.monto_objetivo_cop is not None:
        kwargs["monto_objetivo_cop"] = data.monto_objetivo_cop
    if data.monto_actual_cop is not None:
        kwargs["monto_actual_cop"] = data.monto_actual_cop
    if data.fecha_limite is not None:
        kwargs["fecha_limite"] = data.fecha_limite
    if data.activa is not None:
        kwargs["activa"] = data.activa
    meta = svc_metas.actualizar_meta(db, meta, **kwargs)
    return svc_metas.serializar_meta(meta)


@router.delete("/api/metas-ahorro/{meta_id}")
def api_eliminar_meta(
    meta_id: int,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    meta = db.query(MetaAhorro).filter(MetaAhorro.id == meta_id).one_or_none()
    if meta is None:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    if meta.user_id != session["user_id"]:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propias metas")
    svc_metas.eliminar_meta(db, meta)
    return {"status": "ok"}
