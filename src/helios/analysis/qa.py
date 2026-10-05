"""Preguntas sobre el expediente. La pista numérica la escribe el código."""

from __future__ import annotations

import json
import re

from helios.analysis.citations import filter_unsupported_sentences
from helios.analysis.format import fmt_number, fmt_ratio_as_pct
from helios.analysis.index import image_keyword_hit, rank_images, rank_texts
from helios.analysis.numbers import support_ratio
from helios.compliance.disclaimer import SHORT_DISCLAIMER
from helios.config import Settings
from helios.types import AnalysisResult, Answer, Hit


def answer_question(question: str, result: AnalysisResult, settings: Settings | None = None, use_models: bool = True) -> Answer:
    settings = settings or Settings.from_env()
    query_vector = _text_vector(question, result.chunks, settings, use_models)
    hits = rank_texts(result.chunks, question, query_vector=query_vector, k=4)
    image_vector = _clip_vector(question, result.images, settings, use_models)
    image_hits = rank_images(result.images, image_vector, question)
    image_caption = image_hits[0].text if image_hits else None
    direct = direct_fact_answer(question, result)
    offline = _offline_answer(direct, hits, image_caption if image_keyword_hit(question) or image_hits else None)
    mode = "lexico" if hits and hits[0].mode == "lexico" else ("hibrido" if hits else "ficha")
    if image_hits and image_hits[0].mode == "clip":
        mode = "multimodal"
    raw = offline
    if use_models:
        generated = _model_answer(question, result, settings, direct, hits, image_caption)
        if generated:
            raw = generated
            mode = "modelo+" + mode
    filtered = filter_unsupported_sentences(raw, result.allowed_numbers)
    text = filtered.text.strip() or offline
    if support_ratio(text, result.allowed_numbers) < 1:
        text = offline
    return Answer(
        text=text,
        hits=hits,
        image_caption=image_caption,
        mode=mode,
        rejected=filtered.rejected,
        support_ratio=support_ratio(text, result.allowed_numbers),
    )


def direct_fact_answer(question: str, result: AnalysisResult) -> str:
    folded = question.lower()
    facts = result.fact_sheet
    metrics = facts.metrics
    checks: list[tuple[tuple[str, ...], str]] = [
        (("margen",), "margen_ebitda_pct"),
        (("ebitda",), "ebitda_2025_m"),
        (("ingreso",), "ingresos_2025_m"),
        (("capex", "inversion", "inversión"), "capex_2025_m"),
        (("deuda",), "deuda_neta_m"),
        (("retraso", "meses"), "retraso_permiso_meses"),
    ]
    for words, key in checks:
        if key in metrics and any(word in folded for word in words):
            source = facts.metric_sources.get(key, "PDF")
            value = metrics[key]
            if key == "margen_ebitda_pct":
                rendered = f"{fmt_number(value, 1)}%"
            elif key == "retraso_permiso_meses":
                rendered = f"{fmt_number(value)} meses"
            else:
                rendered = f"{fmt_number(value)} millones EUR"
            return f"{_label(key)}: {rendered} [{source}]."
    if any(word in folded for word in ("drawdown", "caida", "caída", "retroceso", "de mercado")) and facts.price_stats:
        return (
            "Drawdown máximo: "
            f"{fmt_ratio_as_pct(float(facts.price_stats['max_drawdown']))} [Serie de precios]."
        )
    if "volatilidad" in folded and facts.price_stats:
        return (
            "Volatilidad anualizada: "
            f"{fmt_ratio_as_pct(float(facts.price_stats['annualized_volatility']))} [Serie de precios]."
        )
    if any(word in folded for word in ("guía", "guia", "guidance")) and facts.guidance_text:
        return f"Guía: {facts.guidance_text} [PDF]."
    if any(word in folded for word in ("cabo", "permiso", "riesgo")) and facts.risk_text:
        return f"Riesgo operativo: {facts.risk_text} [PDF]."
    if any(word in folded for word in ("sesgo", "recomend", "postura")):
        return f"Sesgo de mesa: {facts.stance}. Es una regla, no una recomendación de compra o venta."
    return ""


def _label(key: str) -> str:
    labels = {
        "margen_ebitda_pct": "Margen EBITDA",
        "ebitda_2025_m": "EBITDA 2025",
        "ingresos_2025_m": "Ingresos 2025",
        "capex_2025_m": "Capex 2025",
        "deuda_neta_m": "Deuda neta",
        "retraso_permiso_meses": "Retraso del permiso",
    }
    return labels.get(key, key)


def _offline_answer(direct: str, hits: list[Hit], image_caption: str | None) -> str:
    parts: list[str] = []
    if direct:
        parts.append(direct)
    if hits:
        best = hits[0]
        excerpt = " ".join(best.text.split())
        if len(excerpt) > 420:
            excerpt = excerpt[:420].rsplit(" ", 1)[0] + "..."
        parts.append(f"Fragmento más cercano ({best.locator}): {excerpt}")
    if image_caption:
        parts.append(f"Lectura del gráfico: {image_caption}")
    if not parts:
        parts.append("No hay un fragmento del expediente que responda a esa pregunta.")
    parts.append(SHORT_DISCLAIMER)
    return "\n\n".join(parts)


def _text_vector(question: str, chunks, settings: Settings, use_models: bool):
    if not use_models or not any(chunk.vector for chunk in chunks):
        return None
    try:
        from helios.models.embeddings import embed_texts

        return embed_texts([question], settings)[0].tolist()
    except Exception:
        return None


def _clip_vector(question: str, images, settings: Settings, use_models: bool):
    if not use_models or not any(image.vector for image in images):
        return None
    try:
        from helios.models.clip_encoder import embed_texts as embed_clip

        return embed_clip([question], settings)[0].tolist()
    except Exception:
        return None


def _model_answer(question, result, settings, direct, hits, image_caption) -> str | None:
    try:
        from helios.models.ollama_client import OllamaClient
    except Exception:
        return None
    client = OllamaClient(settings)
    if not client.healthy():
        return None
    model = client.resolve(settings.text_model, settings.text_fallbacks)
    if not model:
        return None
    sources = "\n".join(f"- {hit.locator}: {hit.text[:500]}" for hit in hits[:4]) or "- sin fragmentos"
    prompt = (
        "Responde en español, en un párrafo breve, solo con el expediente.\n"
        f"Compañía: {result.fact_sheet.company} ({result.fact_sheet.ticker}). Sesgo de mesa: {result.fact_sheet.stance}.\n"
        f"Pista calculada por código, no la contradigas: {direct or 'ninguna'}.\n"
        f"Lectura del gráfico: {image_caption or 'no aplica'}.\n"
        f"Fragmentos:\n{sources}\n\n"
        f"Pregunta: {question}\n"
        "Cita la fuente entre corchetes, por ejemplo [PDF p.1] o [Serie de precios]. "
        "No inventes cifras. Si no consta, dilo."
    )
    try:
        raw = client.chat(model, prompt, timeout=180)
    except Exception:
        return None
    return _as_prose(raw)


def _as_prose(raw: str) -> str:
    text = raw.strip()
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.S)
            payload = json.loads(match.group(0)) if match else None
        if isinstance(payload, dict):
            for key in ("respuesta", "narrativa", "texto", "answer"):
                if payload.get(key):
                    return str(payload[key])
    return text
