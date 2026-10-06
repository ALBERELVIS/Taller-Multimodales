"""Transcripción de llamadas y notas de voz con Whisper (Hugging Face)."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np

from diputado import config
from diputado.ai import audio_io
from diputado.ai.gpu import DEVICE, DTYPE, HAS_CUDA, LIGHT_MODE, gpu

SR = 16_000
_pipe = None
_load_lock = threading.Lock()


def model_id() -> str:
    return config.HF_MODELS["asr_cpu" if LIGHT_MODE else "asr"]["id"]


def _evict() -> None:
    global _pipe
    if _pipe is not None and HAS_CUDA:
        try:
            _pipe.model.to("cpu")
        except Exception:
            _pipe = None


def _get():
    global _pipe
    with _load_lock:
        if _pipe is None:
            from transformers import pipeline

            _pipe = pipeline(
                "automatic-speech-recognition",
                model=model_id(),
                torch_dtype=DTYPE,
                device=DEVICE,
            )
            gpu.register("whisper", _evict)
    return _pipe


def load_audio(path: str | Path, sr: int = SR) -> np.ndarray:
    return audio_io.load(path, sr)


def transcribe(path: str | Path, language: str = "spanish") -> tuple[dict, dict]:
    t0 = time.perf_counter()
    audio = load_audio(path)
    duration = len(audio) / SR
    with gpu.claim("whisper"):
        pipe = _get()
        if HAS_CUDA:
            pipe.model.to(DEVICE)
        out = pipe(
            {"raw": audio, "sampling_rate": SR},
            chunk_length_s=30,
            batch_size=8,
            return_timestamps=True,
            generate_kwargs={"language": language, "task": "transcribe"},
        )
    segments = [
        {"start": float(c["timestamp"][0] or 0), "end": float(c["timestamp"][1] or duration), "text": c["text"].strip()}
        for c in out.get("chunks", [])
    ]
    result = {"text": out["text"].strip(), "segments": segments, "duration_s": round(duration, 2)}
    return result, {"model": model_id(), "ms": (time.perf_counter() - t0) * 1000, "rtf": (time.perf_counter() - t0) / max(duration, 0.1)}
