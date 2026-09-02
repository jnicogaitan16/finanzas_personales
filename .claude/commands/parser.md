# Skill: Parser de mensajes financieros

Eres experto en el parser de mensajes de gastos/ingresos en espanol colombiano de este proyecto.

## Contexto

El parser vive en `backend/parser/` y extrae monto, categoria, descripcion y fecha de mensajes como:
- "gaste 15.300 en almuerzo"
- "15 mil en uber"
- "me pagaron 3 millones"
- "ayer taxi 12000"

## Archivos clave

- `parser/fallback_regex.py` — Parser principal con regex
- `parser/categorias.py` — Keywords por categoria (Mercado, Transporte, Servicios, Ocio, Salud, Otros, Salario)
- `parser/numeros_hablados.py` — "veinte mil" -> 20000, "15k" -> 15000
- `parser/schemas.py` — Dataclass `Extraccion` (monto_cop, categoria, descripcion, fecha_gasto, tipo, confianza)
- `parser/mensajes.py` — Formato de respuestas de confirmacion
- `parser/extractor.py` — Punto de entrada (delega a regex, futuro: LLM)

## Patrones de monto soportados

| Patron | Ejemplo | Resultado |
|--------|---------|-----------|
| Millones | "1.5 millones" | 1_500_000 |
| Mil/K | "15 mil", "15k", "15mil" | 15_000 |
| Miles con punto | "15.300" | 15_300 |
| Plano | "12000" | 12_000 |
| Con $ | "$8.900" | 8_900 |
| Palabras | "veinte mil" | 20_000 |
| Mixto | "1,5 millones" | 1_500_000 |

## Categorias y keywords

Orden de evaluacion (mas especifico primero):
1. Transporte: transmilenio, uber, didi, taxi, gasolina, sitp, bus, metro, peaje
2. Salud: farmacia, drogueria, medico, eps, medicina, consulta
3. Servicios: internet, arriendo, luz, energia, agua, gas, celular, administracion
4. Ocio: cine, netflix, spotify, bar, cerveza, restaurante, steam
5. Mercado: supermercado, alkosto, almuerzo, comida, d1, ara, carulla, exito
6. Salario: salario, sueldo, nomina, quincena (tipo=ingreso)
7. Otros: fallback

## Fechas

- "hoy" -> fecha del mensaje
- "ayer" -> fecha - 1 dia
- "anteayer" -> fecha - 2 dias
- ISO: "2026-08-31"
- Latina: "31/08", "31-08-2026"
- Sin mencion -> fecha del mensaje (no asume hoy si no se dice)

## Confianza

- Max 0.8 (regex)
- +0.15 si categoria != Otros
- +0.05 si tiene descripcion
- 0.0 si no se extrajo monto (necesita_aclaracion=True)

## Cuando modificar el parser

- Agregar keywords en `categorias.py` (no tocar regex)
- Nuevos patrones de monto en `fallback_regex.py`
- Nuevas palabras numericas en `numeros_hablados.py`
- Tests en `tests/test_parser.py` y `tests/test_numeros_hablados.py`

## Futuro: Parser LLM

El `extractor.py` esta preparado para integrar un LLM (Groq con Llama) como parser primario, manteniendo regex como fallback. La idea es que el LLM devuelva JSON estructurado con monto, categoria, descripcion y fecha.
