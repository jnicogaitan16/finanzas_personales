# Finanzas Personales — Dashboard Web

Dashboard web de finanzas personales para registrar gastos e ingresos en COP (pesos colombianos). Proyecto personal para 2 usuarios (Nico y Daylyng) en Bogota, Colombia.

## Stack

- **Backend:** Python 3.12 + FastAPI + Uvicorn
- **Frontend:** Next.js 16 + React + TailwindCSS + Shadcn/ui
- **DB:** PostgreSQL 15 (Docker, puerto host 5433) + SQLAlchemy 2.0 + Alembic
- **Cache:** Redis 7
- **Auth:** Google OAuth + usuario/contrasena, cookies HttpOnly, sesiones en memoria
- **Orquestacion:** Docker Compose (backend + frontend + postgres + redis + caddy)
- **Tests:** pytest contra PostgreSQL real con SAVEPOINT isolation
- **Deploy:** Oracle Cloud Free Tier (ARM) + Caddy HTTPS + GitHub Actions auto-deploy

## Comandos esenciales

```bash
# Levantar todo
docker compose up -d

# Rebuild backend despues de cambios
docker compose build backend && docker compose up -d backend

# Rebuild frontend despues de cambios
docker compose build frontend && docker compose up -d frontend

# Logs
docker compose logs backend --tail 30
docker compose logs frontend --tail 30

# Tests backend (copiar tests al container y ejecutar)
docker cp backend/tests finanzas-personales-backend-1:/app/tests
docker compose exec backend python -m pytest tests/ -q

# Tests E2E frontend (requiere stack completo corriendo)
cd frontend && npx playwright test

# Migraciones
docker compose exec backend alembic upgrade head
docker compose exec backend alembic revision --autogenerate -m "descripcion"
```

## Branching y deploy

```
feature/* → PR → dev (CI: tests) → merge
                  ↓
              dev → PR → main (CI: tests) → merge → deploy prod (Oracle Cloud)
```

- **dev**: Rama de desarrollo. Todas las features van aqui primero.
- **main**: Rama de produccion. Solo recibe merges desde dev.
- **Ambas ramas protegidas**: requieren PR + CI pasando.
- **Deploy automatico**: Al mergear a main, GitHub Actions hace SSH a Oracle Cloud y rebuild.
- **Dominio prod**: `contabilidad-n-d.duckdns.org` (HTTPS via Caddy)

## Estructura clave

```
backend/
  main.py              # FastAPI app, health endpoint
  config.py            # Pydantic settings desde .env
  tiempo.py            # Timezone Bogota
  utils.py             # format_cop() y utilidades
  admin/
    auth.py            # Login, sesiones, Google OAuth, cookies
    router.py          # Todos los endpoints API
    login.html         # Login page legacy (no usado)
  db/
    models.py          # 12 tablas: users, grupos, movimientos, categorias,
                       #   presupuestos, gastos_fijos, ingresos_recurrentes,
                       #   tarjetas_credito, compras_cuotas, deudas,
                       #   metas_ahorro, audit_log
    session.py         # Engine + get_db
    migrations/        # Alembic (10 revisiones)
  services/
    admin.py           # Registro de movimientos, serialización
    audit.py           # Audit log
    balance.py         # Balance compartido Nico-Day
    cuotas.py          # CRUD compras en cuotas TDC
    gastos_fijos.py    # CRUD gastos fijos
    ingresos.py        # CRUD ingresos recurrentes
    inteligencia.py    # Score 8 criterios, alertas inteligentes, flujo de caja
    metas_ahorro.py    # CRUD metas de ahorro
    presupuesto.py     # CRUD presupuestos + resumen
    tarjetas.py        # CRUD tarjetas de crédito + proyección

frontend/
  src/app/             # Pages: dashboard, movimientos, ingresos, cuotas,
                       #   tarjetas, presupuestos, gastos-fijos, compartido,
                       #   metas-ahorro, categorias, usuarios, cuenta, login
  src/app/api/         # Next.js API routes (proxy al backend)
  src/components/      # UI components (shadcn + custom dashboard cards)
  src/hooks/           # use-auth, use-polling, use-user-filter
  src/lib/             # api-client, types, format, constants
```

## Auth y seguridad

- **Google OAuth**: Login con cuenta Google (solo cuentas vinculadas en DB)
- **Usuario/contrasena**: Login con bcrypt hash, lockout por IP (10 intentos, 5min)
- **Registro cerrado**: `REGISTRO_ABIERTO=false` por defecto. Solo con codigo de invitacion.
- **Cookies**: HttpOnly + SameSite=Lax, 24h expiry
- **Aislamiento**: Datos filtrados por grupo_id. Usuario solo ve datos de su grupo.
- **Audit log**: Toda operacion CRUD de movimientos queda registrada.
- **Ownership**: PATCH/DELETE valida que el registro pertenezca al usuario logueado.

## Inteligencia financiera

**Score de salud (8 criterios, 100 pts):**
1. Gastos controlados <90% ingreso (15 pts)
2. Fondo de emergencia >=3 meses gastos fijos (15 pts)
3. Deuda saludable <30% ingreso anual (15 pts)
4. Presupuestos cumplidos >=80% (10 pts)
5. Uso de credito <50% cupo TC (10 pts)
6. Ingreso diversificado >=2 fuentes (10 pts)
7. Tendencia de gasto <= promedio 3 meses (15 pts)
8. Consistencia de registro >=15/mes (10 pts)

**Alertas (8 tipos):** presupuesto, pago_tarjeta, deuda_vencida, gasto_inusual, tendencia_alcista, ingreso_no_recibido, cupo_tc_bajo, oportunidad_ahorro

## Variables de entorno (.env)

```bash
DATABASE_URL=postgresql+psycopg://...
GROQ_API_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:3000/api/oauth/google/callback
REGISTRO_ABIERTO=false  # true para permitir registro sin invitacion
```

## Reglas del proyecto

- **Solo PostgreSQL.** No usar SQLite en ningun contexto.
- **COP siempre.** No multi-moneda.
- **Montos en INTEGER** (sin decimales, COP no tiene centavos relevantes).
- **Timezone Bogota** (America/Bogota) para todas las fechas.
- **Soft delete** en movimientos (columna `eliminado_en`).
- **Audit log** en toda operacion CRUD de movimientos.
- **Tests** deben correr contra PostgreSQL, no SQLite.

## Pendiente

- Migrar sesiones de memoria a Redis (Sprint 3 incompleto)
- Rate limiting en endpoints sensibles (register, cambiar-password, grupo/invitar)
- Tests E2E actualizados para nuevo layout

## Skills disponibles

Usa `/nombre-del-skill` para invocar contexto especializado:

### Desarrollo
- `/db` — Esquema PostgreSQL, Alembic, SQLAlchemy patterns
- `/qa` — QA Automation con Playwright, E2E tests
- `/admin` — Panel admin, auth, CRUD, UI patterns
- `/testing` — Pytest con PostgreSQL SAVEPOINT, fixtures

### Diseno y arquitectura
- `/design` — UI/UX dark theme, dashboard, responsive
- `/architecture` — FastAPI + Docker Compose, estructura de servicios

### Seguridad
- `/security` — OWASP checklist, audit log, auth patterns

### Finanzas Colombia
- `/finanzas-co` — Contexto financiero colombiano completo
- `/presupuesto` — Regla 50/30/20 adaptada a Colombia
- `/ahorro` — Estrategias ahorro/inversion Colombia
- `/impuestos` — DIAN, retencion, declaracion de renta
- `/mercado` — Tasas de usura, BanRep, coyuntura

### Orquestacion
- `/sprint` — Planificador de sprints
