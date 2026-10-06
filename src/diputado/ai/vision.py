"""Lectura de capturas, cartas y correos con Qwen2.5-VL (Ollama)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from diputado import config
from diputado.ai import ollama_client

SCHEMA = {
    "type": "object",
    "properties": {
        "tipo_documento": {"type": "string", "enum": ["sms", "whatsapp", "email", "carta", "web", "red_social", "otro"]},
        "remitente": {"type": "string"},
        "texto_completo": {"type": "string"},
        "enlaces": {"type": "array", "items": {"type": "string"}},
        "telefonos": {"type": "array", "items": {"type": "string"}},
        "marcas_visibles": {"type": "array", "items": {"type": "string"}},
        "senales_visuales": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["tipo_documento", "remitente", "texto_completo", "enlaces", "telefonos", "marcas_visibles", "senales_visuales"],
}

PROMPT = """Eres un analista antifraude. Lee la imagen (captura de móvil, correo, carta o web).
Devuelve JSON con:
- tipo_documento: sms, whatsapp, email, carta, web, red_social u otro.
- remitente: quién lo envía tal como aparece (número, nombre o dirección); "" si no aparece.
- texto_completo: transcripción literal y completa del texto del mensaje principal, en su idioma original.
- enlaces: URLs o dominios que aparezcan, copiados exactamente.
- telefonos: números de teléfono que aparezcan.
- marcas_visibles: empresas o entidades mencionadas o con logotipo (banco, Correos, DGT...).
- senales_visuales: detalles visuales sospechosos (logotipo pixelado, faltas de ortografía, remitente raro, botón de pago...). Lista vacía si no hay.
No inventes texto que no esté en la imagen."""

MAX_SIDE = 1280


def _prepare(path: str | Path) -> str:
    img = Image.open(path)
    img = img.convert("RGB")
    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE))
    tmp = Path(tempfile.gettempdir()) / f"dd_vlm_{Path(path).stem}.jpg"
    img.save(tmp, quality=92)
    return str(tmp)


def read_image(path: str | Path, model: str = config.OLLAMA_VLM) -> tuple[dict, dict]:
    img = _prepare(path)
    data, metrics = ollama_client.chat(
        model,
        [{"role": "user", "content": PROMPT, "images": [img]}],
        schema=SCHEMA,
        num_ctx=6144,
        num_predict=900,
    )
    for key in ("enlaces", "telefonos", "marcas_visibles", "senales_visuales"):
        data[key] = [str(x) for x in data.get(key, []) if str(x).strip()]
    data["texto_completo"] = str(data.get("texto_completo", "")).strip()
    return data, metrics
