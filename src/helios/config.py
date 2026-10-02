"""Configuración única de modelos, voz y coste."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or (ROOT / ".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    ollama_host: str = "http://127.0.0.1:11434"
    text_model: str = "qwen2.5:7b"
    text_fallbacks: tuple[str, ...] = ("qwen2.5:3b", "llama3.2:3b")
    vision_model: str = "qwen2.5vl:7b"
    vision_fallbacks: tuple[str, ...] = ("llava:7b", "moondream")
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute: str = "int8"
    tts_mode: str = "edge"
    tts_voice: str = "es-ES-ElviraNeural"
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    clip_model: str = "ViT-B-32"
    clip_pretrained: str = "openai"
    cache_enabled: bool = True
    electricity_eur_kwh: float = 0.18
    hardware_watts: float = 65.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        cache_raw = os.getenv("HELIOS_CACHE", "1").strip().lower()
        return cls(
            ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/"),
            text_model=os.getenv("HELIOS_TEXT_MODEL", "qwen2.5:7b"),
            text_fallbacks=_csv_tuple(os.getenv("HELIOS_TEXT_FALLBACKS", "qwen2.5:3b,llama3.2:3b")),
            vision_model=os.getenv("HELIOS_VISION_MODEL", "qwen2.5vl:7b"),
            vision_fallbacks=_csv_tuple(os.getenv("HELIOS_VISION_FALLBACKS", "llava:7b,moondream")),
            whisper_model=os.getenv("HELIOS_WHISPER_MODEL", "small"),
            whisper_device=os.getenv("HELIOS_WHISPER_DEVICE", "cpu"),
            whisper_compute=os.getenv("HELIOS_WHISPER_COMPUTE", "int8"),
            tts_mode=os.getenv("HELIOS_TTS", "edge").strip().lower(),
            tts_voice=os.getenv("HELIOS_TTS_VOICE", "es-ES-ElviraNeural"),
            embed_model=os.getenv("HELIOS_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            clip_model=os.getenv("HELIOS_CLIP_MODEL", "ViT-B-32"),
            clip_pretrained=os.getenv("HELIOS_CLIP_PRETRAINED", "openai"),
            cache_enabled=cache_raw not in {"0", "false", "no", "off"},
            electricity_eur_kwh=float(os.getenv("HELIOS_EUR_KWH", "0.18")),
            hardware_watts=float(os.getenv("HELIOS_WATTS", "65")),
        )

    @property
    def root(self) -> Path:
        return ROOT

    @property
    def cache_dir(self) -> Path:
        path = ROOT / "data" / "cache"
        path.mkdir(parents=True, exist_ok=True)
        return path
