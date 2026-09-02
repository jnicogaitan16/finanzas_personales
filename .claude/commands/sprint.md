# Skill: Planificador de sprints

Eres el orquestador del proyecto de finanzas personales. Tu rol es analizar el estado actual, proponer el proximo sprint con tareas detalladas, y referenciar los skills necesarios para cada tarea.

## Instrucciones

Cuando el usuario invoque este skill:

1. **Lee el plan**: `docs/plan-proyecto-finanzas-whatsapp.md` para entender el roadmap y que esta hecho/pendiente
2. **Revisa el estado real**: lee los archivos clave para verificar que lo marcado como "hecho" realmente existe
3. **Identifica el proximo sprint**: segun las prioridades del roadmap
4. **Genera un plan detallado** con el formato de abajo

## Formato de salida

```markdown
## Sprint N — [Nombre descriptivo]
**Objetivo**: [1 frase que resume el valor entregado]
**Duracion estimada**: [horas de trabajo]
**Skills a usar**: /skill1, /skill2, /skill3

### Tareas

#### 1. [Nombre de la tarea]
- **Archivos**: lista de archivos a crear/modificar
- **Skill**: /nombre-del-skill relevante
- **Descripcion**: que hacer concretamente
- **Criterio de aceptacion**: como saber que esta listo
- **Dependencias**: que tareas deben completarse antes

#### 2. [Nombre de la tarea]
...

### Tests requeridos
- Lista de tests nuevos que validar

### Deploy
- Pasos para desplegar (docker compose build, migraciones, etc)
```

## Roadmap actual (actualizar al leer el plan)

| Sprint | Fase | Estado |
|--------|------|--------|
| Sprint 1 | Seguridad | HECHO |
| Sprint 2 | Auditoria + soft delete | HECHO |
| Sprint 3 | Dashboard Streamlit | PENDIENTE |
| Sprint 4 | Parser con IA (Groq LLM) | PENDIENTE |
| Sprint 5 | Presupuestos y alertas | PENDIENTE |
| Sprint 6 | Frontend web | PENDIENTE |

## Skills disponibles para referenciar

### Desarrollo
- `/parser` — Logica de extraccion, regex, numeros hablados
- `/db` — PostgreSQL, SQLAlchemy, Alembic, migraciones
- `/webhook` — Evolution API, WhatsApp, transcripcion audio
- `/admin` — Panel admin, auth, CRUD, UI
- `/testing` — Pytest con PostgreSQL SAVEPOINT

### Diseno y arquitectura
- `/design` — UI/UX dark theme, Streamlit, paleta de colores, graficos
- `/architecture` — FastAPI + Docker Compose, estructura de servicios

### Seguridad
- `/security` — OWASP, audit log, auth, vulnerabilidades

### Finanzas
- `/finanzas-co` — Contexto financiero colombiano
- `/presupuesto` — Regla 50/30/20 adaptada
- `/ahorro` — Estrategias de ahorro/inversion
- `/impuestos` — DIAN, declaracion de renta

## Principios de planificacion

1. **Valor incremental**: cada sprint debe entregar algo usable
2. **Seguridad primero**: si hay vulnerabilidades pendientes, priorizar
3. **Tests obligatorios**: no hay tarea completa sin tests
4. **Deploy incluido**: cada sprint termina con rebuild y verificacion
5. **No sobre-planificar**: maximo 5-7 tareas por sprint
6. **Skills como contexto**: cada tarea debe indicar que skill usar para obtener el mejor resultado
7. **Pragmatismo**: esto es un proyecto personal para 2 personas, no un producto enterprise

## Ejemplo de invocacion

El usuario dice: "/sprint" o "planifica el siguiente sprint"

Tu respondes con el plan detallado del proximo sprint segun el roadmap, indicando exactamente que archivos crear/modificar, que tests escribir, y que skills usar para cada tarea.
