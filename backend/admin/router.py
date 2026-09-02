from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import Any

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from admin.auth import (
    COOKIE_NAME,
    generate_totp_uri,
    get_session,
    login,
    logout,
    require_admin,
    totp_enabled,
)

limiter = Limiter(key_func=get_remote_address)
from db.models import Categoria, CompraCuotas, Deuda, GastoFijo, Presupuesto, User
from db.session import get_db
from services import admin as svc
from services import balance as svc_balance
from services import cuotas as svc_cuotas
from services import gastos_fijos as svc_gf
from services import presupuesto as svc_ppto

router = APIRouter(prefix="/admin", tags=["admin"])
PAGE = Path(__file__).parent / "index.html"
LOGIN_PAGE = Path(__file__).parent / "login.html"


class MovimientoIn(BaseModel):
    user_id: int
    categoria_id: int | None = None
    monto_cop: int
    descripcion: str | None = None
    mensaje_original: str | None = None
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
    mensaje_original: str | None = None
    fecha_gasto: date | None = None
    medio_pago: str | None = None
    es_compartido: bool | None = None
    porcentaje_compartido: int | None = None


class CategoriaIn(BaseModel):
    nombre: str
    tipo: str = "gasto"


class UsuarioIn(BaseModel):
    nombre: str
    numero_whatsapp: str


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
    tarjeta: str | None = None
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
    tarjeta: str | None = None
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


def _render_login(error: str = "") -> str:
    totp_field = ""
    if totp_enabled():
        totp_field = (
            '<label>Codigo 2FA'
            '<input name="totp_code" type="text" inputmode="numeric" '
            'pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code" '
            'placeholder="000000" required>'
            "</label>"
            '<p class="totp-hint">Abre tu app de autenticacion (Google Authenticator, Authy)</p>'
        )
    html = LOGIN_PAGE.read_text(encoding="utf-8")
    return html.replace("{error}", error).replace("{totp_field}", totp_field)


@router.get("/login", response_class=HTMLResponse, response_model=None)
def login_page(request: Request) -> HTMLResponse | RedirectResponse:
    token = request.cookies.get(COOKIE_NAME)
    if get_session(token):
        return RedirectResponse("/admin", status_code=302)
    return HTMLResponse(_render_login())


@router.post("/login", response_model=None)
@limiter.limit("5/minute")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    totp_code: str | None = Form(None),
) -> RedirectResponse:
    client_ip = request.client.host if request.client else ""
    token = login(username, password, totp_code, client_ip=client_ip)
    if token is None:
        return HTMLResponse(_render_login("Usuario, contrasena o codigo 2FA incorrectos"), status_code=401)
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


@router.get("/totp-setup", response_class=HTMLResponse, response_model=None)
def totp_setup(request: Request) -> str | RedirectResponse:
    token = request.cookies.get(COOKIE_NAME)
    if not get_session(token):
        return RedirectResponse("/admin/login", status_code=302)
    secret, uri = generate_totp_uri()
    buf = io.BytesIO()
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage)
    img.save(buf)
    svg = buf.getvalue().decode()
    enabled = totp_enabled()
    badge = (
        '<span class="badge on">Activo</span>'
        if enabled
        else '<span class="badge off">Inactivo</span>'
    )
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>2FA Setup</title>
<style>
:root {{ --bg:#0f1115; --card:#181c24; --line:#2a3140; --txt:#eef1f6; --muted:#93a0b5; --acc:#6ee7b7; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--txt); display:flex; justify-content:center; padding:2rem; }}
.card {{ background:var(--card); border-radius:16px; padding:2rem; width:min(480px, 92vw); }}
h1 {{ margin:0 0 1rem; font-size:1.3rem; display:flex; align-items:center; gap:.6rem; }}
h1 span {{ color:var(--acc); }}
.badge {{ font-size:.75rem; padding:.2rem .6rem; border-radius:20px; font-weight:600; }}
.badge.on {{ background:#065f46; color:#6ee7b7; }}
.badge.off {{ background:#7c2d12; color:#fbbf24; }}
.qr {{ background:#fff; padding:20px; border-radius:16px; display:inline-block; margin:1rem 0; }}
.qr svg {{ width:220px; height:220px; display:block; }}
.secret {{ background:var(--bg); padding:.6rem 1rem; border-radius:8px; font-family:monospace; font-size:1.1rem; letter-spacing:.15em; word-break:break-all; user-select:all; cursor:pointer; border:1px solid var(--line); }}
.steps {{ color:var(--muted); font-size:.9rem; line-height:1.7; }}
.steps li {{ margin-bottom:.5rem; }}
.apps {{ display:flex; gap:.5rem; flex-wrap:wrap; margin:.8rem 0; }}
.apps span {{ background:var(--bg); border:1px solid var(--line); padding:.3rem .7rem; border-radius:8px; font-size:.8rem; }}
code {{ background:var(--bg); padding:.2rem .5rem; border-radius:6px; font-size:.85rem; }}
a {{ color:var(--acc); }}
.back {{ display:inline-block; margin-top:1rem; text-decoration:none; border:1px solid var(--line); padding:.5rem 1rem; border-radius:8px; }}
</style></head><body>
<div class="card">
<h1>Finanzas <span>2FA</span> {badge}</h1>

<p>Escanea el QR desde tu app de contrasenas:</p>
<div class="apps">
<span>Contrasenas (Apple)</span>
<span>Google Authenticator</span>
<span>Authy</span>
<span>1Password</span>
</div>

<div class="qr">{svg}</div>

<p>O copia el secret manualmente:</p>
<p class="secret">{secret}</p>

<ol class="steps">
<li>Escanea el QR o copia el secret en tu app</li>
<li>En <b>Contrasenas de Apple</b>: abre la app &rarr; crea entrada para <code>localhost</code> &rarr; "Configurar codigo de verificacion" &rarr; pega el secret</li>
<li>Al iniciar sesion, usa el codigo de 6 digitos que genera la app</li>
</ol>

<a href="/admin" class="back">&larr; Volver al panel</a>
</div></body></html>"""


@router.get("", response_class=HTMLResponse, response_model=None)
def panel(request: Request) -> str | RedirectResponse:
    token = request.cookies.get(COOKIE_NAME)
    if not get_session(token):
        return RedirectResponse("/admin/login", status_code=302)
    return PAGE.read_text(encoding="utf-8")


@router.get("/api/movimientos")
def api_listar_movimientos(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    return [svc.serializar_movimiento(m) for m in svc.listar_movimientos(db, limit=limit, user_id=user_id)]


@router.post("/api/movimientos", status_code=201)
def api_crear_movimiento(
    payload: MovimientoIn,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        creado = svc.crear_movimiento(
            db,
            user_id=payload.user_id,
            categoria_id=payload.categoria_id,
            monto_cop=payload.monto_cop,
            descripcion=payload.descripcion,
            mensaje_original=payload.mensaje_original or payload.descripcion or "carga manual",
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
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    movimiento = svc.obtener_movimiento(db, movimiento_id)
    if movimiento is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    try:
        actualizado = svc.actualizar_movimiento(
            db,
            movimiento,
            user_id=payload.user_id,
            categoria_id=payload.categoria_id,
            monto_cop=payload.monto_cop,
            descripcion=payload.descripcion,
            mensaje_original=payload.mensaje_original,
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
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    movimiento = svc.obtener_movimiento(db, movimiento_id)
    if movimiento is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    svc.eliminar_movimiento(db, movimiento)
    return {"status": "ok"}


@router.get("/api/categorias")
def api_listar_categorias(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, int | str]]:
    cats = db.query(Categoria).order_by(Categoria.id).all()
    return [{"id": c.id, "nombre": c.nombre, "tipo": c.tipo} for c in cats]


@router.post("/api/categorias", status_code=201)
def api_crear_categoria(
    payload: CategoriaIn,
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, int | str]]:
    users = db.query(User).order_by(User.id).all()
    return [{"id": u.id, "nombre": u.nombre, "numero_whatsapp": u.numero_whatsapp} for u in users]


@router.post("/api/usuarios", status_code=201)
def api_crear_usuario(
    payload: UsuarioIn,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    try:
        user = svc.crear_usuario(db, nombre=payload.nombre, numero_whatsapp=payload.numero_whatsapp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": user.id, "nombre": user.nombre, "numero_whatsapp": user.numero_whatsapp}


@router.patch("/api/usuarios/{user_id}")
def api_actualizar_usuario(
    user_id: int,
    payload: UsuarioIn,
    _: str = Depends(require_admin),
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
            numero_whatsapp=payload.numero_whatsapp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": user.id, "nombre": user.nombre, "numero_whatsapp": user.numero_whatsapp}


@router.delete("/api/usuarios/{user_id}")
def api_eliminar_usuario(
    user_id: int,
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
    mes: str | None = None,
) -> list[dict[str, Any]]:
    return [svc_ppto.serializar_presupuesto(p) for p in svc_ppto.listar_presupuestos(db, user_id=user_id, mes=mes)]


@router.get("/api/presupuestos/resumen")
def api_resumen_presupuestos(
    user_id: int,
    mes: str,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return svc_ppto.presupuesto_vs_real(db, user_id=user_id, mes=mes)


@router.post("/api/presupuestos", status_code=201)
def api_crear_presupuesto(
    payload: PresupuestoIn,
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    return [svc_gf.serializar_gasto_fijo(gf) for gf in svc_gf.listar_gastos_fijos(db, user_id=user_id)]


@router.post("/api/gastos-fijos", status_code=201)
def api_crear_gasto_fijo(
    payload: GastoFijoIn,
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    gf = db.query(GastoFijo).filter(GastoFijo.id == gasto_fijo_id).one_or_none()
    if gf is None:
        raise HTTPException(status_code=404, detail="Gasto fijo no encontrado")
    svc_gf.eliminar_gasto_fijo(db, gf)
    return {"status": "ok"}


# ── Cuotas TDC ────────────────────────────────────────────────────────


@router.get("/api/cuotas")
def api_listar_cuotas(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    return [svc_cuotas.serializar_compra(c) for c in svc_cuotas.listar_compras(db, user_id=user_id)]


@router.post("/api/cuotas", status_code=201)
def api_crear_cuota(
    payload: CompraIn,
    _: str = Depends(require_admin),
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
            tarjeta=payload.tarjeta,
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
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
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
    if payload.tarjeta is not None:
        compra.tarjeta = payload.tarjeta
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
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    compra = svc_cuotas.obtener_compra(db, compra_id)
    if compra is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    svc_cuotas.eliminar_compra(db, compra)
    return {"status": "ok"}


# ── Balance compartido ────────────────────────────────────────────────


@router.get("/api/compartido")
def api_balance_compartido(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
    mes: str | None = None,
) -> dict[str, Any]:
    return svc_balance.calcular_balance(db, mes=mes)


# ── Deudas ────────────────────────────────────────────────────────────


@router.get("/api/deudas")
def api_listar_deudas(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    q = db.query(Deuda)
    if user_id is not None:
        q = q.filter(Deuda.user_id == user_id)
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
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    d = db.query(Deuda).filter(Deuda.id == deuda_id).one_or_none()
    if d is None:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
    db.delete(d)
    db.commit()
    return {"status": "ok"}
