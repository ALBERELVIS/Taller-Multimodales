"""Serie de precios desde CSV local o, si se pide, desde Yahoo Finance."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from helios.analysis.risk import compute_stats


@dataclass
class MarketSnapshot:
    dates: list[str]
    closes: list[float]
    stats: dict[str, float]
    source: str


def load_prices(path: Path | None, live_ticker: str | None = None) -> MarketSnapshot | None:
    if path is not None and path.exists():
        dates, closes = _read_csv(path)
        return _snapshot(dates, closes, f"CSV {path.name}")
    if live_ticker:
        dates, closes = _download(live_ticker)
        return _snapshot(dates, closes, f"yfinance:{live_ticker}")
    return None


def _read_csv(path: Path) -> tuple[list[str], list[float]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "close" not in {key.lower() for key in rows[0]}:
        raise ValueError("El CSV de precios necesita una columna close.")
    dates: list[str] = []
    closes: list[float] = []
    for row in rows:
        lowered = {str(key).lower(): value for key, value in row.items()}
        if lowered.get("close") in (None, ""):
            continue
        closes.append(float(lowered["close"]))
        dates.append(str(lowered.get("date", ""))[:10])
    if not closes:
        raise ValueError("La serie de precios está vacía.")
    return dates, closes


def _download(ticker: str) -> tuple[list[str], list[float]]:
    try:
        import pandas as pd
        import yfinance as yf
    except ImportError as exc:
        raise ValueError("Los precios en vivo necesitan yfinance y pandas.") from exc
    frame = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
    if frame is None or len(frame) == 0:
        raise ValueError(f"Sin precios para {ticker}.")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.reset_index()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    date_key = "date" if "date" in frame.columns else "datetime"
    closes = [float(value) for value in frame["close"].tolist() if pd.notna(value)]
    dates = [str(value)[:10] for value in frame[date_key].tolist()][: len(closes)]
    if not closes:
        raise ValueError(f"Sin precios para {ticker}.")
    return dates, closes


def _snapshot(dates: list[str], closes: list[float], source: str) -> MarketSnapshot:
    return MarketSnapshot(dates=dates, closes=closes, stats=compute_stats(closes), source=source)
