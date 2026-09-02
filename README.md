# Finanzas Personales - Bot WhatsApp

Sistema de finanzas personales que registra gastos e ingresos en COP via WhatsApp (texto y audio), con dashboard web en tiempo real.

## Stack

| Componente | Tecnologia |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js 16 + React + TailwindCSS + Shadcn/ui + Recharts |
| Base de datos | PostgreSQL 15 |
| WhatsApp | Evolution API v2.3.7 (Baileys) |
| Transcripcion | Groq API (Whisper large-v3-turbo) |
| Parser IA | Groq (Llama 3.3 70B) + regex fallback |
| Auth | Cookies HttpOnly + TOTP 2FA |
| Orquestacion | Docker Compose (5 servicios) |

## Funcionalidades

- **Registro por WhatsApp**: texto libre ("gaste 15 mil en uber") o notas de voz
- **Parser inteligente**: Groq LLM como primario, regex como fallback
- **17 categorias**: Mercado, Transporte, Hogar, Suscripciones, Tarjeta, etc.
- **Dashboard**: KPIs, graficos por categoria, donut, tendencia mensual
- **Presupuestos**: limites por categoria con barras de progreso
- **Gastos compartidos**: balance automatico entre 2 usuarios (Day-Nico)
- **Cuotas TDC**: tracking de compras a cuotas con saldo pendiente
- **Gastos fijos**: recurrentes mensuales con compartido
- **Deudas**: tracking de prestamos y tarjetas
- **Soft delete + Audit log**: integridad de datos completa
- **2FA TOTP**: compatible con Apple Passwords, Google Authenticator
- **Auto-refresh**: datos en tiempo real cada 5 segundos
- **Mobile responsive**: funciona en desktop, tablet y celular

## Inicio rapido

### Requisitos
- Docker Desktop
- Git

### Instalacion

```bash
git clone <repo-url> finanzas_personales
cd finanzas_personales
cp .env.example .env
# Editar .env con tus credenciales
docker compose up -d
```

### URLs
- **Frontend**: http://localhost:3000
- **Admin (legacy)**: http://localhost:8000/admin
- **WhatsApp QR**: http://localhost:8000/whatsapp/qr

### Configuracion (.env)

```env
DATABASE_URL=postgresql+psycopg://evolution:evolution@localhost:5433/finanzas
AUTHORIZED_USERS=Nico:573001112233,Pareja:573004445566
EVOLUTION_API_KEY=tu_api_key
ADMIN_USER=admin
ADMIN_PASSWORD=tu_password_seguro
ADMIN_TOTP_SECRET=  # Generar en /admin/totp-setup
GROQ_API_KEY=tu_groq_key  # https://console.groq.com/keys
```

## Arquitectura

```
WhatsApp --> Evolution API (Docker :8080)
                |
            Webhook POST
                |
            FastAPI Backend (Docker :8000)
            /          |          \
        Parser      Comandos    Transcripcion
        (LLM+regex)  (CRUD)     (Groq Whisper)
            \          |          /
            PostgreSQL (Docker :5433)
                |
        Next.js Frontend (Docker :3000)
```

## Estructura del proyecto

```
finanzas_personales/
  backend/
    main.py              # FastAPI + webhooks
    config.py             # Settings desde .env
    admin/                # Panel admin + auth cookies + TOTP
    db/                   # Models, session, migrations Alembic
    parser/               # LLM + regex + categorias + numeros hablados
    services/             # Logica: registro, comandos, presupuesto, balance, cuotas, audit
    transcription/        # Groq Whisper client
    webhook/              # Evolution API client, sender, media
    tests/                # 82 tests con PostgreSQL SAVEPOINT
  frontend/
    src/app/              # 9 paginas Next.js (dashboard, movimientos, cuotas, etc.)
    src/components/       # Dashboard charts, layout, shadcn UI
    src/lib/              # Types, API client, format helpers
  .claude/commands/       # 14 skills de Claude Code
  docs/                   # Plan de proyecto
  docker-compose.yml      # 5 servicios: backend, frontend, postgres, evolution, redis
```

## Comandos utiles

```bash
# Levantar todo
docker compose up -d

# Rebuild despues de cambios
docker compose build backend frontend && docker compose up -d

# Logs
docker compose logs backend --tail 30

# Tests (requiere Postgres corriendo)
cd backend && python -m pytest tests/ -q

# Migraciones
cd backend && alembic upgrade head
```

## Licencia

Proyecto personal. No distribuir.
