"""Fusión explicable de señales en un único riesgo.

Usamos *log-odds pooling*: riesgo = sigmoide(b + Σ w_i · logit(p_i)).
Es una regresión logística sobre los logits de cada señal, con dos ventajas:
* una señal ausente se representa como p = 0,5, cuyo logit es 0, y no aporta nada;
* cada término w_i · logit(p_i) es la contribución de esa señal, que mostramos al analista.
Los pesos los ajustamos en el notebook 05 y se guardan en artifacts/fusion.json.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

from diputado import config

FUSION_PATH = config.ARTIFACTS_DIR / "fusion.json"

DEFAULT = {
    "bias": -0.2,
    "weights": {"tacticnet": 0.9, "llm": 1.0, "campana": 0.6, "reglas": 0.8, "voz": 0.25, "acustica": 0.0},
    "source": "pesos iniciales razonados (antes del notebook 05)",
}
SIGNAL_LABELS = {
    "tacticnet": "TacticNet (Keras, texto)",
    "llm": "Qwen3 (razonamiento)",
    "campana": "Parecido a campañas conocidas",
    "reglas": "Reglas deterministas",
    "voz": "VozSinteticaNet (Keras, audio)",
    "acustica": "Contexto acústico (CLAP)",
}


AMPLIFIERS = {"voz", "acustica"}


def load_params() -> dict:
    if FUSION_PATH.exists():
        return json.loads(FUSION_PATH.read_text(encoding="utf-8"))
    return DEFAULT


def logit(p: float, eps: float = 0.02) -> float:
    p = min(max(p, eps), 1 - eps)
    return math.log(p / (1 - p))


def rules_to_prob(score: float) -> float:
    """Sin banderas rojas es indicio leve de legitimidad (0,2); con muchas, fuerte de fraude."""
    return 0.2 + 0.75 * score


def campaign_to_prob(sim: float) -> float:
    return 0.3 + 0.65 * sim


@dataclass
class FusionResult:
    risk: float
    level: str
    contributions: dict[str, float] = field(default_factory=dict)
    inputs: dict[str, float] = field(default_factory=dict)
    hard_rule: bool = False
    params_source: str = ""


def level_for(risk: float) -> str:
    if risk >= config.THRESHOLD_RED:
        return "rojo"
    if risk >= config.THRESHOLD_AMBER:
        return "ambar"
    return "verde"


def fuse(signals: dict[str, float | None], hard_rule: bool = False, params: dict | None = None) -> FusionResult:
    params = params or load_params()
    w = params["weights"]
    contributions, inputs = {}, {}
    z = params["bias"]
    for name, p in signals.items():
        if p is None or name not in w:
            continue
        # La voz sintética solo puede subir el riesgo: un estafador humano no debe
        # parecer más fiable por tener voz natural (y hay IVR legítimos sintéticos).
        eff = max(float(p), 0.5) if name in AMPLIFIERS else float(p)
        c = w[name] * logit(eff)
        contributions[name] = c
        inputs[name] = float(p)
        z += c
    risk = 1 / (1 + math.exp(-z))
    # Regla dura: si alguien pide códigos/PIN o una app de control remoto y al menos
    # un modelo coincide en que es sospechoso, el resultado nunca baja de rojo.
    models_agree = max(inputs.get("tacticnet", 0), inputs.get("llm", 0)) >= 0.5
    forced = hard_rule and models_agree
    if forced:
        risk = max(risk, 0.9)
    return FusionResult(risk, level_for(risk), contributions, inputs, forced, params.get("source", ""))
