"""Convierte cantidades en palabras (español) a dígitos, p. ej. veinte mil → 20000."""

from __future__ import annotations

import re
import unicodedata

_VALORES: dict[str, int] = {
    "cero": 0,
    "un": 1,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiun": 21,
    "veintiuno": 21,
    "veintiuna": 21,
    "veintidos": 22,
    "veintitres": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    "veintiseis": 26,
    "veintisiete": 27,
    "veintiocho": 28,
    "veintinueve": 29,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
    "cien": 100,
    "ciento": 100,
    "doscientos": 200,
    "trescientos": 300,
    "cuatrocientos": 400,
    "quinientos": 500,
    "seiscientos": 600,
    "setecientos": 700,
    "ochocientos": 800,
    "novecientos": 900,
    "mil": 1000,
    "millon": 1_000_000,
    "millones": 1_000_000,
}

_SOLO_ARTICULO = {"un", "una", "uno"}
_ESCALAS = {"mil": 1_000, "k": 1_000, "millon": 1_000_000, "millones": 1_000_000}
_MIXTO = re.compile(
    r"^\$?(?P<n>\d{1,3}(?:[.,]\d{1,2})?)(?P<esc>mil|k|millones|millon)$",
    re.IGNORECASE,
)
_MILES_AGRUPADOS = re.compile(r"^\d{1,3}(?:\.\d{3})+$")
_DECIMAL_CORTO = re.compile(r"^(\d{1,3})[.,](\d{1,2})$")


def _normalizar_token(token: str) -> str:
    sin = "".join(
        c for c in unicodedata.normalize("NFD", token.lower()) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z]", "", sin)


def _es_parte_numero(token: str) -> bool:
    n = _normalizar_token(token)
    return n == "y" or n in _VALORES


def _factor_escala(token: str) -> int | None:
    return _ESCALAS.get(_normalizar_token(token))


def _a_decimal(crudo: str) -> float | None:
    if "," in crudo:
        crudo = crudo.replace(",", ".")
    try:
        return float(crudo)
    except ValueError:
        return None


def _numero_corto(token: str) -> float | None:
    t = token.strip().lstrip("$")
    if not t or _MILES_AGRUPADOS.fullmatch(t):
        return None
    if t.isdigit():
        n = int(t)
        return float(n) if 1 <= n <= 999 else None
    if _DECIMAL_CORTO.fullmatch(t):
        valor = _a_decimal(t)
        if valor is not None and 0 < valor < 1000:
            return valor
    return None


def _valor_mixto(token: str) -> int | None:
    match = _MIXTO.fullmatch(token.strip())
    if not match:
        return None
    valor = _a_decimal(match.group("n"))
    factor = _ESCALAS.get(match.group("esc").lower())
    if valor is None or factor is None:
        return None
    return int(round(valor * factor))


def _grupo_a_entero(palabras: list[str]) -> int | None:
    utiles = [_normalizar_token(p) for p in palabras if _normalizar_token(p) != "y"]
    utiles = [p for p in utiles if p in _VALORES]
    if not utiles:
        return None
    if len(utiles) == 1 and utiles[0] in _SOLO_ARTICULO:
        return None
    total = 0
    actual = 0
    for palabra in utiles:
        valor = _VALORES[palabra]
        if valor == 1_000_000:
            actual = (actual or 1) * valor
            total += actual
            actual = 0
        elif valor == 1000:
            actual = (actual or 1) * 1000
        else:
            actual += valor
    total += actual
    return total if total > 0 else None


def _saltar_espacios(tokens: list[str], i: int) -> int:
    while i < len(tokens) and tokens[i].isspace():
        i += 1
    return i


def _tomar_grupo_palabras(tokens: list[str], i: int) -> tuple[list[str], int]:
    grupo: list[str] = []
    j = i
    while j < len(tokens):
        if tokens[j].isspace():
            k = _saltar_espacios(tokens, j)
            if k < len(tokens) and _es_parte_numero(tokens[k]):
                j = k
                continue
            break
        if not _es_parte_numero(tokens[j]):
            break
        grupo.append(tokens[j])
        j += 1
    return grupo, j


def normalizar_numeros_hablados(texto: str) -> str:
    tokens = [p for p in re.split(r"(\s+)", texto) if p]
    salida: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.isspace():
            salida.append(token)
            i += 1
            continue

        mixto = _valor_mixto(token)
        if mixto is not None:
            salida.append(str(mixto))
            i += 1
            continue

        corto = _numero_corto(token)
        if corto is not None:
            j = _saltar_espacios(tokens, i + 1)
            factor = _factor_escala(tokens[j]) if j < len(tokens) else None
            if factor is not None:
                j += 1
                extra_grupo, j = _tomar_grupo_palabras(tokens, _saltar_espacios(tokens, j))
                extra = _grupo_a_entero(extra_grupo) or 0
                salida.append(str(int(round(corto * factor + extra))))
                i = j
                continue
            salida.append(token)
            i += 1
            continue

        if _es_parte_numero(token):
            grupo, j = _tomar_grupo_palabras(tokens, i)
            numero = _grupo_a_entero(grupo)
            if numero is None:
                salida.append(token)
                i += 1
                continue
            salida.append(str(numero))
            i = j
            continue

        salida.append(token)
        i += 1
    return "".join(salida)
