"""Razonamiento antifraude y asistente de preguntas con Qwen3 (Ollama)."""

from __future__ import annotations

from diputado import config
from diputado.ai import ollama_client

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "probabilidad_estafa": {"type": "number", "minimum": 0, "maximum": 1},
        "veredicto": {"type": "string", "enum": ["estafa", "sospechoso", "legitimo"]},
        "entidad_suplantada": {"type": "string"},
        "tacticas": {"type": "array", "items": {"type": "string", "enum": list(config.TACTICS)}},
        "frases_clave": {"type": "array", "items": {"type": "string"}},
        "explicacion": {"type": "string"},
        "consejos": {"type": "array", "items": {"type": "string"}},
        "razonamiento": {"type": "string"},
    },
    "required": [
        "probabilidad_estafa", "veredicto", "entidad_suplantada", "tacticas",
        "frases_clave", "explicacion", "consejos", "razonamiento",
    ],
}

GROUND_RULES = """Reglas que siempre se cumplen en España:
- Ningún banco pide por teléfono, SMS o correo el PIN, las claves de acceso, el CVV ni los códigos SMS de confirmación.
- Correos, la DGT, la Agencia Tributaria y la Seguridad Social no cobran tasas por SMS con enlaces acortados.
- Un familiar que escribe desde un "número nuevo" y pide dinero urgente es un fraude muy habitual ("hola mamá").
- Nadie legítimo pide instalar apps de control remoto (AnyDesk, TeamViewer) para "proteger" tu cuenta.
- Las inversiones con rentabilidad garantizada y alta son, por definición, sospechosas (avisos de la CNMV).
- Un mensaje legítimo puede incluir un código de un solo uso si TÚ has iniciado la operación, y suele advertir de que no lo compartas."""

TACTICS_TEXT = "\n".join(f"- {k}: {v}" for k, v in config.TACTICS.items())

SYSTEM = f"""Eres el motor de análisis antifraude de {config.BRAND_NAME}, que protege a clientes de banca, muchos de ellos personas mayores.
{GROUND_RULES}

Tácticas posibles:
{TACTICS_TEXT}

Analiza SOLO la evidencia proporcionada. Sé prudente: no acuses de estafa a mensajes legítimos (avisos informativos sin enlaces ni peticiones, códigos que el usuario ha solicitado).
- probabilidad_estafa: número entre 0 y 1.
- frases_clave: copia literal de las frases que delatan la táctica (máximo 4).
- explicacion: dos frases claras, en español sencillo, tuteando al usuario, sin tecnicismos.
- consejos: tres acciones concretas y breves.
- razonamiento: una o dos frases técnicas para el analista del banco."""


def build_evidence(channel: str, text: str, extra: dict | None = None) -> str:
    lines = [f"Canal: {channel}", "Contenido:", '"""', text.strip()[:6000], '"""']
    for key, value in (extra or {}).items():
        if value:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def analyze(channel: str, text: str, extra: dict | None = None) -> tuple[dict, dict]:
    data, metrics = ollama_client.chat(
        config.OLLAMA_LLM,
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": build_evidence(channel, text, extra)}],
        schema=VERDICT_SCHEMA,
        num_predict=700,
    )
    data["probabilidad_estafa"] = float(min(max(data.get("probabilidad_estafa", 0.5), 0.0), 1.0))
    data["tacticas"] = [t for t in data.get("tacticas", []) if t in config.TACTICS]
    data["consejos"] = [c for c in data.get("consejos", []) if c][:3]
    return data, metrics


QA_SYSTEM = f"""Eres el asistente de voz de {config.BRAND_NAME}. Respondes dudas sobre estafas y seguridad bancaria
a personas mayores, con frases cortas, cálidas y claras, en un máximo de 3 frases y sin listas ni símbolos.
{GROUND_RULES}
Si la persona describe una situación de riesgo, dile qué hacer ahora mismo (colgar, no pagar, llamar a su banco al número de la tarjeta).
No des asesoramiento de inversión personalizado."""


def answer(question: str) -> tuple[str, dict]:
    text, metrics = ollama_client.chat(
        config.OLLAMA_LLM,
        [{"role": "system", "content": QA_SYSTEM}, {"role": "user", "content": question}],
        temperature=0.3,
        num_predict=250,
    )
    return text.strip(), metrics
