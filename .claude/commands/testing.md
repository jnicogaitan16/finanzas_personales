# Skill: Testing con PostgreSQL

Eres experto en la estrategia de tests de este proyecto.

## Stack

- pytest contra PostgreSQL real (localhost:5433/finanzas)
- Aislamiento por SAVEPOINT (rollback automatico por test)
- FastAPI TestClient con dependency override
- **NUNCA usar SQLite** para tests

## Archivos clave

- `backend/tests/conftest.py` — Fixtures: db_session, seeded_session, client
- `backend/tests/test_*.py` — Tests por modulo

## Patron de aislamiento SAVEPOINT

Cada test obtiene una sesion de PostgreSQL dentro de una transaccion que se revierte al final:

```python
@pytest.fixture()
def db_session():
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    session.begin_nested()  # SAVEPOINT

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session
    session.close()
    transaction.rollback()  # revierte TODO
    connection.close()
```

## Fixture hierarchy

```
db_session        -> sesion limpia con tablas vacias (DELETE de todas las tablas)
  seeded_session  -> db_session + categorias iniciales + User Nico (573001112233)
    client        -> TestClient con get_db overrideado a seeded_session
```

## Reglas importantes

1. **No hardcodear IDs**: PostgreSQL no resetea secuencias entre tests. Usar queries para obtener IDs:
   ```python
   user = seeded_session.query(User).filter_by(nombre="Nico").one()
   cat = seeded_session.query(Categoria).filter_by(nombre="Mercado").one()
   ```

2. **Soft delete**: Despues de borrar, verificar `eliminado_en is not None` en vez de `count() == 0`

3. **Auth en tests de admin**: Usar login programatico, no HTTP Basic:
   ```python
   from admin.auth import COOKIE_NAME, clear_all_sessions, login
   clear_all_sessions()
   token = login("admin", "secreto")
   client.cookies.set(COOKIE_NAME, token)
   ```

4. **Monkeypatch settings**: Siempre limpiar settings sensibles:
   ```python
   monkeypatch.setattr(settings, "admin_password", "secreto")
   monkeypatch.setattr(settings, "evolution_api_key", "")
   monkeypatch.setattr(settings, "admin_totp_secret", "")
   ```

5. **refresh despues de operaciones**: Si el test hace una operacion via API y luego verifica con la sesion directa, hacer `seeded_session.refresh(obj)` para ver los cambios.

## Correr tests

```bash
cd backend && python -m pytest tests/ -q          # todos
cd backend && python -m pytest tests/test_parser.py -q  # un modulo
cd backend && python -m pytest tests/test_X.py::test_Y -v  # un test
```

## Cobertura de tests actual (93 tests)

- test_parser.py — Extraccion de montos, categorias, fechas
- test_numeros_hablados.py — Conversion palabras->numeros
- test_comandos.py — Borrar, editar, listar via WhatsApp
- test_webhook.py — Webhook texto/audio, Evolution payload parsing
- test_admin.py — CRUD admin, auth, login/logout, TOTP
- test_models.py — Constraints DB, FK, uniques
- test_migrations.py — Cadena de migraciones Alembic valida
- test_health.py — Health check, categorias
- test_mensajes.py — Formato COP, mensajes de confirmacion
- test_tiempo.py — Timezone Bogota
- test_transcripcion.py — Mock de Groq/Whisper
