# Plan de Trabajo — Finanzas App v2

**Fecha:** 2026-09-04
**Objetivo:** Reestructurar la app para una experiencia mobile-first simplificada, corregir bugs críticos, deprecar código huérfano y alinear estilos al tema oscuro/púrpura de la referencia.

---

## Paleta de Colores (basada en referencia Banking App)

```
Fondo principal:    #0A0E1A (azul muy oscuro / casi negro)
Fondo cards:        #141832 (azul oscuro profundo)
Fondo secundario:   #1C2145 (azul medio)
Acento primario:    #7C3AED (violeta/púrpura)
Acento secundario:  #A855F7 (púrpura claro)
Acento terciario:   #06B6D4 (cyan)
Positivo/Ingreso:   #34D399 (emerald)
Negativo/Gasto:     #FB7185 (rose)
Alerta:             #FBBF24 (amber)
Texto principal:    #F1F5F9 (blanco suave)
Texto secundario:   #94A3B8 (gris)
Bordes:             rgba(255,255,255,0.08)
```

---

## Auditoría — Estado Actual

### Bugs Críticos Encontrados

| # | Bug | Causa Raíz | Severidad |
|---|-----|-----------|-----------|
| 1 | **Compra TC muestra monto total en gastos** | `crear_compra()` crea Movimiento por el total ($1M), no por la cuota mensual ($100K). El dashboard lo cuenta como gasto del mes. | ALTA |
| 2 | **Salario fijo no aparece en balance** | `sincronizar_ingresos_fijos` crea el Movimiento con fecha futura (día 30/31). El dashboard debería mostrar el ingreso esperado, no solo el recibido. | MEDIA |
| 3 | **Código de invitación no funciona** | Frontend llama `POST /api/grupo` pero no pasa el body vacío correctamente, o la sesión del grupo no se refresca al generar. | BAJA |

### Código Huérfano (a eliminar)

| Archivo | Líneas | Razón |
|---------|--------|-------|
| `services/registro.py` | 129 | WhatsApp message processor (removido) |
| `services/comandos.py` | 626 | WhatsApp command parser (removido) |
| `services/resultado.py` | ~14 | DTO para webhook (removido) |
| `cache.py` pendientes | ~50 | Cache de comandos WhatsApp |
| `components/layout/header.tsx` | ~103 | Header viejo (reemplazado por sidebar) |
| `components/layout/header-wrapper.tsx` | ~10 | Wrapper del header viejo |
| `components/dashboard/category-bar.tsx` | ~50 | Reemplazado por category-donut |
| `components/dashboard/distribution-donut.tsx` | ~60 | Reemplazado por category-donut |
| Tests de comandos que usan `procesar_mensaje` | ~400 | Tests del parser WhatsApp |

**Total: ~1,440 líneas de código muerto**

### Funcionalidades Activas (mantener)

- Auth por usuario (bcrypt, sesiones, grupos familiares)
- CRUD movimientos, categorías, usuarios
- Tarjetas de crédito (modelo, CRUD, proyección)
- Ingresos recurrentes (fijo/variable, auto-sync)
- Cuotas TDC (compras diferidas, pagos, progreso)
- Gastos fijos (recurrentes mensuales)
- Presupuestos (límites por categoría)
- Compartido (balance entre miembros del hogar)
- Inteligencia (flujo de caja, alertas, score)
- Deudas

---

## Estructura de Vistas Propuesta

### 1. Login (`/login`)

```
┌─────────────────────────┐
│                         │
│    [Logo Finanzas App]  │
│                         │
│    ┌─────────────────┐  │
│    │  Usuario         │  │
│    └─────────────────┘  │
│    ┌─────────────────┐  │
│    │  Contraseña      │  │
│    └─────────────────┘  │
│                         │
│    [ Entrar ]           │
│                         │
│    ¿No tienes cuenta?   │
│    Crear cuenta         │
│                         │
│    ¿Olvidaste tu clave? │
│    Restablecer           │
└─────────────────────────┘
```

**Acciones:** Login, Registro (con código invitación), Restablecer contraseña.
**Estilo:** Fondo oscuro (#0A0E1A), inputs con bordes púrpura, botón gradiente púrpura.

### 2. Vista Principal (`/`) — SIN sidebar

```
┌─────────────────────────┐
│ Finanzas app    [👤] [⚙]│  ← TopBar: logo + avatar + settings
├─────────────────────────┤
│                         │
│  Balance del mes        │
│  $1.820.000             │  ← Grande, central, color según +/-
│                         │
│  ← Sep 2026 →           │  ← Selector de mes
│                         │
│  ┌──────┐ ┌──────┐     │
│  │Ingre │ │Gasto │     │  ← 2 cards principales (clickeables)
│  │$5.0M │ │$3.1M │     │
│  └──────┘ └──────┘     │
│                         │
│  ┌──────┐ ┌──────┐     │
│  │ TC   │ │Compar│     │  ← 2 cards módulos (clickeables)
│  │$450K │ │$200K │     │
│  └──────┘ └──────┘     │
│                         │
│  ── ¿En qué gastas? ── │
│  Hogar ████████ 30%     │
│  Tarjeta ██████ 25%     │  ← Barras de categoría con %
│  Transporte ███ 10%     │
│                         │
│  ── Últimos movimientos │
│  ▸ Uber   -$12.000     │
│  ▸ Salario +$5.000.000  │
│                     [+] │  ← FAB agregar gasto
└─────────────────────────┘
```

**Sin sidebar lateral.** Toda la navegación desde esta vista:
- **Logo (arriba izq):** Toca → vuelve aquí
- **Avatar (arriba der):** Toca → menú desplegable: Mi cuenta, Cerrar sesión
- **Cards de módulos:** Tocar → navega a la sub-vista
- **FAB (+):** Agregar gasto rápido

### 3. Sub-vistas (al tocar un módulo)

Cada módulo se abre como vista completa con back button:

```
┌─────────────────────────┐
│ ← Ingresos             │  ← Back arrow + título
├─────────────────────────┤
│ [contenido del módulo]  │
└─────────────────────────┘
```

**Módulos:**
- `/ingresos` — Ingresos fijos + variables + historial del mes
- `/movimientos` — Gastos con filtros, CRUD, export
- `/tarjetas` — Cards TC + compras activas + proyección
- `/compartido` — Balance compartido entre miembros del hogar

**Accesibles desde settings/cuenta:**
- `/cuenta` — Mi perfil, grupo familiar, invitación, contraseña
- `/categorias` — Gestión de categorías
- `/presupuestos` — Límites por categoría
- `/gastos-fijos` — Gastos recurrentes

---

## Plan de Ejecución

### Sprint 1 — Limpieza y Bugs Críticos

**Objetivo:** Eliminar código muerto, corregir los 3 bugs, estabilizar.

| # | Tarea | Archivos |
|---|-------|----------|
| 1.1 | Eliminar `services/registro.py`, `comandos.py`, `resultado.py` | Backend services |
| 1.2 | Limpiar `cache.py` (quitar pendientes, dejar solo msg_ya_visto) | `cache.py` |
| 1.3 | Eliminar `tests/test_comandos.py` (tests del parser WhatsApp) | Backend tests |
| 1.4 | Eliminar componentes frontend huérfanos: `header.tsx`, `header-wrapper.tsx`, `category-bar.tsx`, `distribution-donut.tsx` | Frontend components |
| 1.5 | **Fix Bug TC:** No crear Movimiento por monto total al crear compra TC. Solo registrar cuotas mensuales. | `services/cuotas.py` |
| 1.6 | **Fix Bug Salario:** Mostrar ingreso fijo como "esperado" en el mes aunque fecha sea futura. Ajustar dashboard para sumar ingresos esperados. | `services/ingresos.py`, `page.tsx` |
| 1.7 | **Fix Bug Invitación:** Debuggear y corregir el flujo de código de invitación. | `cuenta/page.tsx`, `grupo/route.ts`, `router.py` |
| 1.8 | Tests: verificar que los 97+ tests siguen pasando después de limpieza | Todos |

### Sprint 2 — Nuevo Tema Visual (Púrpura/Oscuro)

**Objetivo:** Cambiar toda la paleta de colores al tema Banking App.

| # | Tarea | Archivos |
|---|-------|----------|
| 2.1 | Actualizar CSS variables en `globals.css` con la nueva paleta | `globals.css` |
| 2.2 | Login: fondo oscuro, inputs con bordes púrpura, botón gradiente | `login/page.tsx` |
| 2.3 | KPI Cards: gradientes púrpura/cyan en lugar de emerald/rose | `kpi-cards.tsx` |
| 2.4 | Dashboard cards: fondo `#141832`, bordes sutiles | Todos los dashboard components |
| 2.5 | Donut/Charts: colores de la nueva paleta | `category-donut.tsx`, `trend-line.tsx` |
| 2.6 | Dialogs: fondo oscuro en lugar de blanco | `globals.css` portal overrides |
| 2.7 | Score ring: gradiente púrpura en lugar de emerald | `score-card.tsx` |
| 2.8 | FAB: gradiente púrpura | `fab.tsx` |

### Sprint 3 — Reestructurar Layout (Quitar Sidebar)

**Objetivo:** Reemplazar sidebar por vista principal con módulos.

| # | Tarea | Archivos |
|---|-------|----------|
| 3.1 | Eliminar `sidebar.tsx` y `topbar.tsx` actuales | Layout components |
| 3.2 | Crear nuevo `topbar-v2.tsx`: logo izq + avatar/menú der (dropdown: Mi cuenta, Cerrar sesión) | Nuevo componente |
| 3.3 | Actualizar `app-shell.tsx`: sin sidebar, solo topbar + content + FAB | `app-shell.tsx` |
| 3.4 | Rediseñar Dashboard (`page.tsx`): balance central + 4 cards módulo clickeables + categorías % + últimos movimientos | `page.tsx` |
| 3.5 | Agregar back button en todas las sub-vistas | Cada page.tsx de módulo |
| 3.6 | Avatar menú dropdown: Mi cuenta, Categorías, Presupuestos, Gastos fijos, Cerrar sesión | `topbar-v2.tsx` |

### Sprint 4 — Lógica de TC Inteligente

**Objetivo:** Que al registrar compra TC, se difiera correctamente.

| # | Tarea | Archivos |
|---|-------|----------|
| 4.1 | Al crear compra TC: NO crear Movimiento por total. Calcular calendario de cuotas basado en fecha corte/pago de la tarjeta. | `services/cuotas.py` |
| 4.2 | Mostrar en dashboard: cuotas del mes actual como gasto proyectado, no el total de la compra | `page.tsx`, `inteligencia.py` |
| 4.3 | Vista tarjetas: mostrar próximo pago y cuotas del ciclo actual | `tarjetas/page.tsx` |
| 4.4 | Al seleccionar medio de pago "TC" en movimientos: auto-seleccionar tarjeta, pedir número de cuotas, no registrar como gasto directo | `movimientos/page.tsx` |

### Sprint 5 — Ingresos Inteligentes

**Objetivo:** Que los ingresos fijos se reflejen correctamente.

| # | Tarea | Archivos |
|---|-------|----------|
| 5.1 | Ingresos fijos: crear Movimiento con fecha del día de pago, pero mostrarlo como "esperado" si es futuro | `services/ingresos.py` |
| 5.2 | Dashboard: mostrar ingreso esperado + recibido separados | `page.tsx`, KPI cards |
| 5.3 | Card de ingresos en vista principal: mostrar ingreso esperado vs recibido del mes | Dashboard |

### Sprint 6 — Alinear Estilos Sub-vistas

**Objetivo:** Todas las sub-vistas con el mismo estilo app móvil.

| # | Tarea | Archivos |
|---|-------|----------|
| 6.1 | Movimientos: estilo cards oscuras, bordes púrpura, back button | `movimientos/page.tsx` |
| 6.2 | Tarjetas: cards con gradiente púrpura/azul | `tarjetas/page.tsx` |
| 6.3 | Ingresos: estilo unificado | `ingresos/page.tsx` |
| 6.4 | Compartido: estilo unificado | `compartido/page.tsx` |
| 6.5 | Cuenta: estilo unificado, form inputs oscuros | `cuenta/page.tsx` |
| 6.6 | Presupuestos, Gastos fijos, Categorías: estilo unificado | Cada page.tsx |
| 6.7 | Dialogs/Modals: fondo oscuro (#141832) en lugar de blanco | `globals.css` |

### Sprint 7 — Tests y Deploy

| # | Tarea | Archivos |
|---|-------|----------|
| 7.1 | Actualizar tests backend por cambios en lógica TC e ingresos | Tests |
| 7.2 | Actualizar E2E tests por cambio de layout (sin sidebar) | Playwright tests |
| 7.3 | Build final, verificar 0 errores | Docker |
| 7.4 | Deploy a producción | GitHub Actions |
| 7.5 | Seedear usuarios en producción con passwords | SSH a Oracle Cloud |

---

## Documentación a Deprecar

| Archivo | Acción |
|---------|--------|
| `docs/plan-deprecar-whatsapp.md` | Eliminar (ya ejecutado) |
| `docs/optimizacion_app.md` | Eliminar (reemplazado por este plan) |
| `docs/plan-proyecto-finanzas-whatsapp.md` | Actualizar nombre y contenido (quitar referencias WhatsApp) |

---

## Criterios de Éxito

- [ ] Sin sidebar — toda navegación desde vista principal
- [ ] Tema púrpura/oscuro consistente en todas las vistas
- [ ] Compra TC de $1M a 10 cuotas muestra $100K/mes en gastos (no $1M)
- [ ] Salario fijo de $5M se refleja en balance del mes
- [ ] Código de invitación funciona end-to-end
- [ ] 0 código huérfano de WhatsApp
- [ ] 0 componentes sin usar
- [ ] Todos los tests pasando
- [ ] Deploy exitoso en producción
- [ ] La app se ve y se siente como una app móvil nativa
