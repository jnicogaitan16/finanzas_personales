from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta

from parser.categorias import KEYWORDS_CATEGORIA, KEYWORDS_COMPARTIDO, KEYWORDS_INGRESO
from parser.schemas import Extraccion
from tiempo import a_bogota, ahora_bogota

_AMOUNT_MILLONES = re.compile(
    r"(?P<n>\d+(?:[.,]\d+)?)\s*(?:millones|millon|millón)\b",
    re.IGNORECASE,
)
_AMOUNT_MIL = re.compile(
    r"(?P<n>\d+(?:[.,]\d+)?)\s*(?:mil|k)\b",
    re.IGNORECASE,
)
_AMOUNT_MILES = re.compile(
    r"(?<!\d)\$?\s*(?P<n>\d{1,3}(?:[.\s]\d{3})+)(?!\d)",
)
_AMOUNT_PLAIN = re.compile(
    r"(?<!\d)\$?\s*(?P<n>\d{3,9})(?!\d)",
)

_RUIDO_DESCRIPCION = re.compile(
    r"\b(gaste|gasté|gastos|pague|pagué|pague|me gaste|me gasté|"
    r"hoy|ayer|anteayer|en|de|del|la|el|un|una|por|para|pesos|peso|cop)\b",
    re.IGNORECASE,
)


def extraer_con_regex(
    texto: str,
    *,
    hoy: date | None = None,
    enviado_en: datetime | None = None,
) -> Extraccion:
    if enviado_en is not None:
        enviado_en = a_bogota(enviado_en)
        hoy = hoy or enviado_en.date()
    else:
        hoy = hoy or ahora_bogota().date()
    normalizado = _normalizar(texto)
    monto, monto_span = _extraer_monto(texto)
    tipo = "ingreso" if _parece_ingreso(normalizado) else "gasto"
    categoria = _extraer_categoria(normalizado, tipo)
    descripcion = _extraer_descripcion(texto, monto_span)
    fecha_gasto = _extraer_fecha(normalizado, hoy)
    compartido = _parece_compartido(normalizado)

    if monto is None or monto <= 0:
        return Extraccion(
            monto_cop=None,
            categoria=categoria,
            descripcion=descripcion,
            fecha_gasto=fecha_gasto,
            tipo=tipo,
            confianza=0.0,
            necesita_aclaracion=True,
            compartido=compartido,
        )

    confianza = 0.55
    if categoria and categoria != "Otros":
        confianza += 0.15
    if descripcion:
        confianza += 0.05

    return Extraccion(
        monto_cop=monto,
        categoria=categoria or ("Salario" if tipo == "ingreso" else "Otros"),
        descripcion=descripcion,
        fecha_gasto=fecha_gasto,
        tipo=tipo,
        confianza=min(confianza, 0.8),
        necesita_aclaracion=False,
        compartido=compartido,
    )


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_tildes).strip()


def _extraer_monto(texto: str) -> tuple[int | None, tuple[int, int] | None]:
    for patron, multiplicador in (
        (_AMOUNT_MILLONES, 1_000_000),
        (_AMOUNT_MIL, 1_000),
    ):
        match = patron.search(texto)
        if match:
            valor = _a_numero(match.group("n"))
            if valor is None:
                continue
            return int(round(valor * multiplicador)), match.span()

    match = _AMOUNT_MILES.search(texto)
    if match:
        crudo = match.group("n").replace(" ", "").replace(".", "")
        if crudo.isdigit():
            return int(crudo), match.span()

    match = _AMOUNT_PLAIN.search(texto)
    if match:
        return int(match.group("n")), match.span()

    return None, None


def _a_numero(crudo: str) -> float | None:
    texto = crudo.strip()
    if not texto:
        return None
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        enteros, _, decimales = texto.partition(",")
        texto = f"{enteros}.{decimales}" if len(decimales) <= 2 else texto.replace(",", "")
    elif texto.count(".") == 1:
        enteros, _, decimales = texto.partition(".")
        if len(decimales) == 3:
            texto = enteros + decimales
    try:
        return float(texto)
    except ValueError:
        return None


def _parece_ingreso(normalizado: str) -> bool:
    return any(_contiene_keyword(normalizado, palabra) for palabra in KEYWORDS_INGRESO)


def _parece_compartido(normalizado: str) -> bool:
    return any(_contiene_keyword(normalizado, palabra) for palabra in KEYWORDS_COMPARTIDO)


def _extraer_categoria(normalizado: str, tipo: str) -> str:
    for categoria, keywords in KEYWORDS_CATEGORIA:
        if any(_contiene_keyword(normalizado, keyword) for keyword in keywords):
            return categoria
    return "Salario" if tipo == "ingreso" else "Otros"


def _contiene_keyword(normalizado: str, keyword: str) -> bool:
    kw = _normalizar(keyword)
    if len(kw) <= 3:
        return re.search(rf"\b{re.escape(kw)}\b", normalizado) is not None
    return kw in normalizado


def extraer_fecha_explicita(texto: str, *, hoy: date) -> date | None:
    """Fecha solo si el texto la nombra. No asume hoy."""
    normalizado = _normalizar(texto)
    if re.search(r"\banteayer\b", normalizado):
        return hoy - timedelta(days=2)
    if re.search(r"\bayer\b", normalizado):
        return hoy - timedelta(days=1)
    if re.search(r"\bhoy\b", normalizado):
        return hoy
    iso = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", normalizado)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None
    latina = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", normalizado)
    if latina:
        dia, mes = int(latina.group(1)), int(latina.group(2))
        crudo_anio = latina.group(3)
        if crudo_anio is None:
            anio = hoy.year
        elif len(crudo_anio) <= 2:
            anio = int(crudo_anio) + 2000
        else:
            anio = int(crudo_anio)
        try:
            return date(anio, mes, dia)
        except ValueError:
            return None
    return None


def _extraer_descripcion(texto: str, monto_span: tuple[int, int] | None) -> str | None:
    resto = texto
    if monto_span:
        resto = (texto[: monto_span[0]] + " " + texto[monto_span[1] :]).strip()
    resto = _RUIDO_DESCRIPCION.sub(" ", resto)
    resto = re.sub(r"[\$\d.,]+", " ", resto)
    resto = re.sub(r"\s+", " ", resto).strip(" -:.,")
    return resto or None


def _extraer_fecha(normalizado: str, hoy: date) -> date:
    if "anteayer" in normalizado:
        return hoy - timedelta(days=2)
    if "ayer" in normalizado:
        return hoy - timedelta(days=1)
    return hoy
