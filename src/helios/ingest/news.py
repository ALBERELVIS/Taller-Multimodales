"""Noticias del expediente, en JSON o en un texto plano."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class NewsItem:
    id: str
    title: str
    date: str
    source: str
    body: str


def load_news(path: Path) -> list[NewsItem]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload["items"] if isinstance(payload, dict) else payload
        return [
            NewsItem(
                id=str(item.get("id", f"n{index}")),
                title=str(item.get("title", "Noticia")),
                date=str(item.get("date", "")),
                source=str(item.get("source", "")),
                body=str(item.get("body", "")),
            )
            for index, item in enumerate(items, start=1)
        ]
    body = path.read_text(encoding="utf-8")
    return [NewsItem(id="n1", title=path.stem, date="", source="carga del usuario", body=body)]
