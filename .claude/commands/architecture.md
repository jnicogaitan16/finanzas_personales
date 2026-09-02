# Skill: Arquitectura del sistema

Eres experto en la arquitectura de este proyecto FastAPI + Docker Compose.

## Diagrama de servicios

```
                    Internet / WhatsApp
                          |
                    Evolution API (Docker :8080)
                          |
                     Webhook POST
                          |
                    FastAPI Backend (Docker :8000)
                    /           \           \
              Parser         Comandos     Transcripcion
              (regex)        (CRUD)       (Groq API)
                    \           |           /
                     PostgreSQL (Docker :5433)
                          |
                    Redis (Docker :6379)
                    (para Evolution)
```

## Docker Compose (4 servicios)

| Servicio | Imagen | Puerto host | Depende de |
|----------|--------|-------------|------------|
| backend | finanzas-personales-backend | 8000 | postgres, evolution |
| postgres | postgres:15-alpine | 5433 | - |
| evolution | evoapicloud/evolution-api:v2.3.7 | 8080 | postgres, redis |
| redis | redis:7-alpine | - (interno) | - |

## Patrones de arquitectura

### Capas del backend

```
main.py (endpoints FastAPI)
  -> services/ (logica de negocio)
    -> parser/ (extraccion de datos)
    -> db/ (acceso a datos)
    -> webhook/ (comunicacion WhatsApp)
    -> transcription/ (Groq API)
  -> admin/ (panel web)
```

### Flujo de datos

1. **Webhook** recibe payload -> `evolution.py` extrae MensajeWhatsApp
2. **Deduplicacion** por message_id (OrderedDict en memoria, 500 IDs)
3. Si es **audio**: descargar de Evolution + transcribir con Groq
4. **Registro**: interpretar_comando() o registrar_texto()
5. **Parser**: extraer monto, categoria, fecha del texto
6. **DB**: crear Movimiento + audit_log
7. **Respuesta**: enviar confirmacion por WhatsApp

### Patron de servicios

```python
# services/ nunca importa de main.py ni de admin/
# services/ puede importar de parser/, db/, tiempo.py
# admin/ importa de services/ y db/
# main.py importa de services/, webhook/, admin/
```

### Configuracion (.env -> Pydantic Settings)

```python
class Settings(BaseSettings):
    database_url: str        # PostgreSQL connection string
    evolution_api_url: str   # http://evolution:8080 (Docker interno)
    evolution_api_key: str   # apikey para Evolution + webhook verification
    evolution_instance: str  # nombre de instancia WhatsApp
    authorized_users: str    # "Nombre:telefono,Nombre:telefono"
    admin_user: str          # usuario admin panel
    admin_password: str      # contrasena admin
    admin_totp_secret: str   # TOTP secret para 2FA
    groq_api_key: str        # API key para transcripcion Whisper
```

## Consideraciones de escalabilidad

Este es un proyecto personal (2 usuarios). NO sobre-ingeniar:
- No microservicios (todo en un backend)
- No Kubernetes (Docker Compose es suficiente)
- No cache de queries (PostgreSQL es suficientemente rapido)
- No async (todo es sincrono, httpx para llamadas externas)
- No message queue (el webhook procesa sincrono)

## Estado en memoria (limitaciones)

Estos datos se pierden al reiniciar el backend:
- `_PENDIENTES` en comandos.py (confirmaciones de borrado/edicion pendientes)
- `_MSG_IDS_VISTOS` en main.py (deduplicacion de webhooks)
- `_sessions` en auth.py (sesiones de admin)
- `_numero_instancia` en client.py (numero de WhatsApp de la instancia)

Esto es aceptable para un proyecto personal. Si crece, migrar a Redis.
