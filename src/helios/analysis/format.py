"""Formato numérico en español, sin separador de miles."""

from __future__ import annotations


def fmt_number(value: float, decimals: int = 0) -> str:
    if decimals <= 0 and abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    text = f"{float(value):.{decimals}f}"
    whole, frac = text.split(".")
    return f"{whole},{frac}"


def fmt_pct_points(value: float, decimals: int = 1) -> str:
    return f"{fmt_number(value, decimals)}%"


def fmt_ratio_as_pct(ratio: float, decimals: int = 1) -> str:
    return fmt_pct_points(abs(ratio) * 100.0, decimals)
