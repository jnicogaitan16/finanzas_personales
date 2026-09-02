# Skill: Panel Admin

Eres experto en el panel de administracion web de este proyecto.

## Stack

- FastAPI router en `backend/admin/router.py`
- Auth por cookies de sesion + TOTP 2FA
- Frontend: HTML/JS vanilla (SPA en un solo archivo)
- Dark theme con CSS custom properties

## Archivos clave

- `backend/admin/router.py` — Endpoints: login, logout, CRUD APIs, totp-setup, panel HTML
- `backend/admin/auth.py` — Sesiones en memoria, login con TOTP, require_admin dependency
- `backend/admin/index.html` — SPA del admin (tablas, formularios, dialogs)
- `backend/admin/login.html` — Pagina de login (template con {error} y {totp_field})

## Autenticacion

- Cookie `finanzas_session` (HttpOnly, SameSite=Strict, 24h)
- Login: POST /admin/login (form: username, password, totp_code)
- Logout: GET /admin/logout (limpia sesion + cookie)
- 2FA: TOTP con pyotp, QR via qrcode SVG en /admin/totp-setup
- Si ADMIN_TOTP_SECRET esta vacio en .env, 2FA desactivado
- Sesiones en OrderedDict en memoria (max 20, se pierden al reiniciar)

## API endpoints (todos requieren sesion)

```
GET    /admin                          Panel HTML
GET    /admin/login                    Pagina de login
POST   /admin/login                    Autenticar
GET    /admin/logout                   Cerrar sesion
GET    /admin/totp-setup               Configurar 2FA

GET    /admin/api/movimientos          Listar (limit, user_id)
POST   /admin/api/movimientos          Crear
PATCH  /admin/api/movimientos/:id      Editar
PUT    /admin/api/movimientos/:id      Editar
DELETE /admin/api/movimientos/:id      Soft delete

GET    /admin/api/categorias           Listar
POST   /admin/api/categorias           Crear
PATCH  /admin/api/categorias/:id       Editar
DELETE /admin/api/categorias/:id       Borrar (falla si tiene movimientos)

GET    /admin/api/usuarios             Listar
POST   /admin/api/usuarios             Crear
PATCH  /admin/api/usuarios/:id         Editar
DELETE /admin/api/usuarios/:id         Borrar (falla si tiene movimientos)
```

## Patron de seguridad HTML

TODO dato de usuario debe escaparse con la funcion `esc()` antes de interpolarse en HTML:
```javascript
function esc(s) {
  if (s == null) return "";
  const d = document.createElement("div");
  d.textContent = String(s);
  return d.innerHTML;
}
// Uso: ${esc(m.descripcion)}  NUNCA: ${m.descripcion}
```

## Design system (CSS variables)

```css
:root {
  --bg: #0f1115;      /* fondo principal */
  --card: #181c24;    /* fondo tarjetas/tablas */
  --line: #2a3140;    /* bordes */
  --txt: #eef1f6;     /* texto principal */
  --muted: #93a0b5;   /* texto secundario */
  --acc: #6ee7b7;     /* acento verde */
  --danger: #f87171;  /* rojo para borrar */
  --warn: #fbbf24;    /* amarillo para warnings */
}
```

## 401 handler

Cuando una API retorna 401, el JS redirige a login:
```javascript
if (res.status === 401) { window.location.href = "/admin/login"; }
```

Las paginas HTML (/admin, /admin/totp-setup) redirigen con RedirectResponse si no hay sesion.
