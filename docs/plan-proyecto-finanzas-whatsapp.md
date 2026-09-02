# Plan de Trabajo — Bot de Finanzas Personales por WhatsApp

**Proyecto:** Registro y análisis de gastos personales vía WhatsApp (texto/audio) con dashboard en tiempo real
**Tipo:** Piloto personal (1-2 usuarios: tú y opcionalmente tu pareja)
**Moneda:** COP (pesos colombianos)
**Entorno de desarrollo:** Claude Code (plan Max)
**Última auditoría:** 2026-09-01

---

## 1. Resumen ejecutivo

Construir un sistema donde te envías a ti mismo (o tu pareja se envía) notas de texto o de voz por WhatsApp del estilo *"gasté 15.300 en almuerzo"*, y el sistema:

1. Recibe el mensaje.
2. Si es audio, lo transcribe (Groq/Whisper).
3. Extrae el valor, la categoría y una descripción usando regex (con plan de integrar IA).
4. Guarda el registro en PostgreSQL.
5. Permite gestión CRUD vía panel admin web.
6. Soporta comandos por WhatsApp: borrar, editar, listar, cambiar categoría.
7. **Próximo:** dashboard con gráficos, analítica, presupuestos y recomendaciones.

**No** se integra con banco, correo, SMS ni compras — la única fuente de verdad es lo que tú escribes o dices en el chat.

---

## 2. Estado actual del proyecto (auditoría 2026-09-01)

### Progreso por fases

| Fase | Estado | Detalle |
|------|--------|---------|
| **Fase 0** — Setup | **COMPLETA** | Estructura, Docker Compose (backend + Postgres + Evolution + Redis), Alembic, esquema DB |
| **Fase 1** — Registro por texto | **COMPLETA** | Webhook Evolution, parser regex, confirmación WhatsApp, categorías, comandos (borrar/editar/listar) |
| **Fase 2** — Registro por audio | **COMPLETA** | Transcripción Groq/Whisper, mismo pipeline, límite 60s |
| **Fase 3** — Dashboard y analítica | **NO INICIADA** | `dashboard/app.py` es placeholder, `analytics/` solo tiene `__init__.py` |
| **Fase 4** — Presupuestos | **PARCIAL** | Tabla `presupuestos` existe en DB pero no hay lógica que la use |
| **Fase 5** — Skills Claude Code | **NO INICIADA** | No hay skills creados |

### Funcionalidad extra implementada (no estaba en el plan original)

- **Panel admin web** (`/admin`) con HTTP Basic Auth — CRUD completo de movimientos, categorías, usuarios
- **Sistema de comandos por WhatsApp**: `borra el último`, `actualiza uber a 15.000`, `últimos`, `categoría del último: Transporte`, `ayuda`
- **Normalización de números hablados**: "veinte mil" → 20000, "15mil" → 15000
- **Stack PostgreSQL** con Docker Compose (backend + Postgres + Evolution + Redis)

---

## 3. Auditoría de seguridad

### CRÍTICO

| # | Hallazgo | Riesgo | Archivo | Remediación |
|---|----------|--------|---------|-------------|
| S1 | **Secretos reales en `.env`** | Las API keys (GROQ, Evolution), contraseña admin y teléfonos personales están en texto plano. Si el repo se sube a GitHub sin limpiar, quedan expuestos. `.gitignore` lo excluye pero no hay protección adicional. | `.env` | Rotar TODAS las keys inmediatamente si el repo se publicó alguna vez. Usar un secret manager o al mínimo `git-crypt`. Agregar pre-commit hook que bloquee commits con archivos `.env`. |
| S2 | **XSS almacenado en panel admin** | Los datos del usuario (descripción, mensaje_original) se inyectan directamente en HTML sin escapar via template literals JS: `` `<td>${m.descripcion}` ``. Un mensaje de WhatsApp malicioso podría ejecutar JS en el navegador del admin. | `backend/admin/index.html:141-153` | Escapar HTML en la función `render()` antes de interpolar. Crear helper `esc(str)` que convierta `<>&"'` a entidades HTML. |
| S3 | **Webhook sin verificación de firma** | `/webhook/evolution` acepta cualquier POST sin validar que venga de Evolution API. Un atacante que conozca la URL podría inyectar mensajes falsos y crear movimientos fraudulentos. | `backend/main.py:108` | Validar header `apikey` o firma HMAC en el webhook. Evolution API soporta autenticación de webhooks. |
| S4 | **Credenciales de DB débiles** | `evolution:evolution` como user/password de PostgreSQL es trivial de adivinar. | `docker-compose.yml:72-73`, `.env:2` | Usar contraseña generada aleatoriamente. No usar las mismas credenciales que la DB de Evolution. |
| S5 | **Sin HTTPS** | Todo el tráfico (admin con credenciales Basic Auth, webhook, datos financieros) viaja en texto plano HTTP. | `docker-compose.yml` | Si se expone fuera de localhost, agregar reverse proxy (Caddy/nginx) con TLS. Para uso local está OK. |

### MEDIO

| # | Hallazgo | Riesgo | Remediación |
|---|----------|--------|-------------|
| S6 | **Sin rate limiting** | Cualquier endpoint puede ser bombardeado sin límite. | Agregar `slowapi` o middleware de rate limiting al menos en `/webhook/evolution` y `/admin/*`. |
| S7 | **Sin CSRF en admin** | HTTP Basic no protege contra CSRF. Un sitio malicioso podría hacer requests al admin si el browser tiene las credenciales cacheadas. | Agregar token CSRF o migrar a cookie-based auth con SameSite=Strict. |
| S8 | **Sin protección de fuerza bruta en login admin** | No hay lockout ni delay después de intentos fallidos. | Implementar delay exponencial o lockout temporal en `require_admin()`. |
| S9 | **Endpoints públicos sin auth** | `/health`, `/categorias`, `/movimientos`, `/whatsapp/estado` son accesibles sin autenticación. `/movimientos` expone datos financieros. | Mover `/movimientos` y `/categorias` detrás de auth, o eliminarlos (el admin ya los tiene). |

### BAJO

| # | Hallazgo | Remediación |
|---|----------|-------------|
| S10 | Dockerfile copia tests al contenedor de producción | Usar `.dockerignore` para excluir `tests/`, `pytest.ini`, `__pycache__/` |
| S11 | Python 3.14 en local vs 3.12 en Docker | Alinear versiones para evitar incompatibilidades |
| S12 | Evolution API v2.3.7 fija — puede tener CVEs | Actualizar periódicamente, revisar changelogs |
| S13 | Sin logging centralizado | Configurar logging con formato estructurado (JSON) para debugging |

---

## 4. Auditoría de producto

### Problemas funcionales

| # | Hallazgo | Impacto | Remediación |
|---|----------|---------|-------------|
| P1 | **Parser solo regex, sin IA** | El plan menciona Claude API para extracción, pero `extractor.py` solo delega a regex. Confianza máxima 0.8. Muchos mensajes naturales fallarán. | Implementar integración con Groq LLM (ya tienes la key) o Claude API como parser primario, con regex como fallback. |
| P2 | **Sin detección de duplicados** | Si Evolution reenvía un webhook (retry), se crean movimientos duplicados. | Agregar campo `message_id` (ID del mensaje de WhatsApp) y constraint UNIQUE, o deduplicar por mensaje_original + fecha_registro + user_id en ventana de tiempo. |
| P3 | **Borrado inmediato sin confirmación** | `borra el último` elimina sin preguntar. Solo pide confirmación cuando hay múltiples candidatos. | Agregar confirmación: "¿Borrar $15.300 en Mercado? Responde sí/no." |
| P4 | **Estado en memoria (no persistente)** | `_PENDIENTES` (confirmaciones pendientes) y `_numero_instancia` se pierden al reiniciar el server. | Guardar en Redis (ya disponible en el stack) o en DB. |
| P5 | **Sin mensaje de bienvenida** | Un usuario nuevo autorizado no recibe indicación de cómo usar el bot. | Enviar mensaje de ayuda la primera vez que un usuario registrado escribe. |
| P6 | **Sin soporte para correcciones del monto parseado** | Si el bot registra $15.000 pero el usuario quería $150.000, no hay un flujo corto para corregir. Tiene que usar el comando de edición. | Después de registrar, permitir "no, era 150 mil" como corrección del último registro. |
| P7 | **Categoría "Otros" como cajón de sastre** | Muchos gastos caen en "Otros" porque las keywords son limitadas. | Ampliar keywords, considerar subcategorías, o usar IA para clasificación. |

### Mejoras de UX pendientes

- Resumen diario/semanal automático por WhatsApp
- Soporte para fotos de recibos (OCR futuro)
- Comando "cuánto llevo este mes" / "cuánto gasté en transporte"
- Emoji de categoría en las confirmaciones (🛒 Mercado, 🚕 Transporte, etc.)
- Formato de fecha en confirmaciones (mostrar "hoy", "ayer" en vez de ISO)

---

## 5. Auditoría contable/financiera

| # | Hallazgo | Impacto | Remediación |
|---|----------|---------|-------------|
| C1 | **Sin log de auditoría para ediciones/borrados** | El plan dice "auditable" pero no hay tabla de auditoría. Si se edita un monto o se borra un registro, no queda rastro de los valores anteriores. | Crear tabla `audit_log` con: movimiento_id, accion (crear/editar/borrar), valores_anteriores (JSON), valores_nuevos, timestamp, origen (whatsapp/admin). |
| C2 | **Sin soft delete** | Los registros se borran con `db.delete()`. No hay papelera ni recuperación. | Agregar columna `eliminado_en` (nullable timestamp). Filtrar por defecto los eliminados. |
| C3 | **Presupuestos sin implementar** | La tabla existe pero ningún código la usa. No hay alertas de límite ni proyecciones. | Implementar en Fase 4. |
| C4 | **Sin balance acumulado** | No hay forma rápida de saber: total ingresos - total gastos = balance. | Agregar endpoint y comando WhatsApp para balance mensual/acumulado. |
| C5 | **Sin separación de cuentas/billeteras** | Todo el dinero es una sola "bolsa". En Colombia es común separar: efectivo, cuenta bancaria, Nequi/Daviplata, tarjeta de crédito. | Agregar campo `medio_pago` al modelo de movimientos. |
| C6 | **Sin manejo de gastos recurrentes** | Arriendo, servicios, suscripciones se registran manualmente cada mes. | Agregar tabla `recurrentes` con monto, frecuencia, siguiente_fecha. Bot pregunta cada mes "¿Pagaste el arriendo este mes?" |
| C7 | **Fecha de gasto se asume como "hoy" si no se menciona** | Si alguien dice "gasté 50 mil en mercado" a las 11pm pero fue en la mañana, la fecha es correcta. Pero si lo dice al día siguiente sin decir "ayer", queda con fecha equivocada. | Esto es inherente al diseño (la fuente de verdad es el mensaje). Documentar la limitación y facilitar la corrección con "fecha del último: ayer". |
| C8 | **Sin categoría de ahorro/inversión** | El modelo solo tiene gasto/ingreso. No hay concepto de transferencia entre cuentas, ahorro, o inversión. | Agregar tipo "transferencia" en categorías, o tabla separada de metas de ahorro. |

---

## 6. Auditoría de sistema

| # | Hallazgo | Impacto | Remediación |
|---|----------|---------|-------------|
| T1 | **Sin backups** | Si el volumen de Docker se corrompe, se pierden todos los datos financieros. | Configurar pg_dump periódico (cron) a un directorio externo o cloud storage. |
| T2 | **Sin monitoreo** | No hay health checks para Evolution, Redis, ni alertas si el bot deja de funcionar. | Agregar endpoint `/health/full` que verifique DB + Evolution + Redis. Cron o uptime monitor externo. |
| T3 | **Redis no utilizado por la app** | Redis está en el stack para Evolution, pero la app no lo usa. Podría almacenar pendientes, caché, rate limiting. | Evaluar uso para `_PENDIENTES`, caché de categorías, rate limiting con `slowapi`. |
| T4 | **Sin CI/CD** | No hay pipeline de tests automáticos ni deploy. | Agregar GitHub Actions para correr tests en PR. |
| T5 | **Alembic corre en CMD del Dockerfile** | Si la migración falla, el container se cae. No hay rollback automático. | Separar migración del startup. Correr `alembic upgrade head` en un init container o script previo. |
| T6 | **Sin `.dockerignore`** | Se copian `.env`, tests, `__pycache__`, `.git` al contenedor. | Crear `.dockerignore` con exclusiones apropiadas. |

---

## 7. Alcance

### Dentro del alcance
- Captura de gasto/ingreso por texto libre ("gasté 15.300 en el mercado").
- Captura por nota de voz (transcripción automática vía Groq/Whisper).
- Clasificación automática por categoría, editable.
- Comandos conversacionales: borrar, editar, listar, cambiar categoría, ayuda.
- Almacenamiento en PostgreSQL con migraciones Alembic.
- Panel admin web con CRUD completo.
- Dashboard con gráficos en tiempo real (pendiente).
- Analítica en Python: proyecciones, promedios, anomalías (pendiente).
- Soporte para dos usuarios con datos separados.
- Skills de Claude Code para finanzas en Colombia.

### Fuera del alcance (explícitamente)
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
│ (tú/pareja) │                      │  (Baileys v2.3.7) │
└─────────────┘                      └────────┬──────────┘
                                               │ webhook
                                               ▼
                                     ┌───────────────────┐
                                     │  FastAPI Backend   │
                                     │  /webhook/evolution│
                                     └────────┬──────────┘
                                               │
                              ┌────────────────┼────────────────┐
                              ▼                ▼                ▼
                    ┌─────────────┐  ┌──────────────┐  ┌───────────┐
                    │ ¿Audio?     │  │ ¿Comando?    │  │ Parser    │
                    │ → Groq API  │  │ → Ejecutar   │  │ Regex     │
                    │   Whisper   │  │   CRUD       │  │ Extracción│
                    └──────┬──────┘  └──────┬───────┘  └─────┬─────┘
                           │               │                │
                           └───────────────┴────────────────┘
                                           │
                                           ▼
                              ┌───────────────────────┐
                              │  PostgreSQL (Docker)   │
                              │  + Redis (para Evol.)  │
                              └───────────┬───────────┘
                                          │
                     ┌────────────────────┼────────────────────┐
                     ▼                    ▼                    ▼
            ┌──────────────┐   ┌──────────────────┐  ┌──────────────┐
            │ Admin Panel  │   │ Dashboard        │  │ Analítica    │
            │ (HTML/JS)    │   │ (Streamlit)      │  │ (Python)     │
            │ IMPLEMENTADO │   │ PENDIENTE        │  │ PENDIENTE    │
            └──────────────┘   └──────────────────┘  └──────────────┘
```

---

## 10. Stack tecnológico

| Componente | Implementado | Notas |
|---|---|---|
| Canal WhatsApp | Evolution API v2.3.7 (Baileys, self-hosted) | Riesgo bajo de bloqueo para uso personal |
| Backend / webhook | Python 3.12 + FastAPI | Docker container |
| Transcripción de audio | Groq API (Whisper large-v3-turbo) | Gratis, requiere GROQ_API_KEY |
| Extracción de datos | Regex + normalización de números | Plan: agregar LLM como parser primario |
| Base de datos | PostgreSQL 15 (Docker) | Producción y tests |
| ORM | SQLAlchemy 2.0 + Alembic | Migraciones versionadas |
| Cache/Queue | Redis 7 (para Evolution) | Disponible para uso de la app |
| Panel admin | HTML/JS vanilla con HTTP Basic Auth | CRUD movimientos, categorías, usuarios |
| Dashboard | Streamlit (placeholder) | Por implementar |
| Orquestación | Docker Compose | backend + postgres + evolution + redis |

---

## 11. Modelo de datos

```sql
-- Tabla de usuarios (tú y tu pareja)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    numero_whatsapp TEXT UNIQUE NOT NULL
);

-- Categorías (editables, con set inicial predefinido)
CREATE TABLE categorias (
    id INTEGER PRIMARY KEY,
    nombre TEXT UNIQUE NOT NULL,
    tipo TEXT CHECK(tipo IN ('gasto', 'ingreso')) DEFAULT 'gasto'
);

-- Registro de gastos/ingresos
CREATE TABLE movimientos (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    categoria_id INTEGER REFERENCES categorias(id),
    monto_cop INTEGER NOT NULL,
    descripcion TEXT,
    mensaje_original TEXT NOT NULL,      -- texto o transcripción tal cual
    fue_audio BOOLEAN DEFAULT FALSE,
    confianza_parsing REAL,               -- confianza del parser (0-1)
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_gasto DATE                      -- fecha real del gasto
);

-- Presupuestos mensuales por categoría (SIN IMPLEMENTAR en código)
CREATE TABLE presupuestos (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    categoria_id INTEGER REFERENCES categorias(id),
    monto_limite_cop INTEGER NOT NULL,
    mes_vigente TEXT -- formato 'YYYY-MM'
);
```

### Tablas pendientes de crear

```sql
-- Auditoría de cambios (hallazgo C1)
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    tabla TEXT NOT NULL,               -- 'movimientos', 'categorias', etc.
    registro_id INTEGER NOT NULL,
    accion TEXT NOT NULL,              -- 'crear', 'editar', 'borrar'
    valores_anteriores JSONB,
    valores_nuevos JSONB,
    origen TEXT DEFAULT 'whatsapp',    -- 'whatsapp', 'admin', 'sistema'
    user_id INTEGER REFERENCES users(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gastos recurrentes (hallazgo C6)
CREATE TABLE recurrentes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    categoria_id INTEGER REFERENCES categorias(id),
    monto_cop INTEGER NOT NULL,
    descripcion TEXT,
    frecuencia TEXT DEFAULT 'mensual',  -- 'mensual', 'quincenal', 'semanal'
    dia_del_mes INTEGER,
    activo BOOLEAN DEFAULT TRUE
);
```

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
- [x] .dockerignore
- [x] Tabla audit_log con logging automático
- [x] Detección de duplicados en webhook
- [x] Auth migrada a cookies HttpOnly + 2FA TOTP
- [x] Login/Logout con página dedicada
- [x] Soft delete para movimientos y cuotas
- [ ] Cambiar credenciales DB (S4) — acción manual del usuario

### Fase 6 — Pendiente
- [ ] Comandos WhatsApp: "presupuesto mercado 500 mil", "cuánto llevo", "resumen del mes"
- [ ] Alertas de presupuesto por WhatsApp al registrar gasto (backend listo, integración pendiente)
- [ ] Resumen semanal automático por WhatsApp
- [ ] Tests frontend (Jest + React Testing Library)
- [ ] CI/CD (GitHub Actions)
- [ ] Exportar datos (CSV/PDF)
- [ ] Proyecciones financieras y detección de anomalías

### Fase 7 — Skills Claude Code y MCP (COMPLETADA 2026-09-01)
- [x] 14 skills creados (.claude/commands/)
- [x] CLAUDE.md con contexto del proyecto
- [ ] MCP a la base de datos (evaluado, pendiente implementar)

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
├── docker-compose.yml      # backend + postgres + evolution + redis
├── backend/
│   ├── Dockerfile
│   ├── main.py             # FastAPI app + webhooks
│   ├── config.py           # Pydantic settings
│   ├── tiempo.py           # Utilidades de timezone Bogotá
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── admin/
│   │   ├── auth.py         # HTTP Basic Auth
│   │   ├── router.py       # CRUD endpoints admin
│   │   └── index.html      # Panel admin SPA
│   ├── db/
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── session.py      # Engine y session factory
│   │   ├── seed.py         # Categorías iniciales
│   │   ├── users_seed.py   # Seed de usuarios desde .env
│   │   └── migrations/
│   │       ├── env.py
│   │       └── versions/
│   │           └── 001_initial_schema.py
│   ├── parser/
│   │   ├── extractor.py    # Punto de entrada (delega a regex)
│   │   ├── fallback_regex.py  # Parser principal actual
│   │   ├── categorias.py   # Keywords por categoría
│   │   ├── mensajes.py     # Formato de respuestas
│   │   ├── numeros_hablados.py  # "veinte mil" → 20000
│   │   └── schemas.py      # Dataclass Extraccion
│   ├── services/
│   │   ├── admin.py        # Lógica CRUD admin
│   │   ├── audio.py        # Orquestación de transcripción
│   │   ├── comandos.py     # Sistema de comandos WhatsApp
│   │   ├── registro.py     # Pipeline principal de registro
│   │   └── resultado.py    # Dataclass ResultadoRegistro
│   ├── transcription/
│   │   └── whisper_client.py  # Groq API para transcripción
│   ├── webhook/
│   │   ├── client.py       # Cliente Evolution API
│   │   ├── evolution.py    # Parser de payloads Evolution
│   │   ├── media.py        # Descarga de audio
│   │   ├── qr_page.py      # HTML para escanear QR
│   │   └── sender.py       # Envío de mensajes WhatsApp
│   ├── scripts/
│   │   └── (vacío)
│   └── tests/
│       ├── conftest.py
│       ├── test_admin.py
│       ├── test_comandos.py
│       ├── test_health.py
│       ├── test_mensajes.py
│       ├── test_migrations.py
│       ├── test_models.py
│       ├── test_numeros_hablados.py
│       ├── test_parser.py
│       ├── test_tiempo.py
│       ├── test_transcripcion.py
│       └── test_webhook.py
├── analytics/
│   └── __init__.py         # Placeholder
├── dashboard/
│   └── app.py              # Placeholder
├── docs/
│   └── plan-proyecto-finanzas-whatsapp.md  # Este archivo
└── postgres/
    └── init-finanzas.sh    # Init script para crear DB finanzas
```

---

## 17. Prioridades de acción inmediata

### Sprint 1 — Seguridad (URGENTE)
1. Rotar API keys si el repo se compartió alguna vez
2. Escapar HTML en admin panel (XSS)
3. Agregar verificación de webhook
4. Crear `.dockerignore`
5. Cambiar credenciales de DB

### Sprint 2 — Integridad contable
1. Crear tabla `audit_log` + migración Alembic
2. Implementar soft delete
3. Agregar detección de duplicados de webhook
4. Agregar campo `message_id` a movimientos

### Sprint 3 — Dashboard MVP
1. Implementar Streamlit dashboard
2. Gráficos: por categoría, por mes, balance
3. Filtros por usuario y rango de fechas

### Sprint 4 — Parser inteligente
1. Integrar Groq LLM como parser primario
2. Mejorar categorización
3. Soporte para mensajes complejos

### Sprint 5 — Presupuestos y analítica
1. Activar lógica de presupuestos
2. Alertas de límite por WhatsApp
3. Resumen semanal automático
4. Proyección de cierre de mes
