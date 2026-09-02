# Finanzas Personales — Bot WhatsApp

Bot de finanzas personales por WhatsApp para registrar gastos e ingresos en COP (pesos colombianos). Proyecto personal para 2 usuarios (Nico y Daylyng) en Bogota, Colombia.

## Stack

- **Backend:** Python 3.12 + FastAPI + Uvicorn
- **DB:** PostgreSQL 15 (Docker, puerto host 5433) + SQLAlchemy 2.0 + Alembic
- **WhatsApp:** Evolution API v2.3.7 (Baileys, self-hosted Docker)
- **Transcripcion:** Groq API (Whisper large-v3-turbo)
- **Cache:** Redis 7 (para Evolution)
- **Admin:** HTML/JS vanilla, auth por cookies + TOTP 2FA
- **Orquestacion:** Docker Compose (backend + postgres + evolution + redis)
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

## Estructura clave

```
backend/
  main.py              # FastAPI app, webhooks
  config.py            # Pydantic settings desde .env
  tiempo.py            # Timezone Bogota
  admin/               # Panel web + auth cookies + TOTP
  db/                  # Models, session, migrations Alembic
  parser/              # Regex extractor, categorias, numeros hablados
  services/            # Logica: registro, comandos, admin CRUD, audit
  transcription/       # Groq Whisper client
  webhook/             # Evolution API client, sender, media
```

## Reglas del proyecto

- **Solo PostgreSQL.** No usar SQLite en ningun contexto.
- **COP siempre.** No multi-moneda.
- **Montos en INTEGER** (sin decimales, COP no tiene centavos relevantes).
- **Timezone Bogota** (America/Bogota) para todas las fechas.
- **Soft delete** en movimientos (columna `eliminado_en`).
- **Audit log** en toda operacion CRUD de movimientos.
- **Escapar HTML** en todo dato de usuario renderizado en admin.
- **Webhook verificado** con header apikey.
- **Tests** deben correr contra PostgreSQL, no SQLite.

## Plan del proyecto

Ver `docs/plan-proyecto-finanzas-whatsapp.md` para el roadmap completo, auditoria de seguridad, y estado de cada fase.

## Skills disponibles

Usa `/nombre-del-skill` para invocar contexto especializado:

### Desarrollo
- `/parser` — Reglas del parser de mensajes, regex, numeros hablados
- `/db` — Esquema PostgreSQL, Alembic, SQLAlchemy patterns
- `/qa` — QA Automation con Playwright, E2E tests, selectores del frontend
- `/webhook` — Evolution API, WhatsApp, media, sender
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
