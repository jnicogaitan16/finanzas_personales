# Finanzas Personales - Dashboard Web

Sistema de finanzas personales con dashboard web tipo app movil para registrar gastos, ingresos y gestionar tarjetas de credito en COP.

## Stack

| Componente | Tecnologia |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js 16 + React + TailwindCSS + Shadcn/ui + Recharts |
| Base de datos | PostgreSQL 15 |
| Parser IA | Groq (Llama 3.3 70B) + regex fallback |
| Auth | Cookies HttpOnly + bcrypt (por usuario) |
| Orquestacion | Docker Compose (4 servicios) |
| PWA | Instalable en celular (manifest.json + standalone) |

## Funcionalidades

### Finanzas
- **Registro de gastos** con categorias, medio de pago y compartido
- **Tarjetas de credito**: crear tarjetas con fecha corte/pago, vincular compras diferidas, proyeccion de cuotas a 6 meses
- **Ingresos**: fijos (auto-registrados mensualmente) y variables/bonos puntuales
- **Presupuestos**: limites por categoria con alertas al 80%+
- **Gastos compartidos**: balance automatico entre miembros del hogar
- **Cuotas TDC**: tracking de compras a cuotas con progreso y saldo
- **Gastos fijos**: recurrentes mensuales
- **Deudas**: tracking de prestamos y tarjetas

### Inteligencia financiera
- **Flujo de caja**: ingresos - fijos - cuotas - gasto flexible = disponible
- **Score de salud financiera** (0-100) con 4 criterios evaluados
- **Alertas automaticas**: presupuesto al limite, pago proximo de tarjeta, deudas vencidas
- **Proyeccion al cierre**: estimacion de gasto/ingreso mensual
- **Deteccion de anomalias**: gastos que superan 2x el promedio historico

### Usuarios y seguridad
- **Auth por usuario**: cada persona tiene su login (usuario + contrasena bcrypt)
- **Grupos familiares**: vincular 2 usuarios por hogar con codigo de invitacion
- **Aislamiento de datos**: cada usuario/grupo solo ve su propia informacion
- **Codigo de invitacion**: 8 caracteres, expira en 24h, uso unico
- **Soft delete + Audit log**: integridad de datos completa

### UI/UX
- **Diseño tipo app movil**: sidebar lateral, FAB, cards con gradientes
- **PWA instalable**: agregar a pantalla de inicio en iOS/Android
- **Login limpio**: fondo blanco, estilo iOS, con opcion de registro
- **Dashboard**: KPIs coloridos, donut de categorias, tendencia, alertas
- **Skeleton loaders**: shimmer durante carga
- **Animaciones**: fade-in, stagger en cards, transiciones suaves
- **Responsive**: funciona en desktop, tablet y celular
- **Dark mode**: tema oscuro con acentos emerald

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
- **API**: http://localhost:8000/health

### Primer uso
1. Abre http://localhost:3000
2. Click "Registrate" → crea tu usuario con nombre y contrasena
3. Inicia sesion
4. Ve a "Mi cuenta" → genera un codigo de invitacion para tu pareja/familia
5. Tu pareja se registra con el codigo → quedan en el mismo grupo familiar

## Arquitectura

```
    Next.js Frontend (Docker :3000)
            |
        REST API
            |
    FastAPI Backend (Docker :8000)
        /          \
    Parser       Servicios
    (LLM+regex)  (CRUD + audit + inteligencia)
        \          /
    PostgreSQL (Docker :5433)
        |
    Redis (Docker :6379)
    (command state)
```

## Estructura del proyecto

```
finanzas_personales/
  backend/
    main.py              # FastAPI app
    config.py             # Settings desde .env
    admin/                # Auth (bcrypt), router con 40+ endpoints
    db/                   # Models (10 tablas), session, migrations Alembic
    parser/               # LLM + regex + categorias + numeros hablados
    services/             # Logica: registro, comandos, tarjetas, ingresos,
                          #   inteligencia, presupuesto, balance, cuotas, audit
    tests/                # 97 tests con PostgreSQL SAVEPOINT
  frontend/
    src/app/              # Paginas: dashboard, movimientos, tarjetas, ingresos,
                          #   cuotas, presupuestos, compartido, gastos-fijos,
                          #   categorias, cuenta, login
    src/components/       # Dashboard (KPIs, donut, score, alertas, cashflow),
                          #   layout (sidebar, topbar, fab, app-shell)
    src/lib/              # Types, API client, format helpers
  docs/                   # Plan de proyecto, deprecacion WhatsApp
  docker-compose.yml      # 4 servicios: backend, frontend, postgres, redis
```

## Modelo de datos

| Tabla | Descripcion |
|-------|-------------|
| `grupos` | Hogar familiar (max 2 miembros, codigo invitacion) |
| `users` | Usuarios con password_hash + grupo_id |
| `categorias` | 17 categorias (gasto/ingreso) |
| `movimientos` | Gastos e ingresos con soft delete |
| `tarjetas_credito` | Tarjetas con fecha corte/pago, tasa EA, cupo |
| `compras_cuotas` | Compras diferidas vinculadas a tarjeta |
| `ingresos_recurrentes` | Ingresos fijos/variables con frecuencia |
| `gastos_fijos` | Gastos recurrentes mensuales |
| `presupuestos` | Limites por categoria y mes |
| `deudas` | Prestamos y tarjetas |
| `audit_log` | Registro de cambios con JSON diffs |

## Comandos utiles

```bash
# Levantar todo
docker compose up -d

# Rebuild despues de cambios
docker compose build backend frontend && docker compose up -d

# Logs
docker compose logs backend --tail 30

# Tests (requiere Postgres corriendo en localhost:5433)
cd backend && python -m pytest tests/ -q

# Migraciones
cd backend && alembic upgrade head
```

## Licencia

Proyecto personal. No distribuir.
