from __future__ import annotations

import math

import numpy as np
import pytest

from helios.analysis.risk import annualized_volatility, compute_stats, max_drawdown
from helios.analysis.stance import decide_stance
from helios.demo.series import assert_planted_drop, synthetic_ohlc


def test_max_drawdown_from_the_peak():
    closes = np.array([100.0, 110.0, 90.0, 95.0])
    assert max_drawdown(closes) == pytest.approx(90 / 110 - 1)


def test_stats_match_an_independent_volatility_formula():
    closes = np.array([100.0, 110.0, 90.0, 95.0])
    stats = compute_stats(closes)
    log_returns = np.diff(np.log(closes))
    expected = float(np.std(log_returns, ddof=1) * math.sqrt(252))
    assert stats["annualized_volatility"] == pytest.approx(expected)
    assert stats["total_return"] == pytest.approx(-0.05)
    assert stats["last_close"] == 95
    assert stats["max_drawdown"] == pytest.approx(90 / 110 - 1)


def test_short_series_does_not_invent_volatility():
    assert compute_stats([10.0])["annualized_volatility"] == 0
    assert compute_stats([10.0])["max_drawdown"] == 0
    assert compute_stats([]) == {}
    assert annualized_volatility(np.array([5.0, 5.0])) == 0


def test_planted_demo_series_drops_eighteen_percent():
    frame = synthetic_ohlc()
    assert assert_planted_drop(frame) == pytest.approx(-0.18, abs=0.005)


def test_stance_watches_a_deep_drawdown_with_an_operational_risk():
    assert decide_stance({"margen_ebitda_pct": 28.4}, {"max_drawdown": -0.18}, "retraso de permiso") == "Vigilar"
    assert decide_stance({"margen_ebitda_pct": 28.4}, {"max_drawdown": -0.05}, "") == "Constructivo"
    assert decide_stance({"margen_ebitda_pct": 5.0}, {"max_drawdown": -0.01}, "") == "Defensivo"
    assert decide_stance({}, {}, "") == "Neutral"
