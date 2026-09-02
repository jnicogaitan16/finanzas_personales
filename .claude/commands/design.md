# Skill: Diseno UI/UX + Dashboard

Eres experto en diseno visual y UX para este proyecto de finanzas personales.

## Design system actual

### Paleta de colores (dark theme)

```css
:root {
  --bg: #0f1115;      /* fondo principal, casi negro */
  --card: #181c24;    /* fondo tarjetas, tablas, modals */
  --line: #2a3140;    /* bordes, separadores */
  --txt: #eef1f6;     /* texto principal, blanco suave */
  --muted: #93a0b5;   /* texto secundario, hints */
  --acc: #6ee7b7;     /* acento principal, verde menta */
  --danger: #f87171;  /* rojo para borrar, errores */
  --warn: #fbbf24;    /* amarillo para warnings */
}
```

### Colores por tipo de dato financiero

- Gastos: `#fda4af` (rosa suave)
- Ingresos: `#6ee7b7` (verde menta = --acc)
- Neutro/total: `--txt` (blanco)

### Tipografia

- Font: `ui-sans-serif, system-ui, sans-serif`
- Numeros: `font-variant-numeric: tabular-nums` (clase `.mono`)
- Formato COP: `$15.300` (punto como separador de miles, sin decimales)

### Componentes implementados

- **Botones**: `.btn` (transparente), `.btn.primary` (verde), `.btn.danger` (rojo borde)
- **Tablas**: fondo `--card`, headers `--muted` uppercase, filas con borde `--line`
- **Inputs**: fondo `--bg`, borde `--line`, focus `--acc`
- **Dialogs**: `<dialog>` nativo, backdrop oscuro, border-radius 12px
- **Cards**: fondo `--card`, border-radius 16px, padding 2rem

### Responsive

- Max width: 1200px centrado
- Min width inputs: 8rem
- Toolbars con `flex-wrap: wrap`
- Cards/forms: `width: min(480px, 92vw)`

## Dashboard Streamlit (a implementar)

### Convenciones de graficos

- **Barras**: gasto por categoria mensual (horizontal, colores por categoria)
- **Donut/Pie**: distribucion de gasto del mes actual
- **Lineas**: tendencia mensual (gasto total por mes, ultimos 6-12 meses)
- **KPIs**: cards grandes arriba (gasto total mes, ingreso, balance, % vs mes anterior)
- **Tabla**: ultimos movimientos con filtros

### Paleta para graficos (categorias)

```python
COLORES_CATEGORIA = {
    "Mercado": "#6ee7b7",      # verde menta
    "Transporte": "#93c5fd",   # azul claro
    "Servicios": "#c4b5fd",    # morado claro
    "Ocio": "#fda4af",         # rosa
    "Salud": "#fdba74",        # naranja
    "Otros": "#94a3b8",        # gris
    "Salario": "#86efac",      # verde claro
}
```

### Layout Streamlit

```
[KPI: Gasto mes] [KPI: Ingreso mes] [KPI: Balance] [KPI: % vs anterior]
[--------- Grafico barras por categoria ---------]
[--- Donut distribucion ---] [--- Linea tendencia ---]
[------------- Tabla ultimos movimientos ----------------]
```

### Streamlit config

- Theme: dark (custom CSS inyectado)
- Sidebar: filtros (usuario, rango fechas, categoria)
- Auto-refresh: cada 30 segundos
- Conexion directa a PostgreSQL (read-only)

## Principios de diseno

1. **Dark-first**: todo el proyecto usa dark theme, no hay light mode
2. **Datos primero**: los numeros son los protagonistas, no la decoracion
3. **COP siempre**: formato `$15.300` sin decimales
4. **Mobile-friendly**: los mensajes de WhatsApp se envian desde el telefono
5. **Accesible**: contraste suficiente, tamaños legibles, no depender solo del color
