"""Tesis y briefing anclados a la ficha. La voz solo lee cifras del código."""

from __future__ import annotations

from helios.analysis.format import fmt_number, fmt_ratio_as_pct
from helios.compliance.disclaimer import DISCLAIMER, SHORT_DISCLAIMER
from helios.types import FactSheet


def render_template(facts: FactSheet, news_title: str | None = None, audio_locator: str | None = None) -> str:
    sentences: list[str] = [
        (
            f"{facts.company} ({facts.ticker}). Sesgo de mesa: {facts.stance}. "
            "La etiqueta sale de reglas sobre margen, drawdown y riesgos del expediente."
        )
    ]
    metric_lines = [
        ("ingresos_2025_m", "Ingresos 2025", "millones EUR", 0),
        ("ebitda_2025_m", "EBITDA 2025", "millones EUR", 0),
        ("margen_ebitda_pct", "Margen EBITDA", "%", 1),
        ("capex_2025_m", "Capex 2025", "millones EUR", 0),
        ("deuda_neta_m", "Deuda neta", "millones EUR", 0),
    ]
    for key, label, unit, decimals in metric_lines:
        if key not in facts.metrics:
            continue
        source = facts.metric_sources.get(key, "PDF")
        value = fmt_number(facts.metrics[key], decimals)
        rendered_unit = unit if unit != "%" else "%"
        if unit == "%":
            sentences.append(f"{label}: {value}{rendered_unit} [{source}].")
        else:
            sentences.append(f"{label}: {value} {unit} [{source}].")
    if facts.guidance_text:
        sentences.append(f"Guía: {facts.guidance_text} [PDF].")
    if facts.risk_text:
        locator = audio_locator or facts.metric_sources.get("risk", "PDF")
        sentences.append(f"Riesgo operativo: {facts.risk_text} [{locator}].")
    if facts.price_stats:
        drawdown = fmt_ratio_as_pct(float(facts.price_stats.get("max_drawdown", 0.0)))
        volatility = fmt_ratio_as_pct(float(facts.price_stats.get("annualized_volatility", 0.0)))
        last = fmt_number(float(facts.price_stats.get("last_close", 0.0)), 2)
        sentences.append(
            f"Riesgo de mercado: último cierre {last}, drawdown máximo {drawdown} "
            f"y volatilidad anualizada {volatility} [Serie de precios]."
        )
    if facts.chart_caption:
        sentences.append(f"Lectura del gráfico: {facts.chart_caption} [Gráfico].")
    if news_title:
        sentences.append(f"La prensa del expediente recoge el caso en «{news_title}» [Noticia: {news_title}].")
    origin = "la capa de texto del PDF" if facts.numbers_origin == "text" else "la lectura visual, porque el PDF no tenía capa de texto"
    sentences.append(f"Las cifras quedan ancladas a {origin}.")
    sentences.append(DISCLAIMER)
    return " ".join(sentences)


def render_briefing(facts: FactSheet) -> str:
    """Guion de voz. No incluye la prosa libre del modelo de visión."""
    chunks: list[str] = [
        f"Resumen Helios para {facts.company}, ticker {facts.ticker}.",
        f"Sesgo de mesa: {facts.stance}.",
    ]
    if "ingresos_2025_m" in facts.metrics:
        chunks.append(f"Ingresos 2025: {fmt_number(facts.metrics['ingresos_2025_m'])} millones de euros.")
    if "ebitda_2025_m" in facts.metrics and "margen_ebitda_pct" in facts.metrics:
        chunks.append(
            "EBITDA "
            f"{fmt_number(facts.metrics['ebitda_2025_m'])} millones de euros, "
            f"margen {fmt_number(facts.metrics['margen_ebitda_pct'], 1)} por ciento."
        )
    if "capex_2025_m" in facts.metrics:
        chunks.append(f"Capex: {fmt_number(facts.metrics['capex_2025_m'])} millones de euros.")
    if "deuda_neta_m" in facts.metrics:
        chunks.append(f"Deuda neta: {fmt_number(facts.metrics['deuda_neta_m'])} millones de euros.")
    if facts.guidance_text:
        chunks.append(f"Guía. {facts.guidance_text}.")
    if facts.risk_text:
        chunks.append(f"Riesgo operativo: {facts.risk_text}")
    if facts.price_stats:
        chunks.append(
            "En la serie local, el drawdown máximo es "
            f"{fmt_ratio_as_pct(float(facts.price_stats.get('max_drawdown', 0.0)))} "
            "y la volatilidad anualizada es "
            f"{fmt_ratio_as_pct(float(facts.price_stats.get('annualized_volatility', 0.0)))}."
        )
    chunks.append(
        "La mesa cruza documento, gráfico, audio, prensa y precios antes de cerrar la nota. "
        f"{SHORT_DISCLAIMER}"
    )
    return " ".join(chunks)


def coded_market_caption(price_stats: dict[str, float]) -> str:
    if not price_stats:
        return ""
    return (
        "La serie calcula un drawdown máximo de "
        f"{fmt_ratio_as_pct(float(price_stats.get('max_drawdown', 0.0)))} "
        "y una volatilidad anualizada de "
        f"{fmt_ratio_as_pct(float(price_stats.get('annualized_volatility', 0.0)))}. "
        "Es una caída desde máximos, no un objetivo de precio."
    )
