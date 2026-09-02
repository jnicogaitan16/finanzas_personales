from datetime import datetime

from config import settings
from parser.fallback_regex import extraer_con_regex
from parser.llm import extraer_con_llm
from parser.schemas import Extraccion
from tiempo import a_bogota, ahora_bogota


def extraer_mensaje(texto: str, *, enviado_en: datetime | None = None) -> Extraccion:
    if enviado_en is not None:
        hoy = a_bogota(enviado_en).date()
    else:
        hoy = ahora_bogota().date()

    # Intentar con LLM primero (si hay API key)
    if settings.groq_api_key:
        resultado = extraer_con_llm(texto, hoy=hoy)
        if resultado is not None and resultado.es_valida:
            return resultado

    # Fallback a regex
    return extraer_con_regex(texto, enviado_en=enviado_en)
