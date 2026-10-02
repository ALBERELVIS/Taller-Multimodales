"""Metadatos de la imagen del gráfico. Las cifras de precio no se leen de los píxeles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChartImage:
    path: Path
    width: int
    height: int


def load_chart(path: Path) -> ChartImage:
    from PIL import Image

    with Image.open(path) as image:
        width, height = image.size
    return ChartImage(path=path, width=width, height=height)
