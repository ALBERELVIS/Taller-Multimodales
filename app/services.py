"""Arranque de la aplicación: precarga de modelos en segundo plano y estado de preparación."""

from __future__ import annotations

import threading
import time
import traceback

from diputado import config

STATUS: dict[str, str] = {}
_started = False


def _task(name: str, fn) -> None:
    STATUS[name] = "cargando"
    try:
        fn()
        STATUS[name] = "listo"
    except Exception as exc:
        STATUS[name] = f"error: {exc}"
        traceback.print_exc()


def _warm_ollama() -> None:
    from diputado.ai import ollama_client

    ollama_client.chat(config.OLLAMA_LLM, [{"role": "user", "content": "Responde solo: ok"}], num_predict=3)


def _warm_whisper() -> None:
    from diputado.ai import asr
    from diputado.ai.gpu import HAS_CUDA, gpu

    with gpu.claim("whisper"):
        asr._get()
    if HAS_CUDA:
        asr._evict()


def _warm_sdxl() -> None:
    from diputado.ai import imagegen

    if imagegen.enabled():
        imagegen.generate("warm up", steps=1, size=256)


def _warm_keras() -> None:
    import numpy as np

    from diputado.ai import keras_heads

    if keras_heads.tactics_available():
        keras_heads.predict_tactics(np.zeros(384, dtype="float32"))
    if keras_heads.voice_available():
        keras_heads.predict_voice(np.zeros(512, dtype="float32"))


def warmup() -> None:
    global _started
    if _started:
        return
    _started = True
    from diputado.ai import audio_clap, embeddings, tts
    from diputado.core import campaigns, cases_db

    tasks = [
        ("Base de casos", cases_db.init),
        ("Campañas", lambda: campaigns.search(embeddings.embed_text("hola")[0])),
        ("e5 (texto)", lambda: embeddings.embed_text("hola")),
        ("SigLIP2 (imagen)", lambda: embeddings.embed_image_texts(["hola"])),
        ("CLAP (audio)", lambda: audio_clap.zero_shot(audio_clap.embed_audio(__import__("numpy").zeros(48000, dtype="float32")))),
        ("MMS-TTS (voz)", lambda: tts.synthesize("Hola.")),
        ("Modelos Keras", _warm_keras),
        ("Whisper", _warm_whisper),
        ("SDXL-Turbo (infografía)", _warm_sdxl),
        ("Qwen3 (Ollama)", _warm_ollama),
    ]
    for name, _ in tasks:
        STATUS[name] = "pendiente"

    def run_all():
        t0 = time.time()
        for name, fn in tasks:
            _task(name, fn)
        STATUS["_total_s"] = f"{time.time() - t0:.0f}"

    threading.Thread(target=run_all, daemon=True).start()


def ready() -> bool:
    return bool(STATUS) and all(v == "listo" or v.startswith("error") for k, v in STATUS.items() if not k.startswith("_"))


def status_html() -> str:
    from diputado.ai.gpu import DEVICE, LIGHT_MODE, vram_gb

    items = {k: v for k, v in STATUS.items() if not k.startswith("_")}
    n_ok = sum(v == "listo" for v in items.values())
    gpu = f"GPU {vram_gb():.0f} GB" if DEVICE == "cuda" else "CPU"
    mode = " · modo ligero" if LIGHT_MODE else ""
    if items and n_ok == len(items):
        badge = f'<span class="dd-badge ok">Todo listo · {n_ok} componentes · 100 % local</span>'
    else:
        current = next((k for k, v in items.items() if v == "cargando"), "")
        badge = f'<span class="dd-badge wait">Preparando modelos {n_ok}/{len(items)} {current}</span>'
    errors = [k for k, v in items.items() if v.startswith("error")]
    err = f'<br><span class="dd-badge">Sin: {", ".join(errors)}</span>' if errors else ""
    return f'{badge}<br><span class="dd-badge">{gpu}{mode}</span><span class="dd-badge">Sin APIs de pago</span>{err}'
