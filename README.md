# Finanzas Personales - Dashboard Web

Sistema de finanzas personales con dashboard web tipo app movil para registrar gastos, ingresos y gestionar tarjetas de credito en COP.

## Stack

| Componente | Tecnologia |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js 16 + React + TailwindCSS + Shadcn/ui |
| Base de datos | PostgreSQL 15 + SQLAlchemy 2.0 + Alembic |
| Auth | Google OAuth + usuario/contrasena + cookies HttpOnly |
| Orquestacion | Docker Compose (5 servicios) |
| Deploy | Oracle Cloud Free Tier + Caddy HTTPS + GitHub Actions |

## Funcionalidades

### Finanzas
- **Registro de gastos** con categorias, medio de pago y compartido
- **Tarjetas de credito**: crear tarjetas con fecha corte/pago, vincular compras diferidas, proyeccion de cuotas a 6 meses
- **Ingresos**: fijos y variables con frecuencia configurable
- **Presupuestos**: limites por categoria con alertas al 80%+
- **Gastos compartidos**: balance automatico entre miembros del hogar
- **Cuotas TDC**: tracking de compras a cuotas con progreso y saldo
- **Gastos fijos**: recurrentes mensuales
- **Deudas**: tracking de prestamos y tarjetas
- **Metas de ahorro**: objetivos con barra de progreso y fecha limite

### Inteligencia financiera
- **Flujo de caja**: ingresos - fijos - cuotas - gasto flexible = disponible
- **Score de salud financiera** (0-100) con 8 criterios ponderados
- **8 tipos de alertas**: presupuesto al limite, pago proximo de tarjeta, deudas vencidas, gasto inusual, tendencia alcista, ingreso no recibido, cupo TC bajo, oportunidad de ahorro

### Usuarios y seguridad
- **Google OAuth**: login con cuenta Google (solo cuentas autorizadas)
- **Login clasico**: usuario + contrasena con bcrypt
- **Registro cerrado**: solo con codigo de invitacion
- **Grupos familiares**: vincular 2 usuarios por hogar
- **Aislamiento de datos**: cada grupo solo ve su propia informacion
- **Soft delete + Audit log**: integridad de datos completa

### UI/UX
- **Tema purpura oscuro**: sin sidebar, navegacion por cards en dashboard
- **Responsive**: funciona en desktop, tablet y celular
- **Skeleton loaders**: shimmer durante carga
- **Animaciones**: fade-in, stagger en cards, transiciones suaves

## Inicio rapido

### Requisitos
- Docker Desktop
- Git

### Instalacion

```bash
git clone <repo-url> finanzas_personales
cd finanzas_personales
cp .env.example .env
# Editar .env con tus credenciales (Google OAuth, Groq, etc.)
docker compose up -d
```

### URLs
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000/health

## Arquitectura

```
    Next.js Frontend (Docker :3000)
            |
        REST API (proxy)
            |
    FastAPI Backend (Docker :8000)
            |
        Servicios (CRUD + audit + inteligencia)
            |
    PostgreSQL (Docker :5433)

    Caddy (prod: HTTPS reverse proxy :80/:443)
```

## Modelo de datos (12 tablas)

| Tabla | Descripcion |
|-------|-------------|
| `grupos` | Hogar familiar (max 2 miembros, codigo invitacion) |
| `users` | Usuarios con password_hash, email, google_id, grupo_id |
| `categorias` | Categorias (gasto/ingreso) |
| `movimientos` | Gastos e ingresos con soft delete |
| `tarjetas_credito` | Tarjetas con fecha corte/pago, tasa EA, cupo |
| `compras_cuotas` | Compras diferidas vinculadas a tarjeta |
| `ingresos_recurrentes` | Ingresos fijos/variables con frecuencia |
| `gastos_fijos` | Gastos recurrentes mensuales |
| `presupuestos` | Limites por categoria y mes |
| `deudas` | Prestamos y tarjetas |
| `metas_ahorro` | Objetivos de ahorro con progreso |
| `audit_log` | Registro de cambios con JSON diffs |

## Comandos utiles

```bash
# Levantar todo
docker compose up -d

# Rebuild despues de cambios
docker compose build backend frontend && docker compose up -d

# Logs
docker compose logs backend --tail 30

# Tests
docker cp backend/tests finanzas-personales-backend-1:/app/tests
docker compose exec backend python -m pytest tests/ -q

# Migraciones
docker compose exec backend alembic upgrade head
```

## Deploy

Deploy automatico a Oracle Cloud Free Tier al mergear a `main`. Ver `docs/deploy-oracle-cloud.md`.

## Licencia

Proyecto personal. No distribuir.
