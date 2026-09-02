# Skill: Presupuesto 50/30/20 para Colombia

Eres experto en presupuesto personal adaptado al contexto colombiano.

## Regla 50/30/20 adaptada a Colombia

### 50% — Necesidades (gastos fijos e indispensables)

Categorias del bot que aplican:
- **Servicios**: arriendo, administracion, luz, agua, gas, internet, celular
- **Mercado**: supermercado, mercado semanal (no restaurantes)
- **Transporte**: TransMilenio/SITP diario, gasolina para ir al trabajo
- **Salud**: EPS (si no la descuentan de nomina), medicinas esenciales

### 30% — Deseos (gastos variables, no esenciales)

Categorias del bot que aplican:
- **Ocio**: Netflix, Spotify, cine, bares, restaurantes, salidas
- **Mercado**: almuerzos ejecutivos, domicilios, comida premium
- **Transporte**: Uber/Didi (cuando hay TransMilenio como alternativa)
- **Otros**: ropa, gadgets, suscripciones no esenciales

### 20% — Ahorro, inversion y deudas

No tiene categoria directa en el bot (es lo que NO se gasta):
- Fondo de emergencia
- CDTs, FICs, pensiones voluntarias
- Pago extra de deudas (cuota + abono a capital)
- Metas de ahorro (vacaciones, carro, apartamento)

## Como implementar en el bot

### Mapeo categorias -> buckets

```python
BUCKET_NECESIDADES = {"Servicios", "Salud"}
BUCKET_DESEOS = {"Ocio"}
# Mercado y Transporte se dividen (estimacion o keywords):
# - Mercado base -> Necesidades
# - Restaurantes/domicilios -> Deseos
# - TransMilenio/SITP -> Necesidades
# - Uber/Didi -> Deseos
BUCKET_MIXTO = {"Mercado", "Transporte"}
```

### Formulas

```python
ingreso_mensual = sum(movimientos tipo='ingreso' del mes)
gasto_necesidades = sum(movimientos bucket='necesidades' del mes)
gasto_deseos = sum(movimientos bucket='deseos' del mes)
ahorro_real = ingreso_mensual - gasto_necesidades - gasto_deseos

pct_necesidades = gasto_necesidades / ingreso_mensual * 100
pct_deseos = gasto_deseos / ingreso_mensual * 100
pct_ahorro = ahorro_real / ingreso_mensual * 100
```

### Alertas sugeridas

- Necesidades > 55%: "Tus gastos fijos consumen mas del 55% de tus ingresos"
- Deseos > 35%: "Llevas mas del 35% en gastos no esenciales"
- Ahorro < 15%: "Este mes solo estas ahorrando el X%. La meta es 20%"

## Tabla de presupuesto (ya en DB)

```sql
-- Tabla presupuestos (existe pero no tiene logica)
presupuestos (user_id, categoria_id, monto_limite_cop, mes_vigente)
```

### Logica a implementar

1. **Comando WhatsApp**: "presupuesto mercado 500 mil" -> crea/actualiza presupuesto
2. **Alerta al registrar**: si el gasto del mes en esa categoria supera el 80% del presupuesto
3. **Resumen semanal**: "Llevas $380K/$500K en Mercado (76%)"

## Ejemplo con datos reales

Si el ingreso es $3.000.000:
- Necesidades (50%): $1.500.000 max
  - Arriendo: $1.000.000
  - Servicios: $200.000
  - TransMi: $120.000
  - Mercado base: $180.000
- Deseos (30%): $900.000 max
  - Restaurantes: $200.000
  - Ocio: $150.000
  - Uber: $100.000
  - Otros: $150.000
- Ahorro (20%): $600.000 min
  - Fondo emergencia: $300.000
  - CDT/FIC: $300.000

## Contexto colombiano especifico

- **Prima y cesantias**: ingreso extra en junio y diciembre. No incluir en el presupuesto mensual base.
- **Quincena**: muchos colombianos cobran quincenal, no mensual. El presupuesto debe ser mensual pero los registros pueden ser quincenales.
- **Temporada escolar**: enero/febrero gastos extras en utiles y matriculas.
- **Diciembre**: gastos significativamente mayores (regalos, fiestas, viajes).
