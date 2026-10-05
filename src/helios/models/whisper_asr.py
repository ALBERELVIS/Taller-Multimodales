"""Transcripción local con faster-whisper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from helios.cache import digest, remember
from helios.config import Settings
from helios.models.errors import ModelUnavailable

_MODEL = None
_MODEL_KEY = ""


@dataclass
class Transcript:
    text: str
    segments: list[dict[str, float | str]]
    language: str
    model: str


def transcribe(path: Path, settings: Settings) -> tuple[Transcript, bool]:
    file_bytes = path.read_bytes()
    key = digest(settings.whisper_model.encode(), settings.whisper_compute.encode(), file_bytes)

    def produce() -> dict:
        transcript = _run(path, settings)
        return {
            "text": transcript.text,
            "segments": transcript.segments,
            "language": transcript.language,
            "model": transcript.model,
        }

    payload, cached = remember("whisper", key, settings, produce)
    return (
        Transcript(
            text=str(payload.get("text", "")),
            segments=list(payload.get("segments", [])),
            language=str(payload.get("language", "")),
            model=str(payload.get("model", settings.whisper_model)),
        ),
        cached,
    )


def _run(path: Path, settings: Settings) -> Transcript:
    global _MODEL, _MODEL_KEY
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ModelUnavailable("faster-whisper no está instalado.") from exc
    key = f"{settings.whisper_model}|{settings.whisper_device}|{settings.whisper_compute}"
    if _MODEL is None or _MODEL_KEY != key:
        _MODEL = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute,
        )
        _MODEL_KEY = key
    segments, info = _MODEL.transcribe(str(path), vad_filter=True)
    collected = []
    texts = []
    for segment in segments:
        text = segment.text.strip()
        collected.append({"start": float(segment.start), "end": float(segment.end), "text": text})
        if text:
            texts.append(text)
    language = getattr(info, "language", "") or ""
    return Transcript(text=" ".join(texts), segments=collected, language=language, model=settings.whisper_model)
