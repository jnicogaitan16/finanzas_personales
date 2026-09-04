# Plan de Deprecación — WhatsApp / Evolution API

**Fecha:** 2026-09-03
**Motivo:** El frontend web (Next.js) cubre el 100% de la funcionalidad. WhatsApp ya no es necesario como canal de entrada.
**URL producción:** https://contabilidad-n-d.duckdns.org

---

## Resumen de impacto

| Métrica | Valor |
|---------|-------|
| Líneas a eliminar | ~550 |
| Líneas a refactorizar | ~150 |
| Archivos a eliminar | 8 |
| Archivos a modificar | ~12 |
| Servicios Docker a eliminar | 1 (Evolution API) |
| Código que NO se toca | ~6000+ líneas (parser, comandos, admin, frontend) |

---

## Fase 1 — Eliminar módulos WhatsApp-only

**Riesgo:** Bajo — estos módulos no tienen dependencias en el resto del sistema.

### 1.1 Eliminar directorio `backend/webhook/`
- `webhook/client.py` — Cliente HTTP para Evolution API (234 líneas)
- `webhook/sender.py` — Envío de mensajes WhatsApp (31 líneas)
- `webhook/evolution.py` — Parser de payloads Evolution (158 líneas)
- `webhook/media.py` — Descarga de audio desde Evolution (60 líneas)
- `webhook/qr_page.py` — HTML para página QR (21 líneas)
- `webhook/__init__.py`

### 1.2 Eliminar directorio `backend/transcription/`
- `transcription/whisper_client.py` — Cliente Groq Whisper (40 líneas)
- `transcription/__init__.py`

### 1.3 Eliminar servicio de audio
- `backend/services/audio.py` — Orquestación de transcripción (34 líneas)

### 1.4 Eliminar tests WhatsApp
- `backend/tests/test_webhook.py` — Tests del webhook Evolution (~293 líneas)
- `backend/tests/test_transcripcion.py` — Tests de transcripción (si existe)

---

## Fase 2 — Limpiar endpoints en `backend/main.py`

### 2.1 Eliminar imports WhatsApp
```python
# ELIMINAR estas líneas:
from webhook.client import (asegurar_instancia, estado_conexion, obtener_numero_instancia, obtener_qr)
from webhook.evolution import extraer_mensaje_entrada
from webhook.sender import enviar_texto_whatsapp
from services.audio import transcribir_nota_voz
```

### 2.2 Eliminar función lifespan
- Remover llamada a `asegurar_instancia()` del startup de FastAPI

### 2.3 Eliminar endpoints
| Endpoint | Método | Líneas aprox | Descripción |
|----------|--------|-------------|-------------|
| `/whatsapp/estado` | GET | 81-83 | Estado de conexión WhatsApp |
| `/whatsapp/qr` | GET | 86-111 | Página QR para vincular dispositivo |
| `/webhook/texto` | POST | 114-128 | Endpoint de prueba para texto |
| `/webhook/evolution` | POST | 149-192 | Webhook principal de Evolution API |

### 2.4 Mantener intacto
- `GET /health` — Health check (solo DB)
- Middleware de seguridad
- Router de admin
- Rate limiter (ajustar si tiene reglas específicas para `/webhook/*`)

---

## Fase 3 — Refactorizar código compartido

### 3.1 `backend/config.py` — Eliminar settings de Evolution y Groq
```python
# ELIMINAR:
evolution_api_url: str = ""
evolution_api_key: str = ""
evolution_instance: str = "finanzas"
evolution_webhook_url: str = "http://backend:8000/webhook/evolution"
groq_api_key: str = ""

# MANTENER:
database_url, admin_user, admin_password, admin_totp_secret, session_hours, redis_url
```

### 3.2 `backend/services/registro.py` — Cambiar origen por defecto
```python
# ANTES:
registrar_creacion(db, movimiento, origen="whatsapp")

# DESPUÉS:
registrar_creacion(db, movimiento, origen="admin")
```

### 3.3 `backend/services/audit.py` — Cambiar origen por defecto
```python
# ANTES:
def registrar_creacion(db, movimiento, origen="whatsapp"):

# DESPUÉS:
def registrar_creacion(db, movimiento, origen="admin"):
```

### 3.4 `backend/db/models.py` — Actualizar defaults
```python
# AuditLog.origen: cambiar default de "whatsapp" a "admin"
# numero_whatsapp: MANTENER el campo (datos históricos), pero ya no se usa activamente
# fue_audio: MANTENER el campo (datos históricos), pero ya no se pobla
```

### 3.5 `backend/cache.py` — Revisar
- Si el caché Redis (db 1) se usa solo para deduplicación de mensajes WhatsApp → evaluar si sigue siendo necesario
- Si se usa para otra cosa (command state) → mantener

### 3.6 `backend/tests/conftest.py` — Limpiar fixtures
```python
# ELIMINAR:
monkeypatch.setattr(settings, "evolution_api_key", "")
monkeypatch.setattr(settings, "groq_api_key", "")
```

---

## Fase 4 — Infraestructura Docker

### 4.1 `docker-compose.yml` (desarrollo)
- **ELIMINAR** servicio `evolution` completo (~37 líneas)
- **EVALUAR** servicio `redis`:
  - Si Redis db 1 se usa en el backend → MANTENER Redis
  - Si Redis solo servía a Evolution → ELIMINAR Redis
- **ELIMINAR** dependencia de `evolution` en otros servicios

### 4.2 `docker-compose.prod.yml` (producción)
- **ELIMINAR** servicio `evolution` completo (~35 líneas)
- **EVALUAR** Redis (mismo criterio que desarrollo)
- **ELIMINAR** dependencia de `evolution` en otros servicios

### 4.3 `Caddyfile` — Eliminar rutas WhatsApp
```caddyfile
# ELIMINAR:
handle /webhook/* {
    reverse_proxy backend:8000
}

handle /whatsapp/* {
    reverse_proxy backend:8000
}
```

---

## Fase 5 — Variables de entorno y configuración

### 5.1 `.env.example` — Eliminar
```
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE=finanzas
GROQ_API_KEY=
AUTHORIZED_USERS=
WEBHOOK_BASE_URL=
```

### 5.2 `.env.production.example` — Eliminar las mismas variables

### 5.3 `.env` (local) — Eliminar las mismas variables

### 5.4 Producción (Oracle Cloud) — Eliminar variables del `.env.production` en el servidor

---

## Fase 6 — Frontend (cambios menores)

### 6.1 `frontend/src/lib/types.ts`
- Campo `numero_whatsapp` en interfaz `Usuario`: **MANTENER** (el backend aún tiene la columna)
- Opcionalmente renombrar a `telefono` en una migración futura

### 6.2 `frontend/src/app/usuarios/page.tsx`
- El campo de WhatsApp en el formulario de usuarios: **MANTENER** como "Teléfono"
- O eliminar del formulario si ya no es relevante

---

## Fase 7 — CI/CD y tests

### 7.1 `.github/workflows/test.yml`
- Limpiar seed de usuarios de test (quitar referencia a `numero_whatsapp` si corresponde)
- Verificar que no se levante Evolution en CI (actualmente no se levanta, OK)

### 7.2 `backend/db/users_seed.py`
- Cambiar fuente de `AUTHORIZED_USERS` (formato `Nombre:Telefono`) si aplica
- O eliminar si el seeding se hace desde el admin panel

---

## Fase 8 — Documentación y Skills

### 8.1 Actualizar `CLAUDE.md`
- Remover "WhatsApp: Evolution API" del stack
- Remover "Transcripción: Groq API" del stack
- Remover "Cache: Redis 7 (para Evolution)"
- Actualizar estructura de carpetas (quitar `webhook/`, `transcription/`)
- Actualizar reglas (quitar "Webhook verificado con header apikey")

### 8.2 Actualizar `docs/plan-proyecto-finanzas-whatsapp.md`
- Marcar WhatsApp como deprecado
- Actualizar arquitectura y stack

### 8.3 Actualizar `docs/deploy-oracle-cloud.md`
- Quitar sección de QR pairing (líneas 122-127)

### 8.4 Actualizar skills de Claude
- `.claude/commands/webhook.md` — Eliminar o archivar
- `.claude/commands/architecture.md` — Actualizar diagrama

### 8.5 Actualizar `README.md`
- Quitar referencias a WhatsApp bot

---

## Orden de ejecución recomendado

```
Fase 1 → Fase 2 → Fase 3 → Tests locales
    ↓
Fase 4 → Fase 5 → Docker compose up → Verificar que todo funciona
    ↓
Fase 6 → Fase 7 → Tests E2E completos
    ↓
Fase 8 → PR a dev → CI → PR a main → Deploy
```

---

## Lo que NO se toca

Estos módulos son 100% independientes de WhatsApp y no requieren cambios:

| Módulo | Razón |
|--------|-------|
| `backend/parser/` | Parseo genérico de texto financiero |
| `backend/services/comandos.py` | Lógica de comandos genérica |
| `backend/services/admin.py` | CRUD de admin |
| `backend/services/presupuesto.py` | Lógica de presupuesto |
| `backend/services/balance.py` | Balance de gastos compartidos |
| `backend/services/cuotas.py` | Tracking de cuotas |
| `backend/services/gastos_fijos.py` | Gastos fijos |
| `backend/admin/` | Panel admin completo |
| `backend/db/session.py` | Conexión a DB |
| `backend/db/migrations/` | Migraciones Alembic |
| `frontend/` | Dashboard Next.js (excepto campo `numero_whatsapp`) |

---

## Validación final

Antes de mergear, verificar:

- [ ] `docker compose up -d` levanta sin errores (sin Evolution)
- [ ] `python -m pytest tests/ -q` — todos los tests pasan
- [ ] `npx playwright test` — E2E pasan
- [ ] Panel admin funciona: login, CRUD movimientos, usuarios
- [ ] Frontend web funciona: registro de gastos/ingresos, reportes
- [ ] Health endpoint responde OK
- [ ] No hay imports rotos ni referencias a módulos eliminados
- [ ] Producción: deploy exitoso sin Evolution
