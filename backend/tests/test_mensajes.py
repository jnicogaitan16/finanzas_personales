from db.users_seed import parse_authorized_users
from parser.mensajes import format_cop, mensaje_confirmacion
from parser.schemas import Extraccion


def test_parse_authorized_users() -> None:
    pares = parse_authorized_users("Nico:573001112233, Pareja: 57 300 444 5566")
    assert pares == [("Nico", "573001112233"), ("Pareja", "573004445566")]


def test_format_cop() -> None:
    assert format_cop(15_300) == "$15.300"
    assert format_cop(1_500_000) == "$1.500.000"


def test_mensaje_confirmacion_gasto() -> None:
    extraccion = Extraccion(
        monto_cop=15_300,
        categoria="Mercado",
        descripcion="almuerzo",
        fecha_gasto=None,
        tipo="gasto",
        confianza=0.7,
        necesita_aclaracion=False,
    )
    assert mensaje_confirmacion(extraccion) == "✅ Registrado: $15.300 en Mercado"
