from parser.numeros_hablados import normalizar_numeros_hablados


def test_veinte_mil() -> None:
    assert "20000" in normalizar_numeros_hablados("gasté veinte mil en uber")


def test_quince_mil_trescientos() -> None:
    assert normalizar_numeros_hablados("quince mil trescientos en almuerzo") == (
        "15300 en almuerzo"
    )


def test_treinta_y_cinco_mil() -> None:
    assert "35000" in normalizar_numeros_hablados("treinta y cinco mil en mercado")


def test_no_convierte_un_suelto() -> None:
    assert "un uber" in normalizar_numeros_hablados("platas en un uber")


def test_borra_ultimo_intacto() -> None:
    assert normalizar_numeros_hablados("borra el último") == "borra el último"


def test_digitos_mas_mil() -> None:
    assert "15000" in normalizar_numeros_hablados("gasté 15 mil en uber")
    assert "20000" in normalizar_numeros_hablados("ayer gasté 20 mil en uber")


def test_quince_mil_como_digitos_y_fraccion() -> None:
    assert normalizar_numeros_hablados("15 mil quinientos en almuerzo") == (
        "15500 en almuerzo"
    )


def test_pegado_y_k() -> None:
    assert "15000" in normalizar_numeros_hablados("gaste 15mil en el mercado")
    assert "50000" in normalizar_numeros_hablados("me gasté 50k en gasolina")


def test_miles_ya_formateados_siguen() -> None:
    assert "15.000" in normalizar_numeros_hablados("gasté 15.000 en uber")
