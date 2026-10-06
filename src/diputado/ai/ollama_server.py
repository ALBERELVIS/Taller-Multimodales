"""Gestión de una instancia de Ollama propia del proyecto.

Arrancamos `ollama serve` en un puerto dedicado (11435) y con `OLLAMA_MODELS`
apuntando a `./models/ollama`, de modo que los pesos viven dentro del repositorio
y no interferimos con un Ollama que el usuario ya tenga en el puerto 11434.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from diputado import config

PORTABLE_URL = "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip"


def _candidates() -> list[Path]:
    exe = "ollama.exe" if os.name == "nt" else "ollama"
    paths = [config.TOOLS_DIR / "ollama" / exe]
    found = shutil.which("ollama")
    if found:
        paths.append(Path(found))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        paths.append(Path(local) / "Programs" / "Ollama" / exe)
    paths += [
        Path(r"C:\Program Files\Ollama\ollama.exe"),
        Path("/usr/local/bin/ollama"),
        Path("/Applications/Ollama.app/Contents/Resources/ollama"),
    ]
    return paths


def find_binary() -> Path | None:
    for p in _candidates():
        if p.exists():
            return p
    return None


def install_portable() -> Path:
    """Descarga la versión portable oficial de Ollama a .tools/ollama (solo Windows)."""
    target = config.TOOLS_DIR / "ollama"
    target.mkdir(parents=True, exist_ok=True)
    zip_path = config.TOOLS_DIR / "ollama.zip"
    print(f"Descargando Ollama portable desde {PORTABLE_URL} ...")
    with urllib.request.urlopen(PORTABLE_URL) as resp, open(zip_path, "wb") as fh:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        while chunk := resp.read(1 << 20):
            fh.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / total:6.1%} de {total / 1e9:.2f} GB", end="", flush=True)
    print()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(target)
    zip_path.unlink(missing_ok=True)
    return target / "ollama.exe"


def is_up(host: str = config.OLLAMA_HOST, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(f"{host}/api/version", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def server_env() -> dict[str, str]:
    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"127.0.0.1:{config.OLLAMA_PORT}"
    env["OLLAMA_MODELS"] = str(config.OLLAMA_MODELS_DIR)
    env.setdefault("OLLAMA_MAX_LOADED_MODELS", "1")
    env.setdefault("OLLAMA_NUM_PARALLEL", "1")
    env.setdefault("OLLAMA_FLASH_ATTENTION", "1")
    env.setdefault("OLLAMA_KEEP_ALIVE", "10m")
    # Explorar la iGPU por Vulkan puede tardar más de un minuto en portátiles AMD + NVIDIA; mientras tanto
    # Ollama no actualiza la VRAM libre y carga Qwen2.5-VL con el codificador de imagen en CPU (10 veces más lento).
    env.setdefault("OLLAMA_VULKAN", "0")
    return env


def ensure_server(install_if_missing: bool = False, wait_s: float = 180) -> bool:
    """Garantiza que nuestra instancia de Ollama responde. Devuelve True si está lista."""
    if is_up():
        return True
    binary = find_binary()
    if binary is None:
        if not install_if_missing or os.name != "nt":
            return False
        binary = install_portable()
    config.ensure_dirs()
    log_dir = config.ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log = open(log_dir / "ollama.log", "ab")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    subprocess.Popen(
        [str(binary), "serve"],
        env=server_env(),
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        start_new_session=os.name != "nt",
    )
    t0 = time.time()
    while time.time() - t0 < wait_s:
        if is_up():
            return True
        time.sleep(0.5)
    return False


def list_local_models() -> set[str]:
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_HOST}/api/tags", timeout=5) as r:
            data = json.load(r)
        return {m["name"] for m in data.get("models", [])}
    except Exception:
        return set()


def _user_store_candidates() -> list[Path]:
    paths = []
    env_dir = os.environ.get("OLLAMA_MODELS_USER") or os.environ.get("OLLAMA_MODELS")
    if env_dir:
        paths.append(Path(env_dir))
    paths.append(Path.home() / ".ollama" / "models")
    return [p for p in paths if p.resolve() != config.OLLAMA_MODELS_DIR.resolve()]


def import_from_user_store(model: str) -> bool:
    """Reutiliza un modelo que el usuario ya tenga en su Ollama habitual.

    Enlazamos (hardlink) el manifiesto y los blobs en lugar de copiarlos: no ocupa
    disco extra y evita volver a descargar varios GB.
    """
    name, _, tag = model.partition(":")
    tag = tag or "latest"
    for store in _user_store_candidates():
        manifest = store / "manifests" / "registry.ollama.ai" / "library" / name / tag
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"))
        digests = [data["config"]["digest"]] + [layer["digest"] for layer in data["layers"]]
        blobs_src = store / "blobs"
        blobs_dst = config.OLLAMA_MODELS_DIR / "blobs"
        blobs_dst.mkdir(parents=True, exist_ok=True)
        try:
            for d in digests:
                fname = d.replace(":", "-")
                src, dst = blobs_src / fname, blobs_dst / fname
                if not src.exists():
                    raise FileNotFoundError(src)
                if not dst.exists():
                    try:
                        os.link(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)
        except FileNotFoundError:
            continue
        man_dst = config.OLLAMA_MODELS_DIR / "manifests" / "registry.ollama.ai" / "library" / name / tag
        man_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest, man_dst)
        return True
    return False


def pull(model: str) -> None:
    """Descarga un modelo en nuestra instancia mostrando el progreso."""
    req = urllib.request.Request(
        f"{config.OLLAMA_HOST}/api/pull",
        data=json.dumps({"model": model, "stream": True}).encode(),
        headers={"Content-Type": "application/json"},
    )
    last = ""
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            msg = json.loads(line)
            if "error" in msg:
                raise RuntimeError(msg["error"])
            status = msg.get("status", "")
            if msg.get("total"):
                pct = msg.get("completed", 0) / msg["total"]
                print(f"\r  {model}: {status} {pct:6.1%}", end="", flush=True)
            elif status != last:
                print(f"\n  {model}: {status}", end="", flush=True)
            last = status
    print()


if __name__ == "__main__":
    ok = ensure_server(install_if_missing="--install" in sys.argv)
    print("Ollama listo" if ok else "No he podido arrancar Ollama")
    if ok and len(sys.argv) > 2 and sys.argv[1] == "pull":
        for name in sys.argv[2:]:
            pull(name)
    sys.exit(0 if ok else 1)
