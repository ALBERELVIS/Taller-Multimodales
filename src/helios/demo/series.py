"""Serie de precios sintética con un drawdown plantado. No depende de pandas."""

from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from helios.analysis.risk import compute_stats


class PriceFrame:
    def __init__(self, columns: dict[str, np.ndarray | list]):
        self.columns = columns

    def __getitem__(self, key: str):
        return self.columns[key]


def business_days(periods: int, end: str) -> list[str]:
    cursor = datetime.strptime(end, "%Y-%m-%d")
    found: list[str] = []
    while len(found) < periods:
        if cursor.weekday() < 5:
            found.append(cursor.strftime("%Y-%m-%d"))
        cursor -= timedelta(days=1)
    return list(reversed(found))


def synthetic_ohlc(periods: int = 252, end: str = "2026-03-31") -> PriceFrame:
    """Construye velas diarias. El cierre toca 30 y después 24,6, un 18% por debajo."""
    if periods < 220:
        raise ValueError("La serie demo necesita al menos 220 sesiones.")
    closes = np.empty(periods, dtype=float)
    rise_end = 180
    drop_end = 200
    closes[:rise_end] = np.linspace(20.0, 30.0, rise_end)
    closes[rise_end:drop_end] = np.linspace(30.0, 24.6, drop_end - rise_end, endpoint=False)
    closes[drop_end - 1] = 24.6
    closes[drop_end:] = np.linspace(24.6, 27.2, periods - drop_end)
    rng = np.random.default_rng(7)
    noise = rng.normal(0.0, 0.04, periods)
    noise[rise_end - 1] = 0.0
    noise[drop_end - 1] = 0.0
    closes = closes + noise
    closes[: rise_end - 1] = np.minimum(closes[: rise_end - 1], 29.7)
    closes[rise_end:] = np.clip(closes[rise_end:], 24.6, 29.5)
    closes[rise_end - 1] = 30.0
    closes[drop_end - 1] = 24.6

    opens = np.empty(periods, dtype=float)
    opens[0] = closes[0]
    opens[1:] = closes[:-1]
    highs = np.maximum(opens, closes) + 0.08
    lows = np.minimum(opens, closes) - 0.08
    volume = rng.integers(180_000, 420_000, periods).astype(float)
    volume[rise_end:drop_end] *= 2.4
    return PriceFrame(
        {
            "date": np.array(business_days(periods, end)),
            "open": np.round(opens, 4),
            "high": np.round(highs, 4),
            "low": np.round(lows, 4),
            "close": np.round(closes, 4),
            "volume": volume.astype(int),
        }
    )


def write_csv(frame: PriceFrame, path: Path) -> None:
    keys = ["date", "open", "high", "low", "close", "volume"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(keys)
        writer.writerows(zip(*(frame[key] for key in keys), strict=True))


def realized_drawdown(frame: PriceFrame) -> float:
    stats = compute_stats(np.asarray(frame["close"], dtype=float))
    return float(stats["max_drawdown"])


def assert_planted_drop(frame: PriceFrame, target: float = -0.18, tolerance: float = 0.02) -> float:
    drawdown = realized_drawdown(frame)
    if not math.isfinite(drawdown) or abs(drawdown - target) > tolerance:
        raise RuntimeError(f"El drawdown plantado es {drawdown:.3%}, se esperaba cerca de {target:.0%}.")
    return drawdown
