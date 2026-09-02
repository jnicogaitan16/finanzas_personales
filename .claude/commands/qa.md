# Skill: QA Automation — Playwright E2E Testing

## Stack de testing

- **Framework:** Playwright (TypeScript)
- **Runner:** @playwright/test
- **Ubicacion:** `frontend/e2e/`
- **Config:** `frontend/playwright.config.ts`
- **Auth state:** `frontend/e2e/.auth/session.json` (generado por setup)

## Comandos

```bash
# Desde frontend/
npx playwright test                    # Correr todos los tests
npx playwright test --headed           # Con browser visible
npx playwright test --ui               # UI mode interactivo
npx playwright test e2e/movimientos    # Un archivo especifico
npx playwright test -g "crear"         # Tests que matcheen un patron
npx playwright show-report             # Ver ultimo reporte HTML

# Debug
npx playwright test --debug            # Step-by-step debugger
PWDEBUG=1 npx playwright test         # Inspector de Playwright
```

## Prerequisitos para correr tests

Los tests E2E requieren el stack completo corriendo:

```bash
# 1. Levantar backend + DB + Evolution + Redis + Frontend
docker compose up -d

# 2. O levantar frontend en dev (si backend ya esta corriendo)
cd frontend && npm run dev
```

**Variables de entorno para tests** (en `frontend/.env.test` o env del sistema):
- `TEST_ADMIN_USER` — usuario admin (default: valor de ADMIN_USER en .env)
- `TEST_ADMIN_PASSWORD` — password admin (default: valor de ADMIN_PASSWORD en .env)
- `BASE_URL` — URL del frontend (default: http://localhost:3000)

## Arquitectura de tests

```
frontend/
  playwright.config.ts          # Config: baseURL, projects, retries
  e2e/
    auth.setup.ts               # Global setup: login y guardar session
    .auth/                      # Session state (gitignored)
    login.spec.ts               # Tests de autenticacion
    dashboard.spec.ts           # Dashboard, KPIs, filtros, graficos
    movimientos.spec.ts         # CRUD movimientos, filtros, medio pago
    categorias.spec.ts          # CRUD categorias, validaciones
    presupuestos.spec.ts        # Presupuestos, barras progreso
    compartido.spec.ts          # Balance gastos compartidos
    cuotas.spec.ts              # Compras en cuotas TDC
    gastos-fijos.spec.ts        # Gastos fijos recurrentes
    navegacion.spec.ts          # Header, nav links, responsive
```

## Convenciones

### Selectores (sin data-testid)
El frontend no usa `data-testid`. Usar selectores en este orden de preferencia:

1. **Role + name:** `page.getByRole('button', { name: 'Crear' })`
2. **Label:** `page.getByLabel('Monto')`
3. **Placeholder:** `page.getByPlaceholder('Descripcion')`
4. **Text:** `page.getByText('Dashboard')`
5. **CSS solo si es necesario:** `page.locator('table tbody tr')`

### Patron de Page Objects (opcional para pages complejas)
```typescript
// No crear page objects salvo que haya duplicacion real.
// Preferir helpers simples:
async function crearMovimiento(page: Page, datos: { monto: string, ... }) { ... }
```

### Manejo de dialogs
```typescript
// Dialogs shadcn/ui (modales React)
const dialog = page.getByRole('dialog');
await dialog.getByLabel('Monto').fill('50000');
await dialog.getByRole('button', { name: 'Crear' }).click();

// Dialogs nativos del browser (confirm/alert)
page.on('dialog', d => d.accept());
```

### Esperar carga de datos
```typescript
// La app usa polling cada 5s. Esperar a que la tabla tenga datos:
await page.getByRole('table').waitFor();
await expect(page.locator('table tbody tr').first()).toBeVisible();
```

### Toasts (Sonner)
```typescript
// Verificar toast de exito/error
await expect(page.getByText('Movimiento creado')).toBeVisible();
```

## Selectores clave por pagina

### Login (`/login`)
- `page.getByLabel('Usuario')` o `page.locator('input[name="username"]')`
- `page.getByLabel('Contrasena')` o `page.locator('input[name="password"]')`
- `page.locator('input[name="totp_code"]')` (si 2FA habilitado)
- `page.getByRole('button', { name: 'Entrar' })`

### Dashboard (`/`)
- KPIs: `page.getByText('Gasto del mes')`, `page.getByText('Ingreso del mes')`, `page.getByText('Balance')`
- Filtro usuario: `page.locator('select').first()`
- Nav meses: botones con iconos ChevronLeft/ChevronRight

### Movimientos (`/movimientos`)
- Boton crear: `page.getByRole('button', { name: 'Nuevo movimiento' })`
- Tabla: `page.getByRole('table')`
- En dialog: inputs por placeholder ("Descripcion", "0") o label
- Select de usuario/categoria/medio: usar `page.getByRole('dialog')` scope
- Editar: `page.getByRole('link', { name: 'Editar' })` en la fila
- Borrar: `page.getByRole('link', { name: 'Borrar' })` en la fila

### Categorias (`/categorias`)
- Boton: `page.getByRole('button', { name: 'Nueva categoria' })`
- Tipo badge: `.getByText('gasto')` o `.getByText('ingreso')` dentro de Badge

### Presupuestos (`/presupuestos`)
- Boton: `page.getByRole('button', { name: 'Nuevo presupuesto' })`
- Cards con barra de progreso y porcentaje
- Boton borrar dentro de cada card

### Cuotas (`/cuotas`)
- Boton: `page.getByRole('button', { name: 'Nueva compra' })`
- Cards resumen: "Cuota mensual total", "Deuda total", "Compras activas"
- Progress bar de cuotas pagadas

### Compartido (`/compartido`)
- Card balance: `page.getByText('Balance neto')`
- Tablas de detalle por usuario
- Nav meses

### Gastos Fijos (`/gastos-fijos`)
- Boton: `page.getByRole('button', { name: 'Nuevo gasto fijo' })`
- Toggle activo: botones "Desactivar"/"Activar" por fila

## API proxy (frontend -> backend)

Todas las llamadas API del frontend pasan por Next.js routes en `src/app/api/`:

| Frontend API | Backend real |
|---|---|
| `POST /api/login` | `POST /admin/login` (form-data) |
| `GET /api/movimientos` | `GET /admin/api/movimientos` |
| `POST /api/movimientos` | `POST /admin/api/movimientos` |
| `PATCH /api/movimientos/{id}` | `PATCH /admin/api/movimientos/{id}` |
| `DELETE /api/movimientos/{id}` | `DELETE /admin/api/movimientos/{id}` |
| `GET/POST /api/categorias` | `GET/POST /admin/api/categorias` |
| `GET/POST /api/presupuestos` | `GET/POST /admin/api/presupuestos` |
| `GET /api/presupuestos/resumen` | `GET /admin/api/presupuestos/resumen` |
| `GET/POST /api/cuotas` | `GET/POST /admin/api/cuotas` |
| `GET /api/compartido` | `GET /admin/api/compartido` |
| `GET/POST /api/gastos-fijos` | `GET/POST /admin/api/gastos-fijos` |
| `GET/POST /api/usuarios` | `GET/POST /admin/api/usuarios` |

La cookie `finanzas_session` se propaga automaticamente.

## Tips

- **No mockear backend:** Los tests E2E corren contra el stack real. Los datos de test se crean y limpian dentro de cada test.
- **Isolacion:** Cada test debe limpiar lo que crea (borrar movimientos/categorias de test al final).
- **Nombres unicos:** Usar timestamps o random en nombres para evitar colisiones: `Test Cat ${Date.now()}`
- **Esperar navegacion:** Despues de click en nav link, esperar `page.waitForURL()`
- **Screenshots en fallo:** Configurado automaticamente en playwright.config.ts
