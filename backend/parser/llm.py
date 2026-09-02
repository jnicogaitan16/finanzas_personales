"""Parser de mensajes financieros usando Groq LLM (Llama 3.3)."""

from __future__ import annotations

import json
import logging
from datetime import date

import httpx

from config import settings
from parser.categorias import CATEGORIAS_TODAS
from parser.schemas import Extraccion

logger = logging.getLogger(__name__)

_GROQ_CHAT = "https://api.groq.com/openai/v1/chat/completions"
_MODELO = "llama-3.3-70b-versatile"


def _system_prompt(categorias: list[str], hoy: str) -> str:
    cats = ", ".join(categorias)
    return (
        "Eres un parser de gastos personales en Colombia (COP). "
        "Del mensaje del usuario extrae la informacion financiera.\n"
        f"Hoy es {hoy}. 'ayer' = dia anterior, 'anteayer' = 2 dias antes.\n"
        f"Categorias validas: {cats}\n"
        "Si no puedes determinar la categoria, usa 'Otros'.\n"
        "Si dice 'compartido', 'mitad', '50/50' o 'a medias', marca compartido=true.\n"
        "Si dice 'me pagaron', 'sueldo', 'nomina', 'quincena', 'freelance', el tipo es 'ingreso'.\n"
        "Responde UNICAMENTE con JSON valido, sin texto adicional:\n"
        '{"monto":15000,"categoria":"Transporte","descripcion":"uber",'
        f'"fecha":"{hoy}","tipo":"gasto","compartido":false}}'
    )


def extraer_con_llm(
    texto: str,
    *,
    hoy: date | None = None,
) -> Extraccion | None:
    if not settings.groq_api_key:
        return None

    hoy = hoy or date.today()
    categorias = list(CATEGORIAS_TODAS)

    try:
        response = httpx.post(
            _GROQ_CHAT,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _MODELO,
                "messages": [
                    {"role": "system", "content": _system_prompt(categorias, hoy.isoformat())},
                    {"role": "user", "content": texto},
                ],
                "temperature": 0,
                "max_tokens": 200,
            },
            timeout=5.0,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Error llamando a Groq LLM")
        return None

    try:
        content = response.json()["choices"][0]["message"]["content"].strip()
        # Limpiar posibles backticks de markdown
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        data = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError):
        logger.warning("Groq LLM respuesta no parseable: %s", response.text[:300])
        return None

    monto = data.get("monto")
    if not isinstance(monto, (int, float)) or monto <= 0:
        return None

    categoria = data.get("categoria", "Otros")
    if categoria not in categorias:
        categoria = "Otros"

    tipo = data.get("tipo", "gasto")
    if tipo not in ("gasto", "ingreso"):
        tipo = "gasto"

    fecha_str = data.get("fecha")
    fecha_gasto = hoy
    if isinstance(fecha_str, str):
        try:
            fecha_gasto = date.fromisoformat(fecha_str)
        except ValueError:
            fecha_gasto = hoy

    compartido = bool(data.get("compartido", False))

    return Extraccion(
        monto_cop=int(monto),
        categoria=categoria,
        descripcion=data.get("descripcion"),
        fecha_gasto=fecha_gasto,
        tipo=tipo,
        confianza=0.95,
        necesita_aclaracion=False,
        compartido=compartido,
    )
