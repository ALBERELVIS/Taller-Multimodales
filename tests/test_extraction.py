import pytest

from helios.analysis.score import score_fields
from helios.config import ROOT
from helios.demo.content import fact_lines, risk_line
from helios.demo.truth import FIELDS
from helios.ingest.fields import extract_document
from helios.ingest.pdf import read_pdf


def test_labeled_demo_text_matches_the_ground_truth():
    text = "\n".join(fact_lines() + [risk_line()])
    extracted = extract_document(text)
    scores = score_fields(extracted["fields"], FIELDS)
    assert scores["f1"] == 1
    assert scores["missing"] == []
    assert extracted["risk_text"].startswith("Retraso de 6 meses")
    assert "910" in extracted["guidance_text"]
    assert extracted["ticker"] == "NRGX"


def test_score_penalizes_a_missing_field():
    predicted = dict(FIELDS)
    del predicted["deuda_neta_m"]
    scores = score_fields(predicted, FIELDS)
    assert "deuda_neta_m" in scores["missing"]
    assert scores["recall"] < 1


def test_generated_pdf_matches_ground_truth():
    pdf = ROOT / "data" / "samples" / "nortegrid" / "resultados.pdf"
    if not pdf.exists():
        pytest.skip("El caso demo todavía no está generado.")
    document = read_pdf(pdf)
    scores = score_fields(document.fields, FIELDS)
    assert scores["f1"] == 1, scores
    assert "Cabo Prior" in document.risk_text
