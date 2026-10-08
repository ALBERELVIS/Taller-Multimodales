"""Fuentes tipográficas: usamos DejaVu, que viene con matplotlib en todos los sistemas."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import matplotlib
from PIL import ImageFont

_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
_LOCAL = Path(__file__).resolve().parent / "fonts"


@lru_cache(maxsize=64)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    local = _LOCAL / ("AtkinsonHyperlegible-Bold.ttf" if bold else "AtkinsonHyperlegible-Regular.ttf")
    if local.exists():
        return ImageFont.truetype(str(local), size)
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(_DIR / name), size)


def wrap(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if fnt.getlength(trial) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines
