"""Sesgo de mesa por reglas. El modelo puede redactar, no cambiar la etiqueta."""

from __future__ import annotations


def decide_stance(metrics: dict[str, float], price_stats: dict[str, float], risk_text: str) -> str:
    drawdown = float(price_stats.get("max_drawdown", 0.0))
    margin = metrics.get("margen_ebitda_pct")
    has_risk = bool(risk_text and risk_text.strip())
    if drawdown <= -0.15 and has_risk:
        return "Vigilar"
    if margin is not None and margin < 10:
        return "Defensivo"
    if margin is not None and margin >= 20 and drawdown > -0.15:
        return "Constructivo"
    return "Neutral"
