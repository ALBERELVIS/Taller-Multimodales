"""Voz sintetizada. edge-tts no pide clave; si no hay red, habla el sistema."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from helios.config import Settings
from helios.models.errors import ModelUnavailable


def synthesize(text: str, out_path: Path, settings: Settings) -> tuple[Path, str]:
    if settings.tts_mode in {"off", "none", "0"}:
        raise ModelUnavailable("La síntesis de voz está desactivada (HELIOS_TTS=off).")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if settings.tts_mode == "system":
        return _system(text, out_path.with_suffix(".wav")), "pyttsx3"
    try:
        return _edge(text, out_path.with_suffix(".mp3"), settings.tts_voice), "edge-tts"
    except Exception:
        return _system(text, out_path.with_suffix(".wav")), "pyttsx3"


def _edge(text: str, out_path: Path, voice: str) -> Path:
    import edge_tts

    async def _save() -> None:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(out_path))

    asyncio.run(asyncio.wait_for(_save(), timeout=60))
    if not out_path.exists() or out_path.stat().st_size < 100:
        raise RuntimeError("edge-tts no escribió audio.")
    return out_path


def _system(text: str, out_path: Path) -> Path:
    script = """
import sys
import pyttsx3
text = sys.stdin.buffer.read().decode("utf-8")
out = sys.argv[1]
engine = pyttsx3.init()
for voice in engine.getProperty("voices") or []:
    blob = f"{getattr(voice, 'name', '')} {getattr(voice, 'id', '')}".lower()
    if "spanish" in blob or "es-es" in blob or "helena" in blob or "laura" in blob or "elvira" in blob:
        engine.setProperty("voice", voice.id)
        break
engine.save_to_file(text, out)
engine.runAndWait()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(out_path)],
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0 or not out_path.exists() or out_path.stat().st_size < 100:
        detail = completed.stderr.decode("utf-8", errors="replace")[-400:]
        raise ModelUnavailable(detail or "La voz del sistema no generó archivo.")
    return out_path
