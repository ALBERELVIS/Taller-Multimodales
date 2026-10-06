"""Carga e inferencia de nuestros dos modelos Keras (backend PyTorch).

* TacticNet: embedding e5 (384) -> probabilidad de estafa + 7 tácticas.
* VozSinteticaNet: embedding CLAP (512) -> probabilidad de voz sintética.

Si los artefactos aún no existen (antes de ejecutar los notebooks 02 y 03), las
funciones devuelven None y la fusión trabaja sin esa señal.
"""

from __future__ import annotations

import json
import threading
from functools import lru_cache

import numpy as np

from diputado import config

TACTIC_PATH = config.ARTIFACTS_DIR / "tacticnet.keras"
TACTIC_META = config.ARTIFACTS_DIR / "tacticnet.json"
VOICE_PATH = config.ARTIFACTS_DIR / "voz_sintetica.keras"
VOICE_META = config.ARTIFACTS_DIR / "voz_sintetica.json"
_lock = threading.Lock()


@lru_cache(maxsize=None)
def _load(path: str):
    import keras

    return keras.saving.load_model(path, compile=False)


def _meta(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def tactics_available() -> bool:
    return TACTIC_PATH.exists()


def voice_available() -> bool:
    return VOICE_PATH.exists()


def predict_tactics(text_emb: np.ndarray) -> dict | None:
    if not tactics_available():
        return None
    meta = _meta(TACTIC_META)
    with _lock:
        model = _load(str(TACTIC_PATH))
        out = model.predict(text_emb.reshape(1, -1).astype("float32"), verbose=0)
    scam = float(np.asarray(out["estafa"]).ravel()[0])
    tactics = np.asarray(out["tacticas"]).ravel()
    labels = meta.get("tactics", list(config.TACTICS))
    thresholds = meta.get("thresholds", {})
    return {
        "scam_prob": scam,
        "tactics": {lab: float(p) for lab, p in zip(labels, tactics)},
        "active": [lab for lab, p in zip(labels, tactics) if p >= thresholds.get(lab, 0.5)],
        "model": "TacticNet (Keras)",
    }


def predict_voice(audio_emb: np.ndarray) -> dict | None:
    if not voice_available():
        return None
    meta = _meta(VOICE_META)
    with _lock:
        model = _load(str(VOICE_PATH))
        p = float(np.asarray(model.predict(audio_emb.reshape(1, -1).astype("float32"), verbose=0)).ravel()[0])
    return {"synthetic_prob": p, "threshold": meta.get("threshold", 0.5), "model": "VozSinteticaNet (Keras)"}
