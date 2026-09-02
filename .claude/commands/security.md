# Skill: Seguridad del proyecto

Eres experto en seguridad aplicada a este proyecto de finanzas personales.

## Estado de seguridad (auditoria 2026-09-01)

### Implementado

- [x] **XSS**: funcion `esc()` escapa todo dato de usuario en admin HTML
- [x] **Auth**: cookies HttpOnly + SameSite=Strict + TOTP 2FA
- [x] **Webhook verificado**: header apikey validado contra EVOLUTION_API_KEY
- [x] **Endpoints protegidos**: /admin/* requiere sesion, /movimientos y /categorias eliminados
- [x] **Audit log**: tabla audit_log registra cada CRUD de movimientos
- [x] **Soft delete**: movimientos no se borran fisicamente
- [x] **Deduplicacion**: message_id previene registros duplicados por webhook retry
- [x] **.dockerignore**: excluye tests, .env, __pycache__ del container
- [x] **Secrets en .env**: .gitignore excluye .env

### Pendiente

- [ ] **Rate limiting**: sin slowapi ni middleware de rate limit
- [ ] **CSRF**: cookies SameSite=Strict mitiga parcialmente, pero no hay token CSRF
- [ ] **Brute force login**: sin lockout ni delay exponencial
- [ ] **HTTPS**: solo HTTP (aceptable en localhost, riesgo si se expone)
- [ ] **Credenciales DB**: evolution:evolution es debil
- [ ] **Backups**: sin pg_dump automatico

## Checklist OWASP para nuevas features

Al agregar cualquier feature, verificar:

### 1. Inyeccion
- SQLAlchemy ORM previene SQL injection (no usar raw SQL con f-strings)
- Si usas `text()`, siempre con parametros nombrados: `text("SELECT * WHERE id = :id")`, nunca `f"... {id}"`

### 2. Auth
- Todo endpoint con datos debe usar `Depends(require_admin)` o verificar sesion
- Paginas HTML: usar RedirectResponse a /admin/login si no hay sesion (no devolver JSON 401)
- API endpoints: devolver 401 JSON para que el JS redirija

### 3. XSS
- En admin HTML: siempre `${esc(dato)}`, nunca `${dato}`
- En valores de input: siempre `value="${esc(dato)}"`
- En WhatsApp: no aplica (WhatsApp escapa automaticamente)

### 4. Datos sensibles
- Numeros de telefono: visible en admin, verificar que solo admin autenticado los vea
- API keys: solo en .env, nunca en codigo ni logs
- Montos financieros: protegidos por auth

### 5. Configuracion
- DEBUG=False en produccion
- No exponer /docs ni /redoc de FastAPI en produccion si no se necesita
- Evolution API key: rotar si se sospecha compromiso

## Patrones de seguridad del proyecto

### Cookie de sesion
```python
response.set_cookie(
    COOKIE_NAME,
    token,
    httponly=True,      # no accesible por JS
    samesite="strict",  # no se envia cross-site
    max_age=86400,      # 24 horas
)
```

### Comparacion segura de credenciales
```python
from secrets import compare_digest
compare_digest(input, expected)  # timing-safe
```

### Verificacion de webhook
```python
def _verify_webhook(apikey: str | None = Header(None)) -> None:
    expected = settings.evolution_api_key
    if not expected:
        return  # no verificar si no esta configurado
    if apikey is None or not compare_digest(apikey, expected):
        raise HTTPException(status_code=401)
```

### Audit log
```python
# Cada operacion CRUD de movimientos registra en audit_log:
registrar_creacion(db, movimiento, origen="whatsapp")  # o "admin"
registrar_edicion(db, movimiento, valores_antes, origen="whatsapp")
registrar_borrado(db, movimiento, origen="whatsapp")
```

## Respuesta a incidentes

Si se sospecha compromiso:
1. Rotar EVOLUTION_API_KEY, ADMIN_PASSWORD, GROQ_API_KEY, ADMIN_TOTP_SECRET
2. Revisar audit_log para operaciones sospechosas
3. Revisar logs de Docker: `docker compose logs backend --tail 100`
4. Cambiar credenciales de PostgreSQL
5. Rebuild: `docker compose build backend && docker compose up -d`
