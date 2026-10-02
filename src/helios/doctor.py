"""Estado del entorno local, sin descargar modelos."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass

from helios.config import Settings
from helios.demo.case import demo_dir


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def readiness(settings: Settings | None = None) -> list[Check]:
    settings = settings or Settings.from_env()
    checks = [
        Check("Python", sys.version_info >= (3, 10), sys.version.split()[0]),
        _module("PyMuPDF", "pymupdf"),
        _module("Streamlit", "streamlit"),
        _module("faster-whisper", "faster_whisper"),
        _module("edge-tts", "edge_tts"),
        _module("pyttsx3", "pyttsx3"),
        _module("sentence-transformers", "sentence_transformers"),
        _module("open-clip", "open_clip"),
        _ollama(settings),
        _demo(),
        Check(
            "Hardware orientativo",
            True,
            "16 GB de RAM y 10-12 GB de disco para los modelos de 7B.",
        ),
    ]
    return checks


def _module(name: str, module: str) -> Check:
    found = importlib.util.find_spec(module) is not None
    return Check(name, found, "instalado" if found else "no instalado")


def _ollama(settings: Settings) -> Check:
    if shutil.which("ollama") is None:
        try:
            from helios.models.ollama_client import OllamaClient

            client = OllamaClient(settings)
            if client.healthy():
                names = ", ".join(client.model_names()) or "servidor vacío"
                return Check("Ollama", True, names)
        except Exception as exc:
            return Check("Ollama", False, str(exc))
        return Check("Ollama", False, "el ejecutable no está en el PATH")
    from helios.models.ollama_client import OllamaClient

    client = OllamaClient(settings)
    if not client.healthy():
        return Check("Ollama", False, "no responde. Arranca ollama serve.")
    installed = client.model_names()
    text = client.resolve(settings.text_model, settings.text_fallbacks)
    vision = client.resolve(settings.vision_model, settings.vision_fallbacks)
    detail = f"texto={text or 'no'}; visión={vision or 'no'}; instalados={len(installed)}"
    return Check("Ollama", True, detail)


def _demo() -> Check:
    folder = demo_dir()
    needed = ["resultados.pdf", "velas.png", "precios.csv", "noticias.json", "verdad.json", "guion.txt"]
    missing = [name for name in needed if not (folder / name).exists()]
    audio = (folder / "llamada.mp3").exists() or (folder / "llamada.wav").exists()
    if missing or not audio:
        detail = "falta " + ", ".join(missing + ([] if audio else ["audio"]))
        return Check("Caso NorteGrid", False, detail + ". Ejecuta scripts/build_demo_case.py.")
    return Check("Caso NorteGrid", True, "listo")


def main() -> int:
    print("Helios · diagnóstico local")
    for check in readiness():
        mark = "OK" if check.ok else "PENDIENTE"
        print(f"[{mark}] {check.name}: {check.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
