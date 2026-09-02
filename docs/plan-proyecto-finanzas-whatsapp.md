# Plan de Trabajo — Bot de Finanzas Personales por WhatsApp

**Proyecto:** Registro y análisis de gastos personales vía WhatsApp (texto/audio) con dashboard en tiempo real
**Tipo:** Piloto personal (1-2 usuarios: tú y opcionalmente tu pareja)
**Moneda:** COP (pesos colombianos)
**Entorno de desarrollo:** Claude Code (plan Max)
**Última auditoría:** 2026-09-02

---

## 1. Resumen ejecutivo

Construir un sistema donde te envías a ti mismo (o tu pareja se envía) notas de texto o de voz por WhatsApp del estilo *"gasté 15.300 en almuerzo"*, y el sistema:

1. Recibe el mensaje.
2. Si es audio, lo transcribe (Groq/Whisper).
3. Extrae el valor, la categoría y una descripción usando LLM Groq (Llama 3.3 70B) con regex como fallback.
4. Guarda el registro en PostgreSQL (con soft delete y audit log).
5. Permite gestión CRUD vía frontend Next.js (dashboard, presupuestos, cuotas TDC, gastos compartidos, gastos fijos, deudas).
6. Soporta comandos básicos por WhatsApp: borrar, editar, listar, cambiar categoría.
7. **Próximo:** exportación CSV/PDF, proyecciones financieras, hardening de seguridad.

**No** se integra con banco, correo, SMS ni compras — la única fuente de verdad es lo que tú escribes o dices en el chat.

---

## 2. Estado actual del proyecto (auditoría 2026-09-02)

### Progreso por fases

| Fase | Estado | Detalle |
|------|--------|---------|
| **Fase 0** — Setup | **COMPLETA** | Estructura, Docker Compose (5 servicios), Alembic (4 migraciones), esquema DB |
| **Fase 1** — Registro por texto | **COMPLETA** | Webhook Evolution, parser regex, confirmación WhatsApp, 17 categorías, comandos (borrar/editar/listar) |
| **Fase 2** — Registro por audio | **COMPLETA** | Transcripción Groq/Whisper, mismo pipeline, límite 60s |
| **Fase 3** — Frontend Next.js + Dashboard | **COMPLETA** | Next.js 16 + TypeScript + TailwindCSS + Shadcn/ui + Recharts. Dashboard con KPIs, gráficos, filtros. CRUD completo. Login 2FA. Docker multi-stage build en puerto 3000 |
| **Fase 4** — Modelo enriquecido + Parser IA | **COMPLETA** | Parser LLM Groq (Llama 3.3 70B) + regex fallback. Presupuestos, cuotas TDC, gastos compartidos, gastos fijos, deudas. 7 modelos DB, 11 servicios |
| **Fase 5** — Seguridad | **COMPLETA** | Auth cookies HttpOnly + TOTP 2FA, audit_log, soft delete, webhook verificado, dedup mensajes, HTML escaping. Pendiente: .dockerignore, cambiar creds DB |
| **Fase 6** — Pendiente | **NO INICIADA** | Comandos WhatsApp avanzados, alertas presupuesto, resumen semanal, CI/CD, exportar datos |
| **Fase 7** — Skills Claude Code | **COMPLETA** | 14 skills creados en `.claude/commands/`, CLAUDE.md configurado |

### Funcionalidad implementada

- **Frontend Next.js** (`/`) en puerto 3000 — Dashboard con KPIs, gráficos por categoría, donut, tendencia 6 meses, filtros por usuario/mes
- **Panel admin legacy** (`/admin`) con HTML/JS vanilla — CRUD básico (reemplazado por frontend Next.js)
- **Parser dual**: LLM Groq (Llama 3.3 70B) como primario, regex como fallback
- **Sistema de comandos por WhatsApp**: `borra el último`, `actualiza uber a 15.000`, `últimos`, `categoría del último: Transporte`, `ayuda`
- **Normalización de números hablados**: "veinte mil" → 20000, "15mil" → 15000
- **Modelo enriquecido**: 7 tablas (users, categorias, movimientos, presupuestos, compras_cuotas, deudas, gastos_fijos, audit_log)
- **Gastos compartidos**: balance Nico-Day con cuotas mensuales recurrentes
- **Cuotas TDC**: CRUD completo, sincronización bidireccional con movimientos
- **Auth segura**: cookies HttpOnly + SameSite=strict + TOTP 2FA + sesiones con expiración
- **Auditoría**: tabla audit_log registra cada crear/editar/borrar con valores antes/después
- **Docker Compose**: 5 servicios (backend, postgres, evolution, redis, frontend)

---

## 3. Auditoría de seguridad

### Resueltos desde la última auditoría

| # | Hallazgo | Estado | Cómo se resolvió |
|---|----------|--------|------------------|
| ~~S2~~ | XSS almacenado en panel admin | **RESUELTO** | Helper `esc()` implementado en `index.html` para escapar HTML |
| ~~S3~~ | Webhook sin verificación | **RESUELTO** | Validación de header `apikey` o `Authorization: Bearer` + IP Docker network |
| ~~S7~~ | Sin CSRF en admin | **RESUELTO** | Auth migrada a cookies HttpOnly con SameSite=strict (CSRF mitigado) |

### CRÍTICO (pendiente)

| # | Hallazgo | Riesgo | Archivo | Remediación |
|---|----------|--------|---------|-------------|
| S1 | **Secretos reales en `.env`** | Las API keys quedan expuestas si el repo se comparte. `.gitignore` lo excluye pero no hay protección adicional. | `.env` | Rotar keys si el repo se publicó. Agregar pre-commit hook que bloquee `.env`. |
| S4 | **Credenciales de DB débiles** | `evolution:evolution` como user/password de PostgreSQL es trivial. | `docker-compose.yml`, `.env` | Usar contraseña generada aleatoriamente. Acción manual del usuario. |
| S5 | **Sin HTTPS** | Tráfico en texto plano HTTP. OK para uso local, riesgoso si se expone. | `docker-compose.yml` | Agregar reverse proxy (Caddy/nginx) con TLS si se expone fuera de localhost. |

### MEDIO (pendiente)

| # | Hallazgo | Riesgo | Remediación |
|---|----------|--------|-------------|
| S6 | **Sin rate limiting por IP** | Solo hay dedup de mensajes (500 IDs), pero sin límite por IP/usuario. | Agregar `slowapi` al menos en `/webhook/evolution` y `/admin/*`. |
| S8 | **Sin protección de fuerza bruta en login** | No hay lockout ni delay después de intentos fallidos de login. | Implementar delay exponencial o lockout temporal. |
| S14 | **Contraseña admin en texto plano** | `config.admin_password` se compara con `compare_digest` pero no se hashea. Si se lee la memoria del proceso, queda expuesta. | Hashear con bcrypt/argon2 y comparar contra el hash. |

### BAJO (pendiente)

| # | Hallazgo | Remediación |
|---|----------|-------------|
| ~~S10~~ | ~~Sin `.dockerignore`~~ | **RESUELTO** — `.dockerignore` existe en backend/ y frontend/ |
| S11 | Python local vs 3.12 en Docker | Alinear versiones |
| S12 | Evolution API v2.3.7 fija — puede tener CVEs | Actualizar periódicamente |
| S13 | Sin logging centralizado | Configurar logging con formato estructurado (JSON) |
| S15 | **Sin CSP headers** | Agregar Content-Security-Policy para reducir riesgo de XSS residual |

---

## 4. Auditoría de producto

### Resueltos desde la última auditoría

| # | Hallazgo | Estado | Cómo se resolvió |
|---|----------|--------|------------------|
| ~~P1~~ | Parser solo regex, sin IA | **RESUELTO** | Parser LLM Groq (Llama 3.3 70B) como primario, regex como fallback. Confianza 0.95 con LLM. |
| ~~P2~~ | Sin detección de duplicados | **RESUELTO** | Dedup por message_id con OrderedDict (500 IDs max, FIFO cleanup) |
| ~~P7~~ | Categoría "Otros" como cajón de sastre | **MEJORADO** | 17 categorías (vs 7 originales). LLM clasifica mejor que keywords. |

### Problemas funcionales (pendientes)

| # | Hallazgo | Impacto | Remediación |
|---|----------|---------|-------------|
| P3 | **Borrado inmediato sin confirmación** | `borra el último` elimina sin preguntar (ahora es soft delete, reversible desde frontend). | Menos urgente: soft delete permite restaurar desde frontend. |
| P4 | **Estado en memoria (no persistente)** | `_PENDIENTES` y `_numero_instancia` se pierden al reiniciar. | Guardar en Redis (ya disponible en el stack) o en DB. |

### Mejoras de UX pendientes

- Exportar datos (CSV/PDF) desde frontend
- Proyecciones financieras y detección de anomalías en frontend
- Soporte para fotos de recibos (OCR futuro)

---

## 5. Auditoría contable/financiera

### Resueltos desde la última auditoría

| # | Hallazgo | Estado | Cómo se resolvió |
|---|----------|--------|------------------|
| ~~C1~~ | Sin log de auditoría | **RESUELTO** | Tabla `audit_log` con accion, valores_anteriores/nuevos (JSON), origen, timestamp. Service `audit.py` con logging automático. |
| ~~C2~~ | Sin soft delete | **RESUELTO** | Columna `eliminado_en` en movimientos y compras_cuotas. Property `.eliminado`. Queries filtran eliminados. |
| ~~C3~~ | Presupuestos sin implementar | **RESUELTO** | Service `presupuesto.py` con CRUD, presupuesto_vs_real, alerta_presupuesto. Frontend con página dedicada y barras de progreso. |
| ~~C5~~ | Sin separación de medios de pago | **RESUELTO** | Campo `medio_pago` en movimientos. |
| ~~C6~~ | Sin manejo de gastos recurrentes | **RESUELTO** | Tabla `gastos_fijos` con CRUD, soporte compartido con porcentaje. |
| ~~C8~~ | Sin categoría de ahorro | **RESUELTO** | Categorías "Ahorro" y "Deuda" agregadas. Tabla `deudas` para tracking de préstamos. |

### Pendientes

| # | Hallazgo | Impacto | Remediación |
|---|----------|---------|-------------|
| C7 | **Fecha de gasto se asume como "hoy"** | Inherente al diseño. El parser detecta "hoy", "ayer", "anteayer" y fechas explícitas, pero si no se dice, asume hoy. | Documentar limitación. Corrección disponible vía comando de edición o desde frontend. |

---

## 6. Auditoría de sistema

| # | Hallazgo | Impacto | Estado | Remediación |
|---|----------|---------|--------|-------------|
| T1 | **Sin backups** | Si el volumen de Docker se corrompe, se pierden todos los datos. | Pendiente | Configurar pg_dump periódico (cron) a directorio externo o cloud storage. |
| T2 | **Sin monitoreo** | No hay alertas si el bot deja de funcionar. Health check básico existe (`/health`). | Parcial | Agregar `/health/full` que verifique DB + Evolution + Redis. Uptime monitor externo. |
| T3 | **Redis no utilizado por la app** | Redis solo lo usa Evolution. La app podría usarlo para `_PENDIENTES`, rate limiting. | Pendiente | Evaluar migrar estado en memoria a Redis. |
| T4 | **Sin CI/CD** | No hay pipeline de tests automáticos ni deploy. | Pendiente | Agregar GitHub Actions para correr tests en PR. |
| T5 | **Alembic corre en CMD del Dockerfile** | Si la migración falla, el container se cae. | Pendiente | Separar migración del startup con init script. |
| ~~T6~~ | ~~Sin `.dockerignore`~~ | ~~Se copiaban archivos innecesarios al contenedor.~~ | **RESUELTO** | `.dockerignore` existe en backend/ y frontend/. |
| T7 | **Placeholders obsoletos** | `analytics/__init__.py` y `dashboard/app.py` son placeholders que ya no se usan (reemplazados por frontend Next.js). | Pendiente | Eliminar carpetas `analytics/` y `dashboard/`. |

---

## 7. Alcance

### WhatsApp — solo registro
WhatsApp es exclusivamente el canal de entrada para registrar gastos e ingresos por texto o audio. Opcionalmente permite actualizar valores con comandos básicos (borrar, editar, listar). **No se implementarán comandos avanzados** (consultas de balance, presupuestos, resúmenes, alertas). Toda la gestión, análisis y visualización se hace desde el frontend Next.js.

### Dentro del alcance (implementado)
- Captura de gasto/ingreso por texto libre ("gasté 15.300 en el mercado").
- Captura por nota de voz (transcripción automática vía Groq/Whisper).
- Clasificación automática por categoría (LLM + regex), editable. 17 categorías.
- Comandos básicos WhatsApp: borrar, editar, listar, cambiar categoría, ayuda.
- Almacenamiento en PostgreSQL con migraciones Alembic, soft delete, audit log.
- Frontend Next.js con dashboard (KPIs, gráficos), CRUD completo, login 2FA.
- Presupuestos mensuales por categoría con barras de progreso.
- Gastos compartidos con balance entre usuarios.
- Compras a cuotas (TDC) con tracking de pagos.
- Gastos fijos recurrentes y deudas.
- Soporte para dos usuarios con datos separados.
- 14 skills de Claude Code para finanzas en Colombia.

### Dentro del alcance (pendiente)
- Exportación de datos (CSV/PDF) desde frontend.
- Proyecciones financieras y anomalías en frontend.
- Seguridad: hashear password, rate limiting, CSP headers.
- Infra: backups, CI/CD, logging estructurado.

### Fuera del alcance (explícitamente)
- Comandos WhatsApp avanzados (consultas, resúmenes, alertas por WhatsApp).
- Lectura de correos, SMS o notificaciones de compras.
- Conexión a cuentas bancarias o tarjetas.
- Multiusuario más allá de 2 personas.
- App móvil nativa.

---

## 8. Principios de diseño

1. **Privacidad primero**: la única fuente de datos es lo que el usuario escribe/dice voluntariamente.
2. **Simplicidad operativa**: piloto para 1-2 personas, Docker Compose todo-en-uno.
3. **Mantenibilidad**: código modular, tipado, con tests para parsing.
4. **COP siempre**: no se necesita multi-moneda.
5. **Auditable**: cada registro guarda el mensaje original. Agregar tabla de auditoría para ediciones/borrados.

---

## 9. Arquitectura actual

```
┌─────────────┐     texto/audio      ┌──────────────────┐
│  WhatsApp   │ ───────────────────▶ │  Evolution API    │
│ (Nico/Day)  │                      │  (Baileys v2.3.7) │
└─────────────┘                      └────────┬──────────┘
                                               │ webhook (apikey verificado)
                                               ▼
                                     ┌───────────────────┐
                                     │  FastAPI Backend   │
                                     │  :8000             │
                                     └────────┬──────────┘
                                               │
                              ┌────────────────┼────────────────┐
                              ▼                ▼                ▼
                    ┌─────────────┐  ┌──────────────┐  ┌───────────┐
                    │ ¿Audio?     │  │ ¿Comando?    │  │ Parser    │
                    │ → Groq API  │  │ → Ejecutar   │  │ LLM Groq  │
                    │   Whisper   │  │   CRUD       │  │ + Regex   │
                    └──────┬──────┘  └──────┬───────┘  └─────┬─────┘
                           │               │                │
                           └───────────────┴────────────────┘
                                           │
                                           ▼
                              ┌───────────────────────┐
                              │  PostgreSQL 15 (:5433) │
                              │  7 tablas + audit_log  │
                              └───────────┬───────────┘
                                          │
                     ┌────────────────────┼────────────────┐
                     ▼                    ▼                ▼
            ┌──────────────┐   ┌──────────────────┐  ┌──────────┐
            │ Admin legacy │   │ Frontend Next.js │  │ Redis 7  │
            │ (HTML/JS)    │   │ :3000            │  │ (Evol.)  │
            │ /admin       │   │ Dashboard+CRUD   │  │          │
            └──────────────┘   │ Login 2FA TOTP   │  └──────────┘
                               └──────────────────┘
```

---

## 10. Stack tecnológico

| Componente | Tecnología | Estado |
|---|---|---|
| Canal WhatsApp | Evolution API v2.3.7 (Baileys, self-hosted) | Implementado |
| Backend / webhook | Python 3.12 + FastAPI + Uvicorn | Implementado |
| Frontend / Dashboard | Next.js 16 + TypeScript + TailwindCSS + Shadcn/ui + Recharts | Implementado |
| Transcripción de audio | Groq API (Whisper large-v3-turbo) | Implementado |
| Extracción de datos | Groq LLM (Llama 3.3 70B) + regex fallback | Implementado |
| Base de datos | PostgreSQL 15 (Docker, puerto 5433) | Implementado |
| ORM | SQLAlchemy 2.0 + Alembic (4 migraciones) | Implementado |
| Cache | Redis 7 (para Evolution) | Implementado (no usado por la app) |
| Admin legacy | HTML/JS vanilla con cookies HttpOnly + TOTP 2FA | Implementado (reemplazado por frontend) |
| Auth | Cookies HttpOnly + SameSite=strict + TOTP 2FA (pyotp) | Implementado |
| Orquestación | Docker Compose (5 servicios: backend, postgres, evolution, redis, frontend) | Implementado |
| Tests | pytest contra PostgreSQL real con SAVEPOINT isolation | 13 archivos de tests |

---

## 11. Modelo de datos (8 tablas)

```sql
-- Usuarios (2: Nico y Day)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    numero_whatsapp TEXT UNIQUE NOT NULL
);

-- Categorías (17 predefinidas, editables)
CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    nombre TEXT UNIQUE NOT NULL,
    tipo TEXT CHECK(tipo IN ('gasto', 'ingreso')) DEFAULT 'gasto',
    es_fijo BOOLEAN DEFAULT FALSE
);

-- Registro de gastos/ingresos (tabla principal)
CREATE TABLE movimientos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    categoria_id INTEGER REFERENCES categorias(id),
    monto_cop INTEGER NOT NULL,
    descripcion TEXT,
    mensaje_original TEXT NOT NULL,
    fue_audio BOOLEAN DEFAULT FALSE,
    confianza_parsing REAL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_gasto DATE,
    eliminado_en TIMESTAMP,                -- soft delete
    es_compartido BOOLEAN DEFAULT FALSE,
    porcentaje_compartido INTEGER,
    medio_pago TEXT,                        -- efectivo, nequi, TDC, etc.
    compra_cuotas_id INTEGER REFERENCES compras_cuotas(id)
);

-- Presupuestos mensuales por categoría
CREATE TABLE presupuestos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    categoria_id INTEGER REFERENCES categorias(id),
    monto_limite_cop INTEGER NOT NULL,
    mes_vigente TEXT,                       -- 'YYYY-MM'
    UNIQUE (user_id, categoria_id, mes_vigente)
);

-- Compras a cuotas (tarjeta de crédito)
CREATE TABLE compras_cuotas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    fecha_compra DATE,
    establecimiento TEXT,
    descripcion TEXT,
    valor_total_cop INTEGER,
    num_cuotas INTEGER,
    cuotas_pagadas INTEGER DEFAULT 0,
    valor_cuota_cop INTEGER,
    valor_intereses_cop INTEGER DEFAULT 0,
    tasa_ea REAL,
    numero_transaccion TEXT,
    tarjeta TEXT,
    saldo_pendiente_cop INTEGER,
    liquidada BOOLEAN DEFAULT FALSE,
    fecha_ultima_cuota DATE,
    eliminado_en TIMESTAMP                 -- soft delete
);

-- Deudas (personal, tarjeta, crédito)
CREATE TABLE deudas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    nombre TEXT NOT NULL,
    tipo TEXT CHECK(tipo IN ('personal', 'tarjeta', 'credito')),
    acreedor TEXT,
    monto_original_cop INTEGER,
    saldo_cop INTEGER,
    cuota_mensual_cop INTEGER,
    tasa_ea REAL,
    activa BOOLEAN DEFAULT TRUE,
    fecha_inicio DATE,
    fecha_limite DATE,
    notas TEXT
);

-- Gastos fijos recurrentes (arriendo, servicios, suscripciones)
CREATE TABLE gastos_fijos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    categoria_id INTEGER REFERENCES categorias(id),
    nombre TEXT NOT NULL,
    monto_cop INTEGER NOT NULL,
    es_compartido BOOLEAN DEFAULT FALSE,
    porcentaje_compartido INTEGER,
    activo BOOLEAN DEFAULT TRUE,
    dia_esperado INTEGER,
    UNIQUE (user_id, nombre)
);

-- Auditoría de cambios (cada crear/editar/borrar)
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    tabla TEXT NOT NULL,
    registro_id INTEGER NOT NULL,
    accion TEXT NOT NULL,              -- 'crear', 'editar', 'borrar'
    valores_anteriores JSON,
    valores_nuevos JSON,
    origen TEXT DEFAULT 'whatsapp',    -- 'whatsapp', 'admin'
    user_id INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Migraciones Alembic (4)

| # | Migración | Contenido |
|---|-----------|-----------|
| 001 | `initial_schema` | users, categorias, movimientos, presupuestos + 15 categorías seed |
| 002 | `audit_log` | Tabla audit_log con JSON + índice (tabla, registro_id) |
| 003 | `soft_delete` | Columna `eliminado_en` en movimientos |
| 004 | `enhanced_model` | compras_cuotas, deudas, gastos_fijos + es_fijo, compartido, medio_pago + 10 categorías nuevas |

---

## 12. Roadmap actualizado

### Fase 3 — Frontend Next.js + Dashboard (COMPLETADA 2026-09-01)
- [x] Frontend Next.js 16 con TypeScript, TailwindCSS, Shadcn/ui, Recharts
- [x] App separada en puerto 3000, proxy pattern (zero CORS)
- [x] Dashboard con KPIs, barras por categoría, donut, tendencia 6 meses
- [x] Filtros por usuario y mes con navegación
- [x] CRUD completo: movimientos, categorías, usuarios
- [x] Login con 2FA TOTP
- [x] Header responsive con auto-hide al scroll
- [x] Auto-refresh cada 5 segundos
- [x] Docker multi-stage build

### Fase 4 — Modelo enriquecido + Parser IA (COMPLETADA 2026-09-01)
- [x] Parser LLM con Groq (Llama 3.3 70B) como primario, regex como fallback
- [x] 10 categorías nuevas (17 total): Hogar, Seguridad Social, Administración, Suscripciones, Tarjeta, Celular, GYM, Ahorro, Deuda, Freelance
- [x] Presupuestos: CRUD + budget vs actual + barras de progreso
- [x] Gastos compartidos: balance Day-Nico con cuotas mensuales recurrentes
- [x] Cuotas TDC: CRUD completo, sincronización bidireccional con movimientos
- [x] Gastos fijos: CRUD con compartido y porcentaje
- [x] Deudas: CRUD (personal, tarjeta, crédito)
- [x] Columnas nuevas: medio_pago, es_compartido, porcentaje_compartido, compra_cuotas_id
- [x] Soft delete cascading (movimiento → cuota vinculada)
- [x] Frontend: 4 páginas nuevas (presupuestos, compartido, cuotas, gastos-fijos)

### Fase 5 — Seguridad (COMPLETADA 2026-09-01)
- [x] Escapar HTML en admin (XSS)
- [x] Verificar firma de webhook Evolution
- [x] Endpoints protegidos con auth
- [x] Tabla audit_log con logging automático
- [x] Detección de duplicados en webhook
- [x] Auth migrada a cookies HttpOnly + 2FA TOTP
- [x] Login/Logout con página dedicada
- [x] Soft delete para movimientos y cuotas
- [x] `.dockerignore` en backend y frontend
- [ ] Cambiar credenciales DB (S4) — acción manual del usuario
- [ ] Hashear contraseña admin (S14) — actualmente plaintext con compare_digest

### Fase 6 — Limpieza, seguridad e infraestructura (EN PROGRESO)
- [x] Limpiar placeholders obsoletos (`analytics/`, `dashboard/`)
- [x] Hashear contraseña admin con bcrypt (`ADMIN_PASSWORD_HASH`)
- [x] Rate limiting por IP (slowapi: webhook 30/min, login 5/min)
- [x] CSP + security headers (X-Content-Type-Options, X-Frame-Options, CSP)
- [x] Protección fuerza bruta en login (lockout 5min tras 10 intentos)
- [x] Backups automáticos (pg_dump cada 12h, retención 7 días, servicio `db-backup`)
- [x] Migrar `_PENDIENTES` y `_MSG_IDS` a Redis (fallback in-memory si Redis no disponible)
- [x] CI/CD (GitHub Actions: pytest + PostgreSQL en PRs)
- [x] Logging estructurado JSON (`logging_config.py`)
- [x] Tests E2E frontend con Playwright (24 tests, skill `/qa`)
- [x] Exportar datos CSV desde frontend (botón en movimientos + endpoint backend)
- [x] Proyecciones financieras de cierre de mes (card en dashboard)
- [x] Detección de anomalías (gastos >2x promedio de categoría, card en dashboard)

### Fase 7 — Skills Claude Code y MCP (COMPLETADA 2026-09-01)
- [x] 14 skills creados (.claude/commands/) + skill `/qa`
- [x] CLAUDE.md con contexto del proyecto
- [ ] MCP a la base de datos (evaluado, pendiente implementar)

### Fase 8 — Deploy a producción (EN PROGRESO)
- [x] Rama `dev` creada y protegida (requiere PR + CI)
- [x] Pipelines CI independientes para dev y main
- [x] Pipeline deploy automático a Oracle Cloud via SSH
- [x] docker-compose.prod.yml con Caddy (HTTPS automático)
- [x] Guía de deploy Oracle Cloud Free Tier (`docs/deploy-oracle-cloud.md`)
- [x] .env.production.example con todas las variables
- [x] Script de setup del server (`scripts/server-setup.sh`)
- [ ] Crear VM en Oracle Cloud (acción manual del usuario)
- [ ] Configurar dominio (DuckDNS o propio)
- [ ] Configurar GitHub Secrets (DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY)
- [ ] Primer deploy a producción

---

## 13. Seguridad y privacidad

- El bot **solo** procesa mensajes de los números de WhatsApp registrados en `users`. Todo lo demás se descarta sin guardar.
- No se accede a correo, SMS ni historial de compras bajo ninguna circunstancia.
- Las credenciales van en `.env`, nunca en el código. `.env` está en `.gitignore`.
- La base de datos vive en Docker local, sin exponer puertos al exterior.
- Admin protegido con cookies de sesión HttpOnly + 2FA TOTP.
- Login/Logout dedicado, sin HTTP Basic Auth.
- Webhook verificado con apikey, detección de duplicados por message_id.
- Tabla audit_log registra cada creación, edición y borrado de movimientos.
- El mensaje original se guarda para auditoría de interpretaciones.

---

## 14. Skills para Claude Code

Skills diseñados para trabajar el proyecto y tomar mejores decisiones financieras en Colombia:

### Skills de desarrollo del proyecto

1. **`finanzas-parser`** — Reglas y ejemplos del parser de mensajes en español colombiano. Cómo funciona la extracción de montos ("15mil", "quince mil", "$15.300"), categorización por keywords, y normalización de números hablados. Útil para debuggear el parser o agregar nuevas reglas.

2. **`finanzas-db`** — Esquema de DB, convenciones de Alembic, relaciones entre tablas. Cómo crear migraciones, seed data, y la lógica de los servicios CRUD.

3. **`finanzas-webhook`** — Cómo funciona la integración con Evolution API (Baileys), el flujo del webhook, extracción de mensajes, descarga de audio, envío de respuestas. Debugging de problemas de conexión WhatsApp.

4. **`finanzas-admin`** — Estructura del panel admin, API endpoints, autenticación, y cómo extender la UI.

### Skills de estrategia financiera (Colombia)

5. **`finanzas-colombia`** — Contexto financiero colombiano para dar recomendaciones informadas:
   - **Impuestos**: Retención en la fuente, declaración de renta (umbral ~$65M anuales en 2026), IVA 19%, GMF 4x1000.
   - **Productos de ahorro**: CDTs (tasas actuales vs inflación), cuentas de ahorro AFC (beneficio tributario), FICs (fondos de inversión colectiva).
   - **Medios de pago**: Nequi, Daviplata, PSE, tarjetas de crédito (cuotas sin interés, millas), efectivo.
   - **Referencias de costo de vida Bogotá 2026**: Arriendo promedio (estrato 3-4: $1.2-2.5M), mercado mensual ($400-800K), transporte SITP/TransMilenio ($2.950/pasaje), servicios públicos ($150-400K).
   - **Inflación y poder adquisitivo**: IPC acumulado, SMLV 2026, UVR.

6. **`finanzas-presupuesto-50-30-20`** — Implementación de la regla 50/30/20 adaptada a Colombia:
   - 50% necesidades (arriendo, servicios, mercado, transporte, salud)
   - 30% deseos (ocio, restaurantes, suscripciones, ropa)
   - 20% ahorro/inversión/deudas
   - Cómo categorizar los movimientos del bot en estos tres buckets.
   - Alertas cuando un bucket se desborda.

7. **`finanzas-deudas`** — Estrategias para manejo de deudas en Colombia:
   - Método avalancha vs bola de nieve
   - Tasas de usura vigentes (Superfinanciera)
   - Compra de cartera
   - Cómo registrar pagos de deuda como categoría especial

8. **`finanzas-ahorro-inversion`** — Guía para decisiones de ahorro e inversión desde los datos del bot:
   - Fondo de emergencia (3-6 meses de gastos según los datos reales)
   - CDTs vs FICs vs ETFs (a]2, Trii, Tyba, Mercadolibre Fondos)
   - Pensiones voluntarias (beneficio tributario)
   - Cesantías y prima (cómo planificar el uso)

9. **`finanzas-impuestos-co`** — Asistente para la declaración de renta:
   - Cómo los datos del bot ayudan a rastrear deducciones
   - Gastos deducibles: salud (medicina prepagada), educación, intereses hipotecarios, AFC
   - Calendario tributario DIAN
   - Cuándo conviene declarar voluntariamente

10. **`finanzas-metas`** — Definición y seguimiento de metas financieras:
    - Metas de ahorro con deadline (vacaciones, carro, apartamento)
    - Tracking de progreso desde los datos de ingresos/gastos del bot
    - Cuánto necesitas ahorrar por mes para alcanzar la meta

---

## 15. MCP a la base de datos — Evaluación

### ¿Qué es un MCP de base de datos?
Un MCP (Model Context Protocol) server para PostgreSQL permitiría que Claude Code consulte directamente la DB del proyecto durante las conversaciones de desarrollo. En vez de correr queries manualmente, Claude podría:

- Inspeccionar el esquema actual
- Ver datos de ejemplo para debuggear el parser
- Verificar que las migraciones se aplicaron correctamente
- Analizar distribución de gastos por categoría
- Detectar anomalías en los datos

### Recomendación: SÍ, pero con precauciones

**Ventajas:**
- Acelera el desarrollo — no necesitas copiar/pegar resultados de queries
- Permite análisis exploratorio directo durante sesiones de Claude Code
- Útil para debugging ("¿por qué este mensaje no se parseó bien?")
- Puede alimentar los skills de analítica financiera

**Precauciones:**
- **Solo READ** — el MCP debe tener acceso de solo lectura a la DB. Nunca permitir INSERT/UPDATE/DELETE desde Claude.
- **Usuario de DB separado** — crear un usuario `readonly` con `GRANT SELECT ON ALL TABLES`.
- **No exponer fuera de localhost** — el MCP server solo debe ser accesible localmente.
- **Datos sensibles** — la DB contiene números de teléfono y patrones de gasto. Considerar si esto es aceptable en el contexto de Claude Code (los datos salen al API de Anthropic).

### Implementación sugerida

```json
// .claude/settings.json
{
  "mcpServers": {
    "finanzas-db": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic/mcp-server-postgres",
        "postgresql://readonly:readonly_password@localhost:5433/finanzas"
      ]
    }
  }
}
```

Para análisis sin datos sensibles:
```bash
pg_dump -h localhost -p 5433 -U evolution finanzas \
  --exclude-table=users > finanzas_snapshot.sql
```

---

## 16. Estructura de carpetas actual

```
finanzas_personales/
├── .env                    # Secretos (NO commitear)
├── .env.example            # Template de configuración
├── .gitignore
├── docker-compose.yml      # 5 servicios: backend + postgres + evolution + redis + frontend
├── CLAUDE.md               # Instrucciones para Claude Code
│
├── backend/
│   ├── Dockerfile
│   ├── main.py             # FastAPI app (177 líneas) — webhooks, health, QR
│   ├── config.py           # Pydantic settings (12 keys)
│   ├── tiempo.py           # Timezone Bogotá
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── admin/
│   │   ├── auth.py         # Cookies HttpOnly + TOTP 2FA + sesiones
│   │   ├── router.py       # CRUD endpoints admin (600+ líneas)
│   │   ├── index.html      # Panel admin legacy (dark theme)
│   │   └── login.html      # Página de login dedicada
│   ├── db/
│   │   ├── models.py       # 8 modelos SQLAlchemy (241 líneas)
│   │   ├── session.py      # Engine y session factory
│   │   ├── seed.py         # 17 categorías iniciales
│   │   ├── users_seed.py   # Seed de usuarios desde .env
│   │   └── migrations/
│   │       ├── env.py
│   │       └── versions/
│   │           ├── 001_initial_schema.py
│   │           ├── 002_audit_log.py
│   │           ├── 003_soft_delete.py
│   │           └── 004_enhanced_model.py
│   ├── parser/
│   │   ├── extractor.py    # Punto de entrada (LLM → regex fallback)
│   │   ├── llm.py          # Parser Groq LLM (Llama 3.3 70B)
│   │   ├── fallback_regex.py  # Parser regex (fallback)
│   │   ├── categorias.py   # 17 categorías con keywords
│   │   ├── mensajes.py     # Formato de respuestas WhatsApp
│   │   ├── numeros_hablados.py  # "veinte mil" → 20000
│   │   └── schemas.py      # Dataclass Extraccion
│   ├── services/
│   │   ├── admin.py        # CRUD admin con cascading y audit
│   │   ├── audio.py        # Orquestación de transcripción
│   │   ├── audit.py        # Logging a tabla audit_log
│   │   ├── balance.py      # Cálculo balance compartido Nico-Day
│   │   ├── comandos.py     # Sistema de comandos WhatsApp
│   │   ├── cuotas.py       # CRUD compras a cuotas TDC
│   │   ├── gastos_fijos.py # CRUD gastos fijos recurrentes
│   │   ├── presupuesto.py  # CRUD presupuestos + alertas
│   │   ├── registro.py     # Pipeline principal de registro
│   │   └── resultado.py    # Dataclass ResultadoRegistro
│   ├── transcription/
│   │   └── whisper_client.py  # Groq Whisper API
│   ├── webhook/
│   │   ├── client.py       # Cliente Evolution API
│   │   ├── evolution.py    # Parser de payloads Evolution
│   │   ├── media.py        # Descarga de audio
│   │   ├── qr_page.py      # HTML para escanear QR
│   │   └── sender.py       # Envío de mensajes WhatsApp
│   └── tests/
│       ├── conftest.py         # Fixtures PostgreSQL SAVEPOINT
│       ├── test_admin.py
│       ├── test_comandos.py    # (17KB, el más extenso)
│       ├── test_health.py
│       ├── test_mensajes.py
│       ├── test_migrations.py
│       ├── test_models.py
│       ├── test_numeros_hablados.py
│       ├── test_parser.py
│       ├── test_tiempo.py
│       ├── test_transcripcion.py
│       └── test_webhook.py
│
├── frontend/                # Next.js 16 + TypeScript + TailwindCSS
│   ├── Dockerfile           # Multi-stage build
│   ├── package.json
│   ├── next.config.ts
│   ├── components.json      # Shadcn/ui config
│   └── src/app/
│       ├── layout.tsx
│       ├── page.tsx          # Dashboard (KPIs, gráficos, tendencias)
│       ├── login/
│       ├── movimientos/
│       ├── categorias/
│       ├── usuarios/
│       ├── presupuestos/
│       ├── compartido/       # Balance gastos compartidos
│       ├── cuotas/           # Compras a cuotas TDC
│       ├── gastos-fijos/
│       └── api/              # Proxy routes al backend
│
├── .claude/
│   └── commands/            # 14 skills para Claude Code
│       ├── parser.md, db.md, webhook.md, admin.md, testing.md
│       ├── design.md, architecture.md, security.md
│       ├── finanzas-co.md, presupuesto.md, ahorro.md
│       ├── impuestos.md, mercado.md, sprint.md
│
├── analytics/               # OBSOLETO — placeholder vacío
│   └── __init__.py
├── dashboard/               # OBSOLETO — reemplazado por frontend/
│   └── app.py
├── docs/
│   └── plan-proyecto-finanzas-whatsapp.md
└── postgres/
    └── init-finanzas.sh     # Init script para crear DB finanzas
```

---

## 17. Prioridades de acción (actualizado 2026-09-02)

### ~~Sprint 1 — Seguridad~~ COMPLETADO
### ~~Sprint 2 — Integridad contable~~ COMPLETADO
### ~~Sprint 3 — Dashboard~~ COMPLETADO (Next.js)
### ~~Sprint 4 — Parser inteligente~~ COMPLETADO (Groq LLM)

### ~~Sprint 5 — Limpieza y seguridad~~ COMPLETADO
### ~~Sprint 6 — Infraestructura y calidad~~ COMPLETADO

### ~~Sprint 7 — Analítica y exportación~~ COMPLETADO

### Sprint 8 — Deploy a Oracle Cloud (PRÓXIMO)
1. Crear VM Oracle Cloud Free Tier (ARM 2 OCPU + 12GB)
2. Ejecutar `scripts/server-setup.sh`
3. Configurar `.env.production` con credenciales seguras
4. Configurar dominio (DuckDNS gratis)
5. `docker compose -f docker-compose.prod.yml up -d`
6. Configurar GitHub Secrets para deploy automático
4. MCP a la base de datos para Claude Code
