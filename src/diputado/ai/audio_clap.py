"""CLAP: embeddings de audio y clasificación acústica sin entrenamiento previo."""

from __future__ import annotations

import inspect
import threading
from functools import lru_cache

import numpy as np
import torch

from diputado import config
from diputado.ai import audio_io
from diputado.ai.gpu import SMALL_DEVICE

SR = 48_000
WINDOW_S = 10
_lock = threading.Lock()

# CLAP se entrenó con descripciones en inglés; mostramos la etiqueta en español.
ACOUSTIC_LABELS = {
    "a phone call with a person talking": "Llamada telefónica",
    "a robotic synthetic computer generated voice": "Voz robótica o sintética",
    "busy call center office background noise": "Ruido de centralita",
    "hold music on a telephone line": "Música de espera",
    "a person speaking in a quiet room": "Voz en una sala tranquila",
    "an automated voice menu": "Menú automático (IVR)",
}


@lru_cache(maxsize=1)
def _clap():
    from transformers import ClapModel, ClapProcessor

    mid = config.HF_MODELS["clap"]["id"]
    return ClapProcessor.from_pretrained(mid), ClapModel.from_pretrained(mid).to(SMALL_DEVICE).eval()


def _audio_kw(proc) -> str:
    params = inspect.signature(proc.__call__).parameters
    return "audio" if "audio" in params else "audios"


def load(path) -> np.ndarray:
    return audio_io.load(path, SR)


def _windows(audio: np.ndarray, max_windows: int = 6) -> list[np.ndarray]:
    step = SR * WINDOW_S
    chunks = [audio[i : i + step] for i in range(0, max(len(audio), 1), step)]
    chunks = [c for c in chunks if len(c) > SR] or [audio]
    return chunks[:max_windows]


@torch.inference_mode()
def embed_audio(audio: np.ndarray) -> np.ndarray:
    """Embedding CLAP (512) promediado sobre ventanas de 10 s y normalizado."""
    with _lock:
        proc, model = _clap()
        inputs = proc(**{_audio_kw(proc): _windows(audio)}, sampling_rate=SR, return_tensors="pt").to(SMALL_DEVICE)
        feats = model.get_audio_features(**inputs)
    feats = torch.nn.functional.normalize(feats, dim=-1).mean(0)
    return torch.nn.functional.normalize(feats, dim=-1).cpu().numpy()


@lru_cache(maxsize=1)
@torch.inference_mode()
def _label_embeddings() -> np.ndarray:
    proc, model = _clap()
    inputs = proc(text=list(ACOUSTIC_LABELS), padding=True, return_tensors="pt").to(SMALL_DEVICE)
    feats = model.get_text_features(**inputs)
    return torch.nn.functional.normalize(feats, dim=-1).cpu().numpy()


def zero_shot(audio_emb: np.ndarray) -> dict[str, float]:
    with _lock:
        labels = _label_embeddings()
        _, model = _clap()
        scale = float(model.logit_scale_a.exp())
    logits = scale * labels @ audio_emb
    probs = np.exp(logits - logits.max())
    probs /= probs.sum()
    return {es: float(p) for es, p in sorted(zip(ACOUSTIC_LABELS.values(), probs), key=lambda kv: -kv[1])}
