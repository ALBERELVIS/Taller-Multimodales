"""Lectura y contraste de cifras. Las fechas civiles no se confunden entre sí."""

from __future__ import annotations

import re

_YEAR_IN_KEY = re.compile(r"20\d{2}")
_NUMBER = re.compile(
    r"(?<![\w])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?)(?![\w])"
)
_CITATION = re.compile(r"\[[^\]]+\]")
_CLOCK = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")


def strip_citations(text: str) -> str:
    without = _CITATION.sub(" ", text)
    return _CLOCK.sub(" ", without)


def parse_number_token(token: str) -> float | None:
    raw = token.strip()
    if not raw:
        return None
    if "." in raw and "," in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        whole, frac = raw.split(",", 1)
        if frac.isdigit() and len(frac) == 3 and whole.isdigit():
            raw = whole + frac
        else:
            raw = whole + "." + frac
    elif raw.count(".") == 1:
        whole, frac = raw.split(".", 1)
        if frac.isdigit() and len(frac) == 3 and whole.isdigit() and len(whole) <= 3:
            raw = whole + frac
    try:
        return float(raw)
    except ValueError:
        return None


def extract_numbers(text: str) -> list[float]:
    values: list[float] = []
    for match in _NUMBER.finditer(text):
        parsed = parse_number_token(match.group(1))
        if parsed is not None:
            values.append(parsed)
    return values


def is_year(value: float) -> bool:
    return 1900 <= value <= 2100 and abs(value - round(value)) < 1e-6


def is_supported(number: float, allowed: list[float]) -> bool:
    for candidate in allowed:
        if is_year(number) or is_year(candidate):
            if abs(number - candidate) < 0.01:
                return True
            continue
        tolerance = 0.15 if abs(candidate) < 100 else max(1.0, abs(candidate) * 0.015)
        if abs(number - candidate) <= tolerance:
            return True
    return False


def support_ratio(text: str, allowed: list[float]) -> float:
    numbers = extract_numbers(strip_citations(text))
    if not numbers:
        return 1.0
    supported = sum(1 for number in numbers if is_supported(number, allowed))
    return supported / len(numbers)


def collect_allowed(metrics: dict[str, float], price_stats: dict[str, float], corpus_texts: list[str]) -> list[float]:
    """Cifras publicables: campos, estadísticos de la serie y texto fuente.

    No entran ni el pie de foto del modelo de visión ni la prosa del modelo de lenguaje.
    Una cifra dicha solo en el audio se publica si también está en el PDF, la prensa o la serie.
    """
    allowed: list[float] = []
    for key in metrics:
        for year in _YEAR_IN_KEY.findall(key):
            allowed.append(float(year))
    for value in list(metrics.values()) + list(price_stats.values()):
        number = float(value)
        allowed.extend([number, abs(number), number * 100.0, abs(number) * 100.0])
    for text in corpus_texts:
        allowed.extend(extract_numbers(text))
    return allowed
