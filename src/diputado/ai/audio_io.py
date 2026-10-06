"""Lectura de audio en cualquier formato (wav, mp3, m4a, ogg, vídeo...) con ffmpeg.

Decodificamos y remuestreamos en un único paso con el ffmpeg que trae imageio-ffmpeg.
Evitamos librosa porque depende de numba, cuyas DLL bloquea Smart App Control de
Windows 11, y así además aceptamos cualquier formato que grabe un móvil.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from diputado import config


def load(path: str | Path, sr: int = 16_000) -> np.ndarray:
    exe = config.ensure_ffmpeg_on_path() or "ffmpeg"
    cmd = [exe, "-nostdin", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"No he podido leer el audio: {proc.stderr.decode(errors='ignore')[:200]}")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def resample(audio: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return audio.astype(np.float32)
    from math import gcd

    from scipy.signal import resample_poly

    g = gcd(sr_in, sr_out)
    return resample_poly(audio, sr_out // g, sr_in // g).astype(np.float32)
