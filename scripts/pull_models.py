"""Descarga los modelos de Ollama que falten. Si el servidor no está, avisa y sigue."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from helios.config import Settings
from helios.models.ollama_client import OllamaClient


def main() -> int:
    settings = Settings.from_env()
    client = OllamaClient(settings)
    if not client.healthy():
        print(f"Ollama no responde en {settings.ollama_host}.")
        print("Arranca 'ollama serve' y vuelve a ejecutar scripts/pull_models.py.")
        print("La aplicación puede abrirse igual: las etapas de modelo figurarán como omitidas.")
        return 0
    _ensure(client, settings.text_model, settings.text_fallbacks, "texto")
    _ensure(client, settings.vision_model, settings.vision_fallbacks, "visión")
    text = client.resolve(settings.text_model, settings.text_fallbacks)
    vision = client.resolve(settings.vision_model, settings.vision_fallbacks)
    print(f"Texto listo: {text or 'ninguno'}")
    print(f"Visión lista: {vision or 'ninguna'}")
    return 0


def _ensure(client: OllamaClient, preferred: str, fallbacks: tuple[str, ...], kind: str) -> None:
    if client.resolve(preferred, ()):
        print(f"{kind}: ya está {preferred}")
        return
    print(f"{kind}: descargando {preferred}")
    try:
        client.pull(preferred)
        return
    except Exception as exc:
        print(f"No se pudo descargar {preferred}: {exc}")
    for name in fallbacks:
        if client.resolve(name, ()):
            print(f"{kind}: se usará {name}")
            return
        print(f"{kind}: descargando alternativa {name}")
        try:
            client.pull(name)
            return
        except Exception as exc:
            print(f"No se pudo descargar {name}: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
