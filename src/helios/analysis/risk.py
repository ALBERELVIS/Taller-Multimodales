"""Riesgo de mercado calculado sobre la serie. El modelo no inventa estos números."""

from __future__ import annotations

import math

import numpy as np


def compute_stats(closes: list[float] | np.ndarray, periods_per_year: int = 252) -> dict[str, float]:
    series = np.asarray(closes, dtype=float)
    series = series[np.isfinite(series)]
    if series.size == 0:
        return {}
    first = float(series[0])
    last = float(series[-1])
    stats = {
        "trading_days": float(series.size),
        "first_close": first,
        "last_close": last,
        "peak_close": float(np.max(series)),
        "trough_close": float(np.min(series)),
        "total_return": (last / first - 1.0) if first else 0.0,
        "max_drawdown": max_drawdown(series),
        "annualized_volatility": annualized_volatility(series, periods_per_year),
    }
    return stats


def max_drawdown(closes: np.ndarray) -> float:
    if closes.size == 0:
        return 0.0
    peak = np.maximum.accumulate(closes)
    safe_peak = np.where(peak == 0, 1.0, peak)
    drawdowns = closes / safe_peak - 1.0
    return float(np.min(drawdowns))


def annualized_volatility(closes: np.ndarray, periods_per_year: int = 252) -> float:
    if closes.size < 3:
        return 0.0
    positive = closes[closes > 0]
    if positive.size < 3:
        return 0.0
    log_returns = np.diff(np.log(positive))
    if log_returns.size < 2:
        return 0.0
    return float(np.std(log_returns, ddof=1) * math.sqrt(periods_per_year))
