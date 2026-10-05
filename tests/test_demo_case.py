"""El PDF generado y la serie plantada coinciden con la verdad terreno."""

import json
from pathlib import Path

import pytest

from helios.analysis.risk import compute_stats
from helios.analysis.score import score_fields
from helios.ingest.market import load_prices
from helios.ingest.pdf import read_pdf

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "data" / "samples" / "nortegrid"


@pytest.mark.skipif(not (CASE / "resultados.pdf").exists(), reason="Caso demo aún no generado")
def test_demo_pdf_matches_truth():
    truth = json.loads((CASE / "verdad.json").read_text(encoding="utf-8"))
    document = read_pdf(CASE / "resultados.pdf")
    score = score_fields(document.fields, truth["fields"])
    assert score["f1"] == 1.0
    assert truth["risk_text"] in document.risk_text or document.risk_text == truth["risk_text"]


@pytest.mark.skipif(not (CASE / "precios.csv").exists(), reason="Caso demo aún no generado")
def test_demo_drawdown_is_the_planted_drop():
    snapshot = load_prices(CASE / "precios.csv")
    assert snapshot is not None
    stats = compute_stats(snapshot.closes)
    assert stats["max_drawdown"] == pytest.approx(-0.18, abs=0.02)
