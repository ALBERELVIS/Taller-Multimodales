"""Descarga todos los modelos a ./models (Hugging Face) y ./models/ollama (Ollama).

Uso:
    python scripts/download_models.py            # todo
    python scripts/download_models.py --light    # sin SDXL ni Bark (equipos sin GPU)
    python scripts/download_models.py --only hf  # solo Hugging Face
"""

from __future__ import annotations

import argparse
import sys
import time

from diputado import config
from diputado.ai import ollama_server

LIGHT_SKIP = {"sdxl", "bark", "asr"}


def download_hf(keys: list[str]) -> list[str]:
    from huggingface_hub import snapshot_download

    failed = []
    for key in keys:
        spec = config.HF_MODELS[key]
        print(f"\n[Hugging Face] {spec['id']}")
        for attempt in range(3):
            try:
                snapshot_download(spec["id"], allow_patterns=spec["allow"])
                break
            except Exception as exc:
                print(f"  intento {attempt + 1} fallido: {exc}")
                time.sleep(3)
        else:
            failed.append(spec["id"])
    return failed


def download_ollama() -> list[str]:
    if not ollama_server.ensure_server(install_if_missing=True):
        print("No he podido arrancar Ollama; revisa logs/ollama.log")
        return list(config.OLLAMA_MODELS)
    failed = []
    for model in config.OLLAMA_MODELS:
        have = ollama_server.list_local_models()
        if model in have:
            print(f"[Ollama] {model}: ya disponible")
            continue
        if ollama_server.import_from_user_store(model):
            print(f"[Ollama] {model}: reutilizado de tu Ollama habitual (sin descargar)")
            continue
        print(f"[Ollama] {model}: descargando")
        try:
            ollama_server.pull(model)
        except Exception as exc:
            print(f"  error: {exc}")
            failed.append(model)
    return failed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--light", action="store_true")
    parser.add_argument("--only", choices=["hf", "ollama"])
    args = parser.parse_args()
    config.ensure_dirs()

    keys = [k for k in config.HF_MODELS if not (args.light and k in LIGHT_SKIP)]
    failed: list[str] = []
    if args.only in (None, "hf"):
        failed += download_hf(keys)
    if args.only in (None, "ollama"):
        failed += download_ollama()

    if failed:
        print("\nNo se han podido descargar:", ", ".join(failed))
        print("Vuelve a ejecutar el instalador cuando tengas conexión estable.")
        return 1
    (config.MODELS_DIR / ".complete").write_text("ok", encoding="utf-8")
    print("\nTodos los modelos están listos en", config.MODELS_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
