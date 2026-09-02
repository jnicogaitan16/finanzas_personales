# Skill: Base de datos PostgreSQL + SQLAlchemy + Alembic

Eres experto en el modelo de datos y migraciones de este proyecto.

## Stack

- PostgreSQL 15 (Docker, puerto host 5433, user: evolution)
- SQLAlchemy 2.0 con Mapped types
- Alembic para migraciones versionadas
- **NUNCA usar SQLite** en ningun contexto

## Archivos clave

- `backend/db/models.py` — Modelos SQLAlchemy (User, Categoria, Movimiento, Presupuesto, AuditLog)
- `backend/db/session.py` — Engine y SessionLocal (PostgreSQL puro)
- `backend/db/seed.py` — Categorias iniciales
- `backend/db/users_seed.py` — Seed de usuarios desde AUTHORIZED_USERS en .env
- `backend/db/migrations/versions/` — Migraciones Alembic

## Esquema actual

```
users (id, nombre, numero_whatsapp UNIQUE)
categorias (id, nombre UNIQUE, tipo CHECK gasto/ingreso)
movimientos (id, user_id FK, categoria_id FK nullable, monto_cop INT,
             descripcion, mensaje_original, fue_audio, confianza_parsing,
             fecha_registro, fecha_gasto, eliminado_en nullable)
presupuestos (id, user_id FK, categoria_id FK, monto_limite_cop, mes_vigente,
              UNIQUE user+categoria+mes)
audit_log (id, tabla, registro_id, accion, valores_anteriores JSON,
           valores_nuevos JSON, origen, user_id, timestamp)
```

## Convenciones

- Montos siempre INTEGER (COP sin decimales)
- Fechas en timezone Bogota (naive datetime, sin tzinfo)
- Soft delete en movimientos: columna `eliminado_en` (nullable DateTime)
- Toda consulta de movimientos debe filtrar `eliminado_en IS NULL`
- Audit log en cada crear/editar/borrar de movimientos
- FK constraints con nombres explicitos (fk_tabla_columna)
- Indices en columnas de filtro frecuente (user_id, categoria_id, fecha_gasto)

## Crear nueva migracion

```bash
cd backend
# Autogenerar desde cambios en models.py:
alembic revision --autogenerate -m "descripcion del cambio"
# O manual:
alembic revision -m "descripcion"
# Aplicar:
alembic upgrade head
```

## Patron de migracion manual

```python
revision: str = "004_nombre"
down_revision = "003_soft_delete"

def upgrade() -> None:
    op.add_column("tabla", sa.Column("nueva", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("tabla", "nueva")
```

## Servicios de datos

- `services/admin.py` — CRUD completo (crear, actualizar, eliminar, listar movimientos/categorias/usuarios)
- `services/registro.py` — Pipeline de registro desde WhatsApp
- `services/audit.py` — Logging automatico en audit_log
- `services/comandos.py` — Comandos WhatsApp (borrar, editar, listar)

## Regla: validacion de FK al borrar

Al borrar usuario o categoria, contar TODOS los movimientos (incluidos soft-deleted) porque los FK siguen activos:
```python
usados = db.query(Movimiento).filter(Movimiento.user_id == user.id).count()  # sin _activos()
```
