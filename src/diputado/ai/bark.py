"""Bark (Suno) para generar llamadas sintéticas: datos de entrenamiento y casos de demo."""

from __future__ import annotations

import re
import threading
from functools import lru_cache

import numpy as np
import torch

from diputado import config
from diputado.ai.gpu import DEVICE, HAS_CUDA, gpu

_lock = threading.Lock()
SPANISH_VOICES = [f"v2/es_speaker_{i}" for i in range(10)]


@lru_cache(maxsize=1)
def _bark():
    from transformers import AutoProcessor, BarkModel

    mid = config.HF_MODELS["bark"]["id"]
    proc = AutoProcessor.from_pretrained(mid)
    model = BarkModel.from_pretrained(mid, torch_dtype=torch.float16 if HAS_CUDA else torch.float32).to(DEVICE)
    gpu.register("bark", lambda: model.to("cpu"))
    return proc, model


def _chunks(text: str, max_chars: int = 160) -> list[str]:
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    out, cur = [], ""
    for s in sents:
        if len(cur) + len(s) < max_chars:
            cur = f"{cur} {s}".strip()
        else:
            if cur:
                out.append(cur)
            cur = s
    if cur:
        out.append(cur)
    return out


@torch.inference_mode()
def synthesize(text: str, voice: str = "v2/es_speaker_1", seed: int = 0) -> tuple[np.ndarray, int]:
    """Genera voz frase a frase (Bark degrada por encima de ~13 s por llamada)."""
    with _lock, gpu.claim("bark"):
        proc, model = _bark()
        model.to(DEVICE)
        sr = model.generation_config.sample_rate
        pieces = []
        for i, chunk in enumerate(_chunks(text)):
            torch.manual_seed(seed + i)
            inputs = proc(chunk, voice_preset=voice, return_tensors="pt").to(DEVICE)
            wav = model.generate(**inputs, do_sample=True, pad_token_id=10000)
            pieces += [wav[0].float().cpu().numpy(), np.zeros(int(0.2 * sr), dtype=np.float32)]
    audio = np.concatenate(pieces)
    return (0.9 * audio / (np.abs(audio).max() or 1)).astype(np.float32), sr
