"""Cliente fino sobre Ollama con salida JSON validada por esquema."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import ollama

from diputado import config
from diputado.ai import ollama_server
from diputado.ai.gpu import gpu

_client: ollama.Client | None = None


def client() -> ollama.Client:
    global _client
    if _client is None:
        ollama_server.ensure_server()
        _client = ollama.Client(host=config.OLLAMA_HOST, timeout=300)
    return _client


def prime_vram(model: str) -> None:
    """Carga un modelo diminuto antes de un modelo de visión que aún no está en memoria.

    Ollama 0.35 en Windows no logra refrescar la VRAM libre al cambiar de modelo (su descubrimiento de GPU agota
    el tiempo) y reutiliza la medida tomada con el modelo anterior cargado: con Qwen3 en VRAM cree que quedan
    1,1 GB y deja el codificador de imagen de Qwen2.5-VL en CPU (140 s por captura en lugar de 35 s). Tras cargar
    un modelo de 46 MB, la medida que reutiliza es la buena.
    """
    from diputado.ai.gpu import ollama_running_models

    if model in ollama_running_models():
        return
    try:
        client().embed(model=config.OLLAMA_PRIMER, input="x", keep_alive="10m")
    except Exception:
        pass


def _supports_think(model: str) -> bool:
    return model.startswith(("qwen3", "deepseek-r1", "gpt-oss"))


def _parse_json(text: str) -> Any:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            return json.loads(match.group(0))
        raise


def chat(
    model: str,
    messages: list[dict],
    schema: dict | None = None,
    temperature: float = 0.0,
    num_ctx: int = 8192,
    num_predict: int = 1024,
    seed: int | None = 7,
) -> tuple[Any, dict]:
    """Llama a Ollama. Devuelve (contenido, métricas). Si hay esquema, el contenido es un dict."""
    kwargs: dict[str, Any] = {}
    if _supports_think(model):
        kwargs["think"] = False
    options = {"temperature": temperature, "num_ctx": num_ctx, "num_predict": num_predict}
    if seed is not None:
        options["seed"] = seed
    last_exc: Exception | None = None
    with gpu.claim("ollama"):
        if any(m.get("images") for m in messages):
            prime_vram(model)
        for attempt in range(2):
            t0 = time.perf_counter()
            try:
                resp = client().chat(
                    model=model,
                    messages=messages,
                    format=schema if schema else None,
                    options=options,
                    keep_alive="10m",
                    **kwargs,
                )
            except Exception as exc:
                last_exc = exc
                ollama_server.ensure_server()
                continue
            content = resp["message"]["content"]
            metrics = {
                "model": model,
                "ms": (time.perf_counter() - t0) * 1000,
                "load_ms": (resp.get("load_duration") or 0) / 1e6,
                "prompt_tokens": resp.get("prompt_eval_count"),
                "output_tokens": resp.get("eval_count"),
            }
            if not schema:
                return content, metrics
            try:
                return _parse_json(content), metrics
            except (json.JSONDecodeError, ValueError) as exc:
                last_exc = exc
                options["temperature"] = 0.2
    raise RuntimeError(f"Ollama ({model}) no ha devuelto una respuesta válida: {last_exc}")


def available() -> bool:
    return ollama_server.is_up()
