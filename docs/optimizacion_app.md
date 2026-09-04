# Plan de Optimización — Finanzas App

**Fecha:** 2026-09-03
**Objetivo:** Transformar la web en una experiencia tipo app móvil, con gestión inteligente de tarjetas de crédito, ingresos y proyecciones financieras.
**Producción:** https://contabilidad-n-d.duckdns.org

---

## Índice

1. [Rediseño UI/UX — Experiencia App](#1-rediseño-uiux--experiencia-app)
2. [Módulo de Tarjetas de Crédito](#2-módulo-de-tarjetas-de-crédito)
3. [Módulo de Ingresos Inteligente](#3-módulo-de-ingresos-inteligente)
4. [Inteligencia Financiera](#4-inteligencia-financiera)
5. [Modelo de Datos (Migraciones)](#5-modelo-de-datos-migraciones)
6. [Endpoints API](#6-endpoints-api)
7. [Orden de Ejecución](#7-orden-de-ejecución)

---

## 1. Rediseño UI/UX — Experiencia App

### 1.1 Login — Estilo App Nativa

**Estado actual:** Card centrada con campos usuario/password/2FA, fondo oscuro, logo texto.

**Nuevo diseño (basado en mockups del usuario):**
- Fondo limpio blanco/claro (no dark mode en login)
- Logo/icono de la app arriba (ilustración o icono grande)
- Título "Finanzas app" con subtítulo "Ingresa tus credenciales"
- Campos con bordes redondeados, estilo iOS/Material
- Inputs con labels flotantes o superiores
- Campo 2FA con placeholder "000000" y hint "Abre tu app de autenticación"
- Botón "Entrar" prominente, full-width
- Sin header/navegación visible

**Archivos a modificar:**
- `frontend/src/app/login/page.tsx` — Rediseño completo
- `frontend/src/app/globals.css` — Variables para light mode en login

### 1.2 Navegación — Menú Lateral tipo App

**Estado actual:** Header fijo horizontal con links en fila. En mobile: hamburguesa que despliega dropdown.

**Nuevo diseño (basado en mockups del usuario):**
- **Mobile:** Menú hamburguesa que abre un drawer/sidebar desde la izquierda
  - Fondo oscuro semi-transparente (overlay)
  - Panel lateral con logo arriba
  - Links con iconos a la izquierda: Dashboard, Movimientos, Compartido, Cuotas, Presupuestos, Categorías, **Tarjetas** (nuevo), **Ingresos** (nuevo)
  - Botón "Salir" al final
  - Animación slide-in desde la izquierda
- **Desktop:** Sidebar fija a la izquierda (240px), contenido a la derecha
  - Misma estructura que mobile pero siempre visible
  - Collapse opcional a solo iconos (64px)
- Header compacto: solo título de la página actual + avatar/nombre usuario

**Archivos a modificar:**
- `frontend/src/components/layout/header.tsx` — Reemplazar por Sidebar + TopBar
- Crear `frontend/src/components/layout/sidebar.tsx`
- Crear `frontend/src/components/layout/topbar.tsx`
- `frontend/src/app/layout.tsx` — Ajustar layout grid (sidebar + content)

### 1.3 Dashboard — Cards Visuales tipo App Financiera

**Estado actual:** KPI cards + gráficos en grid. Funcional pero estético de "admin panel".

**Nuevo diseño (basado en mockups del usuario):**
- **Cards de tarjetas:** Carousel horizontal con cards estilo tarjeta de crédito (gradiente, últimos 4 dígitos, saldo, logo banco)
- **KPIs:** Cards coloridas con bordes redondeados grandes
  - Ingreso (verde), Gastos (rojo/rosa), Balance (azul), Cuotas mes (naranja)
  - Cada card con icono, monto grande, etiqueta pequeña
- **Historial de pagos:** Timeline vertical con items recientes
- **Gasto por categoría:** Barras horizontales con colores vivos
- **Proyección:** Card tipo alerta con icono y datos en grid
- **Anomalías:** Card con borde accent (amarillo/naranja)

**Archivos a modificar:**
- `frontend/src/app/page.tsx` — Reorganizar layout
- `frontend/src/components/dashboard/` — Todos los componentes
- Crear `frontend/src/components/dashboard/card-carousel.tsx` — Carousel de tarjetas

### 1.4 Botón Flotante de Agregar Gasto

**Nuevo:** Botón FAB (Floating Action Button) en esquina inferior derecha.
- Icono "+" grande, color primario
- Al tocar: abre modal de nuevo gasto (mismo form actual pero con mejor UX)
- Visible en todas las páginas excepto login
- Con animación de aparición

**Archivos:**
- Crear `frontend/src/components/layout/fab.tsx`
- Integrar en `frontend/src/app/layout.tsx`

### 1.5 Tema Visual General

**Ajustes globales:**
- Border radius más grandes (16px en cards, 12px en inputs)
- Shadows suaves en cards (no solo bordes)
- Gradientes sutiles en headers de cards
- Transiciones suaves en todo (300ms ease)
- Espaciado más generoso (padding 20-24px en cards)
- Tipografía: tamaños más grandes para montos, más contraste
- Dark mode mejorado: fondos más cálidos, menos "admin panel"

**Archivos:**
- `frontend/src/app/globals.css` — Variables CSS actualizadas
- `frontend/tailwind.config.ts` — Extender tema

---

## 2. Módulo de Tarjetas de Crédito

### 2.1 Contexto Colombia

En Colombia:
- Cada tarjeta tiene su propia **fecha de corte** (día del mes donde cierra el extracto) y **fecha de pago** (día del mes donde vence el pago mínimo/total)
- La **tasa EA** (Efectiva Anual) es por tarjeta, no por compra. Sin embargo, promociones de establecimientos pueden ofrecer cuotas a 0% o tasas preferenciales
- Al diferir una compra, la primera cuota se cobra en el siguiente ciclo de facturación después del corte
- El pago mínimo incluye: cuotas vigentes + intereses de rotativo + seguros

### 2.2 Nuevo Modelo: TarjetaCredito

**Campos:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int PK | — |
| `user_id` | FK User | Dueño |
| `banco` | str | "Bancolombia", "Davivienda", "Nu", etc. |
| `nombre` | str | Nombre personalizado ("Visa Bancolombia", "Mastercard Nu") |
| `ultimos_4` | str(4) | Últimos 4 dígitos |
| `fecha_corte` | int (1-31) | Día del mes de corte |
| `fecha_pago` | int (1-31) | Día del mes de pago |
| `tasa_ea` | float | Tasa EA de la tarjeta (ej: 28.5) |
| `cupo_total_cop` | int | Cupo aprobado |
| `activa` | bool | Si está activa |

**Relación con CompraCuotas:**
- Agregar `tarjeta_id` (FK a TarjetaCredito) en CompraCuotas
- El campo `tarjeta` (texto libre actual) se reemplaza por la FK
- Al crear una compra, seleccionar de qué tarjeta es
- La tasa EA por defecto viene de la tarjeta, pero puede ser override por compra (promociones 0%)

### 2.3 Proyección Automática de Cuotas

**Problema actual:** Al crear una compra a 10 cuotas, el sistema solo guarda el total y las cuotas pagadas. No proyecta cuándo se paga cada cuota.

**Solución:** Al crear una CompaCuotas vinculada a una tarjeta:

1. Calcular `primera_cuota` basado en fecha de compra y fecha de corte:
   ```
   Si compra_dia <= fecha_corte del mes actual:
     primera_cuota = fecha_pago del mes actual
   Sino:
     primera_cuota = fecha_pago del mes siguiente
   ```

2. Generar calendario de pagos proyectados:
   ```
   Compra: $100.000 a 10 cuotas, corte: 8, pago: 25
   Compra hoy 3 sep → corte 8 sep → pago 25 sep (cuota 1)
   
   Cuota 1:  25 sep 2026 — $10.000
   Cuota 2:  25 oct 2026 — $10.000
   ...
   Cuota 10: 25 jun 2027 — $10.000
   ```

3. Mostrar en el dashboard: "Este mes debes pagar $X en cuotas de tarjeta Y"

### 2.4 Registro Automático de Pagos

**Flujo actual:** El usuario registra un pago manualmente con POST `/api/cuotas/{id}/pago`.

**Flujo mejorado:**
- En la vista de tarjetas, mostrar "Cuotas pendientes este mes" agrupadas por tarjeta
- Botón "Registrar pago de este mes" que marca automáticamente todas las cuotas del ciclo
- Al registrar, se crea un Movimiento por cada cuota pagada y se actualiza `cuotas_pagadas`
- Mostrar progreso: "Compra X: 2/10 cuotas pagadas" con barra visual

### 2.5 Vista de Tarjetas en Frontend

**Nueva página: `/tarjetas`**

**Sección 1 — Mis Tarjetas (carousel horizontal):**
- Cards estilo tarjeta de crédito con gradiente
- Mostrar: banco, nombre, últimos 4, próximo pago, total a pagar
- Botón "Agregar tarjeta"

**Sección 2 — Cuotas activas por tarjeta:**
- Expandir tarjeta para ver sus compras activas
- Cada compra muestra: establecimiento, progreso (3/10), valor cuota, saldo
- Botón "Registrar pago"

**Sección 3 — Proyección 6 meses:**
- Timeline/tabla mostrando por mes cuánto se debe pagar en cuotas
- Gráfico de barras apiladas: mes vs monto por tarjeta

---

## 3. Módulo de Ingresos Inteligente

### 3.1 Contexto Colombia

- **Ingresos fijos:** Salario (quincenal o mensual), arriendos recibidos
- **Ingresos variables:** Freelance, comisiones, ventas, bonos
- **Ingresos periódicos especiales:** Prima (junio), cesantías (enero/febrero), bonificaciones anuales
- **Quincenal vs mensual:** La mayoría de empleados colombianos cobran quincenal (día 15 y último día hábil)

### 3.2 Nuevo Modelo: IngresoRecurrente

**Campos:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int PK | — |
| `user_id` | FK User | — |
| `nombre` | str | "Salario Empresa X", "Freelance diseño" |
| `tipo` | str | "fijo" o "variable" |
| `frecuencia` | str | "mensual", "quincenal", "anual" |
| `monto_cop` | int | Monto base (para fijos) |
| `dia_pago_1` | int | Día del primer pago del mes (ej: 15) |
| `dia_pago_2` | int null | Día del segundo pago (ej: 30, solo quincenal) |
| `activo` | bool | — |

### 3.3 Onboarding Inteligente de Ingresos

**Flujo al crear usuario o al primer login:**

1. "¿Tus ingresos son fijos o variables?"
   - **Fijo:** Pedir monto, frecuencia (mensual/quincenal), y día(s) de pago
   - **Variable:** Pedir estimado mensual, recordar actualizar cada mes
   - **Mixto:** Permitir agregar múltiples fuentes (salario fijo + freelance variable)

2. Si es fijo quincenal:
   - "¿Cuánto recibes en cada quincena?" → Registrar como 2 pagos/mes
   - No necesita re-ingresarlo cada mes, se marca automáticamente

3. Si es variable:
   - Mostrar notificación al inicio de cada mes: "¿Cuánto esperas recibir este mes?"
   - Usar promedio de últimos 3 meses como sugerencia

### 3.4 Registro Automático de Ingresos Fijos

**Lógica:**
- Al llegar el día de pago, el sistema puede:
  - **Opción A (recomendada):** Mostrar banner "¿Recibiste tu salario de $X?" → Confirmar con un tap
  - **Opción B:** Auto-registrar como Movimiento tipo ingreso (más agresivo)
- Mantener historial: si el usuario confirma cada mes, el sistema aprende

### 3.5 Vista de Ingresos en Frontend

**Integrar en Dashboard o nueva sección:**
- Card "Ingresos del mes": fijo esperado vs recibido
- Si variable: mostrar promedio 3 meses como referencia
- Indicador: "Próximo ingreso: 15 sep (en 12 días)"

---

## 4. Inteligencia Financiera

### 4.1 Proyección de Flujo de Caja

**Nuevo en Dashboard:**
```
Ingresos esperados:     $4.500.000
- Gastos fijos:         $1.800.000
- Cuotas tarjetas:      $  450.000
- Gasto promedio flex:   $1.200.000
= Disponible estimado:  $1.050.000
```

**Lógica:**
- Ingresos: suma de IngresoRecurrente activos del mes
- Gastos fijos: suma de GastoFijo activos
- Cuotas: suma de cuotas proyectadas del mes (de todas las tarjetas)
- Gasto flexible: promedio últimos 3 meses de gastos no fijos
- Disponible: ingreso - fijos - cuotas - flexible

### 4.2 Alertas Inteligentes

| Alerta | Trigger | Acción |
|--------|---------|--------|
| Presupuesto al 80% | Gasto de categoría supera 80% del límite | Banner amarillo en dashboard |
| Gasto inusual | Gasto > 2x promedio histórico de su categoría | Card "Gastos inusuales" |
| Próximo pago tarjeta | Faltan ≤ 5 días para fecha de pago | Banner en dashboard |
| Cupo bajo | Saldo usado > 80% del cupo de tarjeta | Alerta en card de tarjeta |
| Ingreso pendiente | Día de pago llegó y no se confirmó ingreso | Banner "¿Recibiste tu salario?" |

### 4.3 Presupuesto 50/30/20 Adaptado

**Regla adaptada para Colombia:**
- **50% Necesidades:** Mercado, Servicios, Hogar, Transporte, Salud, Seguridad Social
- **30% Deseos:** Ocio, Suscripciones, GYM, Celular
- **20% Ahorro/Deuda:** Ahorro, pago de deudas, inversión

**Vista:** Donut con 3 segmentos + barras de progreso por sección.

### 4.4 Score de Salud Financiera

**Cálculo simple (0-100):**
- +25 pts: Gastos < 90% de ingresos
- +25 pts: Tiene fondo de emergencia (≥ 3 meses de gastos fijos)
- +25 pts: Deuda total < 30% de ingreso anual
- +25 pts: Cumple presupuestos del mes (≥ 80% dentro de límites)

**Vista:** Indicador circular con puntaje y recomendaciones.

---

## 5. Modelo de Datos (Migraciones)

### 5.1 Nueva tabla: `tarjetas_credito`

```sql
CREATE TABLE tarjetas_credito (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    banco TEXT NOT NULL,
    nombre TEXT NOT NULL,
    ultimos_4 VARCHAR(4),
    fecha_corte INTEGER NOT NULL CHECK (fecha_corte BETWEEN 1 AND 31),
    fecha_pago INTEGER NOT NULL CHECK (fecha_pago BETWEEN 1 AND 31),
    tasa_ea FLOAT,
    cupo_total_cop INTEGER,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (user_id, nombre)
);
```

### 5.2 Nueva tabla: `ingresos_recurrentes`

```sql
CREATE TABLE ingresos_recurrentes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('fijo', 'variable')),
    frecuencia TEXT NOT NULL CHECK (frecuencia IN ('mensual', 'quincenal', 'semanal', 'anual')),
    monto_cop INTEGER NOT NULL,
    dia_pago_1 INTEGER CHECK (dia_pago_1 BETWEEN 1 AND 31),
    dia_pago_2 INTEGER CHECK (dia_pago_2 BETWEEN 1 AND 31),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (user_id, nombre)
);
```

### 5.3 Modificar tabla: `compras_cuotas`

```sql
ALTER TABLE compras_cuotas
    ADD COLUMN tarjeta_id INTEGER REFERENCES tarjetas_credito(id),
    ADD COLUMN fecha_primera_cuota DATE,
    ADD COLUMN tasa_ea_override FLOAT;  -- Para promociones 0%

-- Migrar datos existentes: campo tarjeta (texto) a tarjeta_id donde sea posible
-- Mantener campo tarjeta (texto) por compatibilidad temporal
```

### 5.4 Mantener sin cambios

- `users` — Solo agregar relaciones a tarjetas e ingresos
- `movimientos` — Sin cambios de esquema
- `categorias`, `presupuestos`, `gastos_fijos`, `deudas`, `audit_log` — Sin cambios

---

## 6. Endpoints API

### 6.1 Tarjetas de Crédito

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/tarjetas` | Listar tarjetas del usuario |
| POST | `/api/tarjetas` | Crear tarjeta |
| PATCH | `/api/tarjetas/{id}` | Actualizar tarjeta |
| DELETE | `/api/tarjetas/{id}` | Desactivar/eliminar tarjeta |
| GET | `/api/tarjetas/{id}/proyeccion` | Proyección de cuotas por mes (6-12 meses) |
| GET | `/api/tarjetas/{id}/estado-cuenta` | Estado de cuenta del ciclo actual |

### 6.2 Ingresos Recurrentes

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/ingresos` | Listar ingresos configurados |
| POST | `/api/ingresos` | Crear ingreso recurrente |
| PATCH | `/api/ingresos/{id}` | Actualizar |
| DELETE | `/api/ingresos/{id}` | Desactivar/eliminar |
| GET | `/api/ingresos/resumen?mes=YYYY-MM` | Ingresos esperados vs recibidos del mes |

### 6.3 Inteligencia Financiera

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/flujo-caja?mes=YYYY-MM` | Proyección de flujo de caja del mes |
| GET | `/api/salud-financiera` | Score de salud financiera |
| GET | `/api/alertas` | Alertas activas (presupuesto, pagos, inusuales) |

---

## 7. Orden de Ejecución

### Sprint 1 — UI/UX Base (Prioridad Alta)

**Objetivo:** Transformar la experiencia visual de "admin panel" a "app móvil".

| # | Tarea | Archivos | Estimación |
|---|-------|----------|------------|
| 1.1 | Rediseñar Login (fondo claro, estilo iOS) | `login/page.tsx`, `globals.css` | — |
| 1.2 | Implementar Sidebar navigation (mobile drawer + desktop fixed) | `sidebar.tsx`, `topbar.tsx`, `header.tsx`, `layout.tsx` | — |
| 1.3 | FAB (botón flotante agregar gasto) | `fab.tsx`, `layout.tsx` | — |
| 1.4 | Actualizar tema global (radius, shadows, spacing, gradients) | `globals.css`, componentes | — |
| 1.5 | Rediseñar Dashboard cards (estilo app financiera) | `page.tsx`, `kpi-cards.tsx` | — |

**Criterio de éxito:** La app se ve y se siente como una app móvil nativa.

### Sprint 2 — Módulo Tarjetas de Crédito (Prioridad Alta)

| # | Tarea | Archivos |
|---|-------|----------|
| 2.1 | Crear modelo TarjetaCredito + migración Alembic | `models.py`, migración |
| 2.2 | Agregar `tarjeta_id` a CompraCuotas + migración | `models.py`, migración |
| 2.3 | Crear servicio `services/tarjetas.py` (CRUD + proyección) | `tarjetas.py` |
| 2.4 | Crear endpoints API tarjetas en `admin/router.py` | `router.py` |
| 2.5 | Frontend: página `/tarjetas` con carousel + compras + proyección | `tarjetas/page.tsx` |
| 2.6 | Modificar form de movimientos: seleccionar tarjeta al registrar TC | `movimientos/page.tsx` |
| 2.7 | Modificar form de cuotas: vincular a tarjeta | `cuotas/page.tsx` |
| 2.8 | Lógica de proyección: calcular calendario de cuotas por mes | `tarjetas.py` |
| 2.9 | Tests: tarjetas CRUD + proyección + vinculación cuotas | `test_tarjetas.py` |

**Criterio de éxito:** El usuario puede crear tarjetas, registrar compras diferidas y ver un calendario de pagos futuros.

### Sprint 3 — Módulo Ingresos (Prioridad Media)

| # | Tarea | Archivos |
|---|-------|----------|
| 3.1 | Crear modelo IngresoRecurrente + migración | `models.py`, migración |
| 3.2 | Crear servicio `services/ingresos.py` | `ingresos.py` |
| 3.3 | Crear endpoints API ingresos | `router.py` |
| 3.4 | Frontend: sección de ingresos en dashboard o página dedicada | `ingresos/page.tsx` o `page.tsx` |
| 3.5 | Onboarding: wizard al primer login para configurar ingresos | `onboarding/page.tsx` o modal |
| 3.6 | Banner "¿Recibiste tu salario?" en día de pago | Dashboard banner |
| 3.7 | Tests | `test_ingresos.py` |

**Criterio de éxito:** El usuario configura sus ingresos una vez y el sistema los proyecta automáticamente.

### Sprint 4 — Inteligencia Financiera (Prioridad Media)

| # | Tarea | Archivos |
|---|-------|----------|
| 4.1 | Endpoint flujo de caja: ingresos - fijos - cuotas - flexible | `services/inteligencia.py` |
| 4.2 | Card de flujo de caja en dashboard | `dashboard/cashflow-card.tsx` |
| 4.3 | Sistema de alertas (presupuesto, pagos, inusuales) | `services/alertas.py` |
| 4.4 | Vista de alertas en dashboard (banners/cards) | `dashboard/alertas.tsx` |
| 4.5 | Presupuesto 50/30/20 visual | `dashboard/presupuesto-5030.tsx` |
| 4.6 | Score de salud financiera | `services/salud.py`, `dashboard/score.tsx` |
| 4.7 | Tests | `test_inteligencia.py` |

**Criterio de éxito:** El dashboard muestra proyecciones, alertas y score sin que el usuario tenga que calcular nada.

### Sprint 5 — Polish y Detalles

| # | Tarea |
|---|-------|
| 5.1 | Animaciones y transiciones (slide, fade, scale) |
| 5.2 | Skeleton loaders en lugar de "Cargando..." |
| 5.3 | Pull-to-refresh en mobile |
| 5.4 | Swipe en cards del carousel de tarjetas |
| 5.5 | PWA: manifest.json + service worker para instalar en home |
| 5.6 | Haptic feedback visual (vibración de botones al tocar) |
| 5.7 | Tests E2E Playwright actualizados |

---

## Resumen Visual del Cambio

```
ANTES (Admin Panel):
┌─────────────────────────────────┐
│ [Logo] [Link] [Link] [Link]... │  ← Header horizontal
├─────────────────────────────────┤
│                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐      │  ← Cards planas
│  │ KPI │ │ KPI │ │ KPI │      │
│  └─────┘ └─────┘ └─────┘      │
│                                 │
│  ┌────────────────────────┐    │  ← Tablas densas
│  │ Tabla de movimientos   │    │
│  └────────────────────────┘    │
└─────────────────────────────────┘

DESPUÉS (App Móvil):
┌──────┬──────────────────────────┐
│      │ Dashboard         [👤]  │  ← TopBar compacta
│  ☰   ├──────────────────────────┤
│      │                          │
│ 📊   │  ┌─ ─ ─ ─ ─ ─ ─ ─ ─┐  │  ← Carousel tarjetas
│ 💰   │  │ Visa ●●●● 2408   │  │
│ 👥   │  │ Saldo: $1.2M     │  │
│ 💳   │  └─ ─ ─ ─ ─ ─ ─ ─ ─┘  │
│ 📈   │                          │
│ 🏷   │  ┌────────┐ ┌────────┐  │  ← Cards coloridas
│      │  │Ingreso │ │Gastos  │  │
│ 🚪   │  │$4.5M ↑ │ │$3.2M ↓│  │
│      │  └────────┘ └────────┘  │
│      │                     [+] │  ← FAB
└──────┴──────────────────────────┘
         Sidebar    Contenido
```

---

## Lo que NO cambia

| Componente | Razón |
|-----------|-------|
| Backend FastAPI | Arquitectura sólida, solo se agregan endpoints |
| PostgreSQL + Alembic | Se agregan tablas, no se cambia motor |
| Auth cookies + TOTP | Seguro y funcional |
| Parser LLM + regex | No aplica a la web (era para WhatsApp) |
| Docker Compose | Solo se rebuilds |
| Servicios existentes | `comandos.py`, `balance.py`, `presupuesto.py` — intactos |
| Tests existentes | Se agregan nuevos, no se modifican los 74 actuales |
