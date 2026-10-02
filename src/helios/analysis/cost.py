"""Coste local frente a un escenario de API de pago. Las tarifas son hipótesis de trabajo."""

from __future__ import annotations

from helios.config import Settings
from helios.types import StageLog

# Hipótesis de comparación, no una tarifa contratada.
# Visión: 0,01 EUR por imagen. Texto: 0,005 EUR por 1.000 tokens.
# Transcripción: 0,006 EUR por minuto. Voz: 0,015 EUR por 1.000 caracteres.
API_EUR_PER_IMAGE = 0.01
API_EUR_PER_1K_TOKENS = 0.005
API_EUR_PER_AUDIO_MINUTE = 0.006
API_EUR_PER_1K_TTS_CHARS = 0.015
ASSUMED_TEXT_TOKENS = 2800
ASSUMED_AUDIO_MINUTES = 1.5


def estimate_cost(stages: list[StageLog], settings: Settings, briefing_chars: int = 700) -> dict[str, float | str]:
    seconds = sum(stage.seconds for stage in stages)
    kilowatt_hours = (settings.hardware_watts / 1000.0) * (seconds / 3600.0)
    local_eur = kilowatt_hours * settings.electricity_eur_kwh
    vision_calls = sum(1 for stage in stages if "Visión" in stage.name and stage.status == "ok")
    text_calls = sum(1 for stage in stages if stage.name == "Tesis" and stage.model not in {"reglas", "léxico"})
    asr_calls = sum(1 for stage in stages if stage.name == "Transcripción" and stage.status == "ok")
    tts_calls = sum(1 for stage in stages if stage.name == "Briefing de voz" and stage.status == "ok")
    api_eur = (
        vision_calls * API_EUR_PER_IMAGE
        + text_calls * (ASSUMED_TEXT_TOKENS / 1000.0) * API_EUR_PER_1K_TOKENS
        + asr_calls * ASSUMED_AUDIO_MINUTES * API_EUR_PER_AUDIO_MINUTE
        + tts_calls * (briefing_chars / 1000.0) * API_EUR_PER_1K_TTS_CHARS
    )
    return {
        "seconds": round(seconds, 3),
        "kwh": kilowatt_hours,
        "local_eur": local_eur,
        "api_eur": api_eur,
        "watts": settings.hardware_watts,
        "eur_kwh": settings.electricity_eur_kwh,
        "note": "escenario de comparación, no tarifa contratada",
    }
