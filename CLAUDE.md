# Finanzas Personales — Dashboard Web

Dashboard web de finanzas personales para registrar gastos e ingresos en COP (pesos colombianos). Proyecto personal para 2 usuarios (Nico y Daylyng) en Bogota, Colombia.

## Stack

- **Backend:** Python 3.12 + FastAPI + Uvicorn
- **Frontend:** Next.js + React + TailwindCSS + Shadcn/ui + Recharts
- **DB:** PostgreSQL 15 (Docker, puerto host 5433) + SQLAlchemy 2.0 + Alembic
- **Parser IA:** Groq API (Llama 3.3 70B) + regex fallback
- **Cache:** Redis 7 (command state, deduplicacion)
- **Auth:** Cookies HttpOnly + TOTP 2FA
- **Orquestacion:** Docker Compose (backend + frontend + postgres + redis)
- **Tests:** pytest contra PostgreSQL real con SAVEPOINT isolation

## Comandos esenciales

```bash
# Levantar todo
docker compose up -d

# Rebuild backend despues de cambios
docker compose build backend && docker compose up -d backend

# Logs del backend
docker compose logs backend --tail 30

# Tests backend (requiere Postgres corriendo en localhost:5433)
cd backend && python -m pytest tests/ -q

# Tests E2E frontend (requiere stack completo corriendo)
cd frontend && npx playwright test

# Migraciones
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "descripcion"
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

## Estructura clave

```
backend/
  main.py              # FastAPI app, health endpoint
  config.py            # Pydantic settings desde .env
  tiempo.py            # Timezone Bogota
  admin/               # Panel web + auth cookies + TOTP
  db/                  # Models, session, migrations Alembic
  parser/              # LLM + regex extractor, categorias, numeros hablados
  services/            # Logica: registro, comandos, admin CRUD, audit
```

## Reglas del proyecto

- **Solo PostgreSQL.** No usar SQLite en ningun contexto.
- **COP siempre.** No multi-moneda.
- **Montos en INTEGER** (sin decimales, COP no tiene centavos relevantes).
- **Timezone Bogota** (America/Bogota) para todas las fechas.
- **Soft delete** en movimientos (columna `eliminado_en`).
- **Audit log** en toda operacion CRUD de movimientos.
- **Escapar HTML** en todo dato de usuario renderizado en admin.
- **Tests** deben correr contra PostgreSQL, no SQLite.

## Plan del proyecto

Ver `docs/plan-proyecto-finanzas-whatsapp.md` para el roadmap completo, auditoria de seguridad, y estado de cada fase.

## Skills disponibles

Usa `/nombre-del-skill` para invocar contexto especializado:

### Desarrollo
- `/parser` — Reglas del parser de mensajes, regex, numeros hablados
- `/db` — Esquema PostgreSQL, Alembic, SQLAlchemy patterns
- `/qa` — QA Automation con Playwright, E2E tests, selectores del frontend
- `/admin` — Panel admin, auth, CRUD, UI patterns
- `/testing` — Pytest con PostgreSQL SAVEPOINT, fixtures, patterns

### Diseno y arquitectura
- `/design` — UI/UX dark theme, Streamlit dashboard, responsive
- `/architecture` — FastAPI + Docker Compose, estructura de servicios

### Seguridad
- `/security` — OWASP checklist, audit log, auth patterns, vulnerabilidades

### Finanzas Colombia
- `/finanzas-co` — Contexto financiero colombiano completo
- `/presupuesto` — Regla 50/30/20 adaptada a Colombia
- `/ahorro` — Estrategias ahorro/inversion Colombia
- `/impuestos` — DIAN, retencion, declaracion de renta
- `/mercado` — Tasas de usura, intervencion BanRep, noticias financieras, coyuntura

### Orquestacion
- `/sprint` — Planificador de sprints, genera plan detallado con tareas
