from __future__ import annotations

import pytest

from helios.analysis.citations import filter_unsupported_sentences
from helios.analysis.numbers import collect_allowed, is_supported, support_ratio
from helios.analysis.thesis import render_template
from helios.demo.truth import FIELDS, RISK_TEXT
from helios.types import FactSheet


def test_years_do_not_match_each_other():
    assert is_supported(2025, [2025])
    assert not is_supported(2026, [2025])
    assert is_supported(842, [840])
    assert not is_supported(99, [28.4, 842])


def test_filter_drops_only_the_sentence_with_an_unknown_figure():
    allowed = [842, 28.4, 2025]
    text = "Los ingresos fueron 842 millones en 2025. El margen inventado es 99%. El margen real es 28,4%."
    outcome = filter_unsupported_sentences(text, allowed)
    assert "99" not in outcome.text
    assert "842" in outcome.text
    assert "28,4" in outcome.text
    assert outcome.support_ratio == 1
    assert len(outcome.rejected) == 1
    assert support_ratio(text, allowed) == pytest.approx(0.75)


def test_citations_are_not_counted_as_financial_figures():
    allowed = [842, 2025]
    text = "Ingresos 2025: 842 millones EUR [PDF p.1]."
    assert support_ratio(text, allowed) == 1
    outcome = filter_unsupported_sentences(text, allowed)
    assert outcome.rejected == []


def test_template_publishes_only_anchored_numbers():
    metrics = dict(FIELDS)
    stats = {
        "last_close": 27.2,
        "max_drawdown": -0.18,
        "annualized_volatility": 0.2,
        "total_return": 0.36,
        "trading_days": 252.0,
        "first_close": 20.0,
        "peak_close": 30.0,
        "trough_close": 24.6,
    }
    guidance = "Ingresos 2026 entre 910 y 940 millones EUR"
    facts = FactSheet(
        company="NorteGrid",
        ticker="NRGX",
        synthetic=True,
        metrics=metrics,
        metric_sources={key: "PDF p.1" for key in metrics},
        risk_text=RISK_TEXT,
        guidance_text=guidance,
        chart_caption="",
        price_stats=stats,
        stance="Vigilar",
        numbers_origin="text",
    )
    facts.metric_sources["risk"] = "PDF p.2"
    allowed = collect_allowed(metrics, stats, [guidance, RISK_TEXT, "Informe 2025"])
    text = render_template(facts, news_title="NorteGrid retrasa Cabo Prior", audio_locator="Audio 00:12")
    outcome = filter_unsupported_sentences(text, allowed)
    assert outcome.rejected == [], outcome.rejected
    assert support_ratio(text, allowed) == 1
