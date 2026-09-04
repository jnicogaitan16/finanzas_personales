# Skill: Arquitectura del sistema

Eres experto en la arquitectura de este proyecto FastAPI + Docker Compose.

## Diagrama de servicios

```
    Next.js Frontend (Docker :3000)
            |
        REST API
            |
    FastAPI Backend (Docker :8000)
        /          \
    Parser       Servicios
    (LLM+regex)  (CRUD + audit)
        \          /
    PostgreSQL (Docker :5433)
        |
    Redis (Docker :6379)
    (command state, deduplicacion)
```

## Docker Compose (4 servicios)

| Servicio | Imagen | Puerto host | Depende de |
|----------|--------|-------------|------------|
| backend | finanzas-personales-backend | 8000 | postgres |
| frontend | finanzas-personales-frontend | 3000 | backend |
| postgres | postgres:15-alpine | 5433 | - |
| redis | redis:7-alpine | - (interno) | - |

## Patrones de arquitectura

### Capas del backend

```
main.py (endpoints FastAPI)
  -> services/ (logica de negocio)
    -> parser/ (extraccion de datos)
    -> db/ (acceso a datos)
  -> admin/ (panel web)
```

### Flujo de datos

1. **Frontend** envia datos via REST API
2. **Admin router** procesa la peticion
3. **Services** ejecutan logica de negocio (CRUD, comandos, presupuesto)
4. **Parser**: extraer monto, categoria, fecha del texto (LLM + regex fallback)
5. **DB**: crear/editar/borrar Movimiento + audit_log
6. **Frontend** muestra datos actualizados (auto-refresh cada 5s)

### Patron de servicios

```python
# services/ nunca importa de main.py ni de admin/
# services/ puede importar de parser/, db/, tiempo.py
# admin/ importa de services/ y db/
# main.py importa de services/, admin/
```

### Configuracion (.env -> Pydantic Settings)

```python
class Settings(BaseSettings):
    database_url: str        # PostgreSQL connection string
    authorized_users: str    # "Nombre:telefono,Nombre:telefono"
    admin_user: str          # usuario admin panel
    admin_password: str      # contrasena admin
    admin_totp_secret: str   # TOTP secret para 2FA
    groq_api_key: str        # API key para parser LLM
    redis_url: str           # Redis para state management
```

## Consideraciones de escalabilidad

Este es un proyecto personal (2 usuarios). NO sobre-ingeniar:
- No microservicios (todo en un backend)
- No Kubernetes (Docker Compose es suficiente)
- No cache de queries (PostgreSQL es suficientemente rapido)
- No async (todo es sincrono, httpx para llamadas externas)
- No message queue

## Estado en Redis

- `_PENDIENTES` en comandos.py (confirmaciones de borrado/edicion pendientes)
- `_MSG_IDS_VISTOS` en cache.py (deduplicacion)
- Fallback a memoria si Redis no esta disponible
- `_sessions` en auth.py (sesiones de admin, en memoria)
