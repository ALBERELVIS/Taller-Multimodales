"""Carga del expediente demo ya generado en disco."""

from __future__ import annotations

import json
from pathlib import Path

from helios.config import ROOT
from helios.demo.truth import COMPANY, TICKER
from helios.types import CaseInput

DEMO_DIR = ROOT / "data" / "samples" / "nortegrid"


def demo_dir() -> Path:
    return DEMO_DIR


def _existing(*candidates: Path) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def load_demo_case() -> CaseInput:
    folder = demo_dir()
    return CaseInput(
        company=COMPANY,
        ticker=TICKER,
        pdf_path=_existing(folder / "resultados.pdf"),
        chart_path=_existing(folder / "velas.png"),
        audio_path=_existing(folder / "llamada.mp3", folder / "llamada.wav"),
        news_path=_existing(folder / "noticias.json"),
        prices_path=_existing(folder / "precios.csv"),
        live_prices=False,
        synthetic=True,
    )


def load_truth() -> dict:
    path = demo_dir() / "verdad.json"
    if not path.exists():
        raise FileNotFoundError("No está el caso demo. Ejecuta scripts/build_demo_case.py.")
    return json.loads(path.read_text(encoding="utf-8"))


def load_script() -> str:
    path = demo_dir() / "guion.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    from helios.demo.truth import EARNINGS_SCRIPT

    return EARNINGS_SCRIPT
