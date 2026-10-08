"""Ilustraciones para la infografía con SDXL-Turbo (diffusers)."""

from __future__ import annotations

import threading
import time

import torch
from PIL import Image

from diputado import config
from diputado.ai.gpu import DTYPE, HAS_CUDA, LIGHT_MODE, gpu

_pipe = None
_load_lock = threading.Lock()

STYLE = (
    "cybersecurity HUD, dark background, neon cyan and red wireframe, holographic, futuristic, "
    "circuit grid, one centered object, no text, no letters, no watermark"
)


def enabled() -> bool:
    return HAS_CUDA and not LIGHT_MODE


def _evict() -> None:
    if _pipe is not None:
        _pipe.maybe_free_model_hooks()


def _get():
    global _pipe
    with _load_lock:
        if _pipe is None:
            from diffusers import AutoPipelineForText2Image

            _pipe = AutoPipelineForText2Image.from_pretrained(
                config.HF_MODELS["sdxl"]["id"], torch_dtype=DTYPE, variant="fp16"
            )
            _pipe.enable_model_cpu_offload()
            _pipe.set_progress_bar_config(disable=True)
            gpu.register("sdxl", _evict)
    return _pipe


@torch.inference_mode()
def generate(prompt: str, seed: int = 0, steps: int = 2, size: int = 512) -> tuple[Image.Image, dict]:
    if not enabled():
        raise RuntimeError("SDXL-Turbo necesita una GPU NVIDIA con 8 GB")
    t0 = time.perf_counter()
    with gpu.claim("sdxl"):
        pipe = _get()
        gen = torch.Generator("cpu").manual_seed(seed)
        image = pipe(
            prompt=f"{prompt}, {STYLE}",
            num_inference_steps=steps,
            guidance_scale=0.0,
            height=size,
            width=size,
            generator=gen,
        ).images[0]
    return image, {"model": config.HF_MODELS["sdxl"]["id"], "ms": (time.perf_counter() - t0) * 1000, "steps": steps, "seed": seed}
