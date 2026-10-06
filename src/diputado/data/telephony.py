"""Simulación de canal telefónico para que voz real y sintética pasen por lo mismo.

Si entrenásemos con voz real de audiolibro (limpia, 16 kHz) frente a voz sintética,
el clasificador aprendería el "atajo" de la calidad de grabación. Pasamos ambas por
el mismo canal: 8 kHz, banda 300-3400 Hz, compresión mu-law de 8 bits y ruido.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt

from diputado.ai.audio_io import resample


def mulaw(x: np.ndarray, mu: int = 255) -> np.ndarray:
    y = np.sign(x) * np.log1p(mu * np.abs(x)) / np.log1p(mu)
    y = np.round((y + 1) / 2 * mu) / mu * 2 - 1
    return np.sign(y) * (np.expm1(np.abs(y) * np.log1p(mu))) / mu


def phone_channel(audio: np.ndarray, sr: int, rng: np.random.Generator | None = None, out_sr: int | None = None) -> np.ndarray:
    rng = rng or np.random.default_rng()
    x = resample(audio, sr, 8000)
    sos = butter(4, [300, 3400], btype="bandpass", fs=8000, output="sos")
    x = sosfilt(sos, x)
    x = x / (np.abs(x).max() + 1e-6) * rng.uniform(0.4, 0.9)
    x = mulaw(np.clip(x, -1, 1))
    snr_db = rng.uniform(18, 35)
    noise = rng.normal(0, 1, len(x)) * np.sqrt(np.mean(x**2) / 10 ** (snr_db / 10))
    x = (x + noise).astype(np.float32)
    return resample(x, 8000, out_sr or sr)
