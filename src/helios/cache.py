"""Caché local de transcripciones y lecturas de visión."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from helios.config import Settings


def digest(*parts: bytes) -> str:
    hasher = hashlib.sha256()
    for part in parts:
        hasher.update(part)
        hasher.update(b"\0")
    return hasher.hexdigest()[:24]


def read_json(namespace: str, key: str, settings: Settings) -> dict[str, Any] | None:
    if not settings.cache_enabled:
        return None
    path = _path(namespace, key, settings)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(namespace: str, key: str, settings: Settings, payload: dict[str, Any]) -> None:
    if not settings.cache_enabled:
        return
    path = _path(namespace, key, settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def remember(
    namespace: str,
    key: str,
    settings: Settings,
    producer: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    cached = read_json(namespace, key, settings)
    if cached is not None:
        return cached, True
    payload = producer()
    write_json(namespace, key, settings, payload)
    return payload, False


def _path(namespace: str, key: str, settings: Settings) -> Path:
    return settings.cache_dir / namespace / f"{key}.json"
