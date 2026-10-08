"""Gestor de VRAM: un único modelo grande en la GPU en cada momento.

Con 8 GB de VRAM no caben a la vez Whisper (1,6 GB), Qwen2.5-VL 7B (6 GB),
Qwen3 8B (5,2 GB) y SDXL-Turbo (7 GB). Nuestra política es:

* Los modelos pequeños (e5, SigLIP2, CLAP, Piper y las cabezas Keras) viven en
  CPU: en un Ryzen moderno tardan decenas de milisegundos y no compiten por VRAM.
* Los grandes se turnan la GPU. Antes de que uno entre, desalojamos al anterior:
  Whisper y SDXL se mueven a RAM (volver tarda <1 s) y a Ollama le pedimos que
  descargue sus modelos con `keep_alive=0`.
* Un cerrojo reentrante serializa el acceso, porque Gradio atiende peticiones en
  hilos y dos cargas simultáneas provocarían un OOM.
"""

from __future__ import annotations

import gc
import json
import threading
import time
import urllib.request
from contextlib import contextmanager
from typing import Callable

import torch

from diputado import config

HAS_CUDA = torch.cuda.is_available()
DEVICE = "cuda" if HAS_CUDA else "cpu"
DTYPE = torch.float16 if HAS_CUDA else torch.float32
SMALL_DEVICE = "cpu"


def vram_gb() -> float:
    if not HAS_CUDA:
        return 0.0
    return torch.cuda.get_device_properties(0).total_memory / 2**30


LIGHT_MODE = (not HAS_CUDA) or vram_gb() < 7.5


class GPUManager:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.owner: str | None = None
        self._evictors: dict[str, Callable[[], None]] = {"ollama": unload_ollama}
        self.events: list[dict] = []

    def register(self, owner: str, evict: Callable[[], None]) -> None:
        self._evictors[owner] = evict

    @contextmanager
    def claim(self, owner: str):
        """Reserva la GPU para `owner`, desalojando al ocupante anterior."""
        with self.lock:
            # Ollama es otro proceso: puede tener modelos en VRAM aunque aquí aún no haya dueño.
            previous = self.owner or ("ollama" if owner != "ollama" and ollama_running_models() else None)
            if previous not in (None, owner):
                t0 = time.perf_counter()
                evict = self._evictors.get(previous)
                if evict:
                    try:
                        evict()
                    except Exception as exc:
                        print(f"[gpu] no se pudo desalojar {previous}: {exc}")
                gc.collect()
                if HAS_CUDA:
                    torch.cuda.empty_cache()
                self.events.append(
                    {"t": time.time(), "evicted": previous, "for": owner, "ms": (time.perf_counter() - t0) * 1000}
                )
            self.owner = owner
            yield

    def snapshot(self) -> dict:
        info = {"owner": self.owner, "device": DEVICE, "light_mode": LIGHT_MODE}
        if HAS_CUDA:
            free, total = torch.cuda.mem_get_info()
            info.update(
                vram_total_gb=round(total / 2**30, 2),
                vram_free_gb=round(free / 2**30, 2),
                torch_alloc_gb=round(torch.cuda.memory_allocated() / 2**30, 2),
            )
        return info


def _post(path: str, payload: dict, timeout: float = 30) -> dict:
    req = urllib.request.Request(
        f"{config.OLLAMA_HOST}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def ollama_running_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_HOST}/api/ps", timeout=3) as r:
            return [m["name"] for m in json.load(r).get("models", [])]
    except Exception:
        return []


def unload_ollama() -> None:
    for name in ollama_running_models():
        try:
            _post("/api/generate", {"model": name, "keep_alive": 0})
        except Exception:
            pass
    for _ in range(20):
        if not ollama_running_models():
            break
        time.sleep(0.25)


gpu = GPUManager()
