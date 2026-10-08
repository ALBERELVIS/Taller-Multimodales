"""Voz de la aplicación: un hombre, español de España (Piper, es_ES-davefx).

MMS-TTS sigue en el repositorio para fabricar el dataset de VozSinteticaNet y como
referencia del notebook 04. Su acento no es el de España, así que no es la voz
que oye el cliente en el aviso, la respuesta ni el vídeo.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from diputado import config
from diputado.ai.gpu import SMALL_DEVICE

_lock = threading.Lock()

_UNITS = "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis diecisiete dieciocho diecinueve veinte veintiuno veintidós veintitrés veinticuatro veinticinco veintiséis veintisiete veintiocho veintinueve".split()
_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
_HUNDREDS = {100: "ciento", 200: "doscientos", 300: "trescientos", 400: "cuatrocientos", 500: "quinientos",
             600: "seiscientos", 700: "setecientos", 800: "ochocientos", 900: "novecientos"}
VOICE_NAME = "es_ES-davefx-medium"


def number_to_words(n: int) -> str:
    """Convierte un entero (0 a 999.999.999) a palabras en español."""
    if n < 30:
        return _UNITS[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        return _TENS[tens * 10] + ("" if unit == 0 else " y " + _UNITS[unit])
    if n < 1000:
        if n == 100:
            return "cien"
        h, rest = divmod(n, 100)
        return _HUNDREDS[h * 100] + ("" if rest == 0 else " " + number_to_words(rest))
    if n < 1_000_000:
        th, rest = divmod(n, 1000)
        head = "mil" if th == 1 else number_to_words(th).replace("uno", "un") + " mil"
        return head + ("" if rest == 0 else " " + number_to_words(rest))
    mill, rest = divmod(n, 1_000_000)
    head = "un millón" if mill == 1 else number_to_words(mill).replace("uno", "un") + " millones"
    return head + ("" if rest == 0 else " " + number_to_words(rest))


def normalize_for_speech(text: str) -> str:
    """Pasa cifras, símbolos y URLs a palabras para que el locutor las pronuncie."""
    t = text
    t = re.sub(r"https?://", "", t)
    t = re.sub(r"(\d+),(\d{1,2})\s*€", lambda m: f"{m.group(1)} euros con {m.group(2)}", t)
    t = re.sub(r"\b(\d{1,3}(?:\.\d{3})+)\b", lambda m: m.group(1).replace(".", ""), t)
    t = re.sub(r"(\d+),(\d+)", r"\1 coma \2", t)
    for _ in range(3):
        t = re.sub(r"([A-Za-zñáéíóú0-9])\.([A-Za-zñáéíóú])", r"\1 punto \2", t)
        t = re.sub(r"([A-Za-zñáéíóú0-9])-([A-Za-zñáéíóú0-9])", r"\1 guion \2", t)
    t = t.replace("€", " euros").replace("%", " por ciento").replace("&", " y ").replace("@", " arroba ")
    t = re.sub(r"\d{5,}", lambda m: " ".join(_UNITS[int(d)] for d in m.group(0)), t)
    t = re.sub(r"\d+", lambda m: number_to_words(int(m.group(0))), t)
    t = re.sub(r"\b([A-ZÁÉÍÓÚÑ]{2,5})\b", lambda m: m.group(1).lower(), t)
    t = re.sub(r"[\"“”«»()\[\]*_#/\\|<>]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?¡¿:;])\s+", text)
    return [p for p in (s.strip() for s in parts) if len(p) > 1]


@lru_cache(maxsize=1)
def _mms():
    from transformers import AutoTokenizer, VitsModel

    mid = config.HF_MODELS["tts"]["id"]
    tok = AutoTokenizer.from_pretrained(mid)
    model = VitsModel.from_pretrained(mid).to(SMALL_DEVICE).eval()
    return tok, model


@lru_cache(maxsize=1)
def _piper():
    from huggingface_hub import hf_hub_download
    from piper import PiperVoice

    spec = config.HF_MODELS["piper"]
    onnx = hf_hub_download(spec["id"], spec["file"])
    hf_hub_download(spec["id"], spec["file"] + ".json")
    return PiperVoice.load(onnx)


@torch.inference_mode()
def synthesize_mms(text: str, speaking_rate: float = 0.95, seed: int = 3) -> tuple[np.ndarray, int]:
    """Voz de MMS-TTS, solo para el dataset de entrenamiento."""
    with _lock:
        tok, model = _mms()
        model.speaking_rate = speaking_rate
        sr = model.config.sampling_rate
        pause = np.zeros(int(sr * 0.25), dtype=np.float32)
        chunks = []
        torch.manual_seed(seed)
        for sent in _sentences(normalize_for_speech(text)) or [normalize_for_speech(text)]:
            ids = tok(sent, return_tensors="pt").to(SMALL_DEVICE)
            if ids["input_ids"].shape[-1] < 2:
                continue
            wav = model(**ids).waveform[0].cpu().numpy().astype(np.float32)
            chunks += [wav, pause]
    audio = np.concatenate(chunks) if chunks else np.zeros(sr, dtype=np.float32)
    peak = float(np.abs(audio).max()) or 1.0
    return (0.9 * audio / peak).astype(np.float32), sr


def synthesize(text: str, length_scale: float = 1.08) -> tuple[np.ndarray, int]:
    """Locución en español de España. length_scale > 1 habla más despacio."""
    from piper.config import SynthesisConfig

    spoken = normalize_for_speech(text)
    with _lock:
        voice = _piper()
        chunks = [
            c.audio_float_array.astype(np.float32)
            for c in voice.synthesize(spoken, syn_config=SynthesisConfig(length_scale=length_scale))
        ]
        sr = voice.config.sample_rate
    if not chunks:
        return np.zeros(sr, dtype=np.float32), sr
    pause = np.zeros(int(sr * 0.16), dtype=np.float32)
    pieces: list[np.ndarray] = []
    for wav in chunks:
        pieces += [wav, pause]
    audio = np.concatenate(pieces)
    peak = float(np.abs(audio).max()) or 1.0
    return (0.9 * audio / peak).astype(np.float32), sr


def speak(text: str, out_dir: Path | None = None) -> tuple[str, dict]:
    t0 = time.perf_counter()
    audio, sr = synthesize(text)
    out_dir = out_dir or config.OUTPUTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"aviso_{uuid.uuid4().hex[:8]}.wav"
    sf.write(path, audio, sr)
    return str(path), {
        "model": f"piper {VOICE_NAME}",
        "ms": (time.perf_counter() - t0) * 1000,
        "audio_s": len(audio) / sr,
    }
