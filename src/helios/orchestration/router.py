"""Clasifica un archivo del expediente según su modalidad."""

from __future__ import annotations

from pathlib import Path

CHART_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}


def route_file(path: Path) -> str:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in CHART_EXTENSIONS:
        return "chart"
    if suffix == ".csv" or "precio" in name or "price" in name:
        return "prices"
    if suffix == ".json" or "noticia" in name or "news" in name:
        return "news"
    if suffix in {".txt", ".md"}:
        return "news"
    return "unknown"
