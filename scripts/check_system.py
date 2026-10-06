"""Diagnóstico del equipo con mensajes claros para personas no técnicas."""

from __future__ import annotations

import platform
import shutil
import socket
import sys

from diputado import config

OK, WARN, FAIL = "[ OK ]", "[AVISO]", "[FALLO]"


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def main() -> int:
    print(f"\n=== Diagnóstico de {config.BRAND_NAME} ===\n")
    problems = 0
    print(f"{OK} Sistema: {platform.system()} {platform.release()} · Python {sys.version.split()[0]}")

    try:
        import psutil

        ram = psutil.virtual_memory().total / 1e9
        mark = OK if ram >= 15 else WARN
        print(f"{mark} Memoria RAM: {ram:.0f} GB" + ("" if ram >= 15 else " (recomendamos 16 GB o más)"))
    except ImportError:
        pass

    free = shutil.disk_usage(config.ROOT).free / 1e9
    needed = 0 if (config.MODELS_DIR / ".complete").exists() else 30
    mark = OK if free >= needed else FAIL
    problems += free < needed
    print(f"{mark} Disco libre: {free:.0f} GB" + (f" (necesitamos unos {needed} GB para los modelos)" if needed else ""))

    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 2**30
            mark = OK if vram >= 7.5 else WARN
            print(f"{mark} GPU: {name} con {vram:.1f} GB de VRAM")
            if vram < 7.5:
                print("       Con menos de 8 GB la app funciona, pero desactivaremos la infografía generada.")
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            print(f"{WARN} GPU Apple (MPS): funcionará, aunque más despacio que con NVIDIA.")
        else:
            print(f"{WARN} No hay GPU NVIDIA: la app funcionará en modo ligero (más lenta y sin infografía IA).")
    except Exception as exc:
        print(f"{FAIL} PyTorch no se ha cargado bien: {exc}")
        problems += 1

    from diputado.ai import ollama_server

    binary = ollama_server.find_binary()
    if binary:
        print(f"{OK} Ollama encontrado en {binary}")
    else:
        print(f"{WARN} Ollama no está instalado: el instalador descargará la versión portable.")

    if not port_free(config.APP_PORT):
        print(f"{WARN} El puerto {config.APP_PORT} está ocupado: quizá la app ya está abierta.")
    print()
    if problems:
        print("Hay problemas que impiden continuar. Revisa los mensajes [FALLO].")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
