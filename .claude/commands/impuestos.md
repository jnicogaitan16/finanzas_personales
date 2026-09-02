# Skill: Impuestos Colombia (DIAN)

Eres experto en el sistema tributario colombiano aplicado a personas naturales, ayudando al usuario a rastrear deducciones y prepararse para la declaracion de renta.

## Obligacion de declarar renta (2026, verificar umbrales actualizados)

Una persona natural DEBE declarar si cumple CUALQUIERA de estos:
- Ingresos brutos anuales > ~$65.000.000 (1.400 UVT aprox)
- Patrimonio bruto > ~$222.000.000 (4.500 UVT aprox)
- Consumos con tarjeta de credito > ~$65.000.000
- Compras y consumos totales > ~$65.000.000
- Consignaciones bancarias > ~$65.000.000

**Nota**: Los umbrales cambian cada ano con la UVR/UVT. Verificar en www.dian.gov.co.

## Calendario tributario DIAN

- **Marzo-Abril**: publican calendario
- **Agosto-Octubre**: vencimientos declaracion renta personas naturales (segun NIT)
- **Enero**: pago segunda cuota (si aplica)

## Deducciones rastreables con el bot

El bot registra gastos que pueden ser deducibles:

### Salud (categoria Salud en el bot)
- Medicina prepagada: deducible hasta 16 UVT mensuales
- Consultas medicas particulares: no directamente, pero soportan la deduccion por dependientes

### Vivienda (categoria Servicios)
- Intereses de credito hipotecario: deducible hasta 1.200 UVT anuales
- Arriendo: NO es deducible directamente para empleados

### Educacion
- Agregar categoria "Educacion" al bot para rastrear
- No es deducible directamente pero puede aplicar para dependientes

### Aportes voluntarios
- AFC: hasta 30% del ingreso (max 3.800 UVT) - no pasa por el bot pero se puede registrar como categoria
- Pensiones voluntarias: hasta 25% del ingreso (max 2.500 UVT)

## Retencion en la fuente

- Se descuenta del salario si supera umbral (~$5.200.000 mensuales, 2026 aprox)
- El empleador la hace automaticamente
- Se puede optimizar presentando certificados de dependientes, medicina prepagada, intereses hipotecarios

## GMF (4x1000)

- 0.4% sobre retiros bancarios
- Exencion: una cuenta marcada como exenta del GMF (pedir en el banco)
- Nequi/Daviplata: generalmente exentos en montos pequenos

## IVA relevante

- IVA general: 19%
- Sin IVA: canasta familiar basica, educacion, salud
- IVA diferencial 5%: algunos alimentos procesados

## Como el bot ayuda con impuestos

### Rastreo automatico de deducciones
1. Gastos en **Salud** -> potencial deduccion por medicina prepagada
2. Gastos en **Servicios** (arriendo, intereses hipotecarios) -> deduccion vivienda
3. Registrar ingresos de **Salario** -> base para calcular si supera umbrales

### Reporte sugerido para declaracion

```sql
-- Gastos por categoria en el ano fiscal
SELECT c.nombre, SUM(m.monto_cop) as total
FROM movimientos m
JOIN categorias c ON m.categoria_id = c.id
WHERE m.user_id = :user_id
  AND m.fecha_gasto BETWEEN '2026-01-01' AND '2026-12-31'
  AND m.eliminado_en IS NULL
GROUP BY c.nombre
ORDER BY total DESC;

-- Ingresos totales del ano
SELECT SUM(m.monto_cop) as total_ingresos
FROM movimientos m
JOIN categorias c ON m.categoria_id = c.id
WHERE m.user_id = :user_id
  AND c.tipo = 'ingreso'
  AND m.fecha_gasto BETWEEN '2026-01-01' AND '2026-12-31'
  AND m.eliminado_en IS NULL;
```

### Alertas utiles

- "Tus ingresos del ano suman $X. El umbral de declaracion es $65M."
- "Llevas $X en Salud este ano. Recuerda que medicina prepagada es deducible."
- "Diciembre: prepara certificados de retencion para la declaracion."

## Categorias sugeridas para agregar

Para mejorar el rastreo tributario, considerar agregar:
- **Educacion**: matriculas, cursos, libros
- **Ahorro**: AFC, pensiones voluntarias, CDTs
- **Deuda**: pagos de credito hipotecario (intereses son deducibles)

## Disclaimer

Este skill provee contexto general. Para la declaracion de renta real, consultar con un contador publico. Los umbrales y reglas cambian anualmente.
