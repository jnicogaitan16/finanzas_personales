from datetime import date, datetime, timezone

import pytest

from parser.fallback_regex import extraer_con_regex, extraer_fecha_explicita

HOY = date(2026, 8, 31)


@pytest.mark.parametrize(
    ("texto", "monto", "categoria"),
    [
        ("gasté 15.300 en almuerzo", 15_300, "Mercado"),
        ("gaste 15mil en el mercado", 15_000, "Mercado"),
        ("15 mil en uber", 15_000, "Transporte"),
        ("pagué 120.000 de internet", 120_000, "Servicios"),
        ("me gasté 50k en gasolina", 50_000, "Transporte"),
        ("cine 28000", 28_000, "Ocio"),
        ("farmacia 45000", 45_000, "Salud"),
        ("1.5 millones de arriendo", 1_500_000, "Hogar"),
        ("me pagaron 3 millones", 3_000_000, "Salario"),
        ("$8.900 en d1", 8_900, "Mercado"),
        ("compró 1.200.000 de mercado", 1_200_000, "Mercado"),
        ("taxi 12000", 12_000, "Transporte"),
    ],
)
def test_extrae_monto_y_categoria(texto: str, monto: int, categoria: str) -> None:
    resultado = extraer_con_regex(texto, hoy=HOY)
    assert resultado.necesita_aclaracion is False
    assert resultado.monto_cop == monto
    assert resultado.categoria == categoria
    assert resultado.es_valida


def test_sin_monto_pide_aclaracion() -> None:
    resultado = extraer_con_regex("me gasté plata en el almuerzo", hoy=HOY)
    assert resultado.necesita_aclaracion is True
    assert resultado.monto_cop is None
    assert resultado.es_valida is False


def test_fecha_ayer() -> None:
    resultado = extraer_con_regex("ayer gasté 20 mil en uber", hoy=HOY)
    assert resultado.fecha_gasto == date(2026, 8, 30)
    assert resultado.monto_cop == 20_000
    assert resultado.categoria == "Transporte"


def test_fecha_anteayer() -> None:
    resultado = extraer_con_regex("anteayer pagué 80.000 de farmacia", hoy=HOY)
    assert resultado.fecha_gasto == date(2026, 8, 29)


def test_ingreso_por_sueldo() -> None:
    resultado = extraer_con_regex("me llegó el sueldo de 4.500.000", hoy=HOY)
    assert resultado.tipo == "ingreso"
    assert resultado.monto_cop == 4_500_000
    assert resultado.categoria == "Salario"


def test_sin_categoria_cae_en_otros() -> None:
    resultado = extraer_con_regex("gasté 9000 en no sé qué", hoy=HOY)
    assert resultado.categoria == "Otros"
    assert resultado.monto_cop == 9000


def test_para_no_se_confunde_con_ara() -> None:
    resultado = extraer_con_regex("gasté 9000 para el perro", hoy=HOY)
    assert resultado.categoria == "Otros"
    assert resultado.monto_cop == 9000


def test_fecha_usa_envio_en_horario_bogota() -> None:
    enviado = datetime(2026, 9, 1, 1, 15, tzinfo=timezone.utc)
    resultado = extraer_con_regex("gasté 15.300 en almuerzo", enviado_en=enviado)
    assert resultado.fecha_gasto == date(2026, 8, 31)


def test_ayer_es_relativo_a_la_fecha_de_envio_en_bogota() -> None:
    enviado = datetime(2026, 9, 1, 1, 15, tzinfo=timezone.utc)
    resultado = extraer_con_regex("ayer gasté 20 mil en uber", enviado_en=enviado)
    assert resultado.fecha_gasto == date(2026, 8, 30)


def test_fecha_explicita_no_asume_hoy() -> None:
    hoy = date(2026, 9, 1)
    assert extraer_fecha_explicita("sin fecha", hoy=hoy) is None
    assert extraer_fecha_explicita("ayer", hoy=hoy) == date(2026, 8, 31)
    assert extraer_fecha_explicita("31/08/2026", hoy=hoy) == date(2026, 8, 31)
    assert extraer_fecha_explicita("2026-08-30", hoy=hoy) == date(2026, 8, 30)
