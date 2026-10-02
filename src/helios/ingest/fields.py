"""Extracción de campos financieros desde texto de un informe."""

from __future__ import annotations

import re

from helios.analysis.format import fmt_number
from helios.analysis.numbers import parse_number_token

_SIMPLE = {
    "ingresos_2025_m": r"INGRESOS 2025:\s*([0-9][0-9.,]*)",
    "ebitda_2025_m": r"EBITDA 2025:\s*([0-9][0-9.,]*)",
    "margen_ebitda_pct": r"MARGEN EBITDA:\s*([0-9][0-9.,]*)\s*%",
    "capex_2025_m": r"CAPEX 2025:\s*([0-9][0-9.,]*)",
    "deuda_neta_m": r"DEUDA NETA:\s*([0-9][0-9.,]*)",
}


def extract_document(text: str) -> dict[str, object]:
    fields: dict[str, float] = {}
    for key, pattern in _SIMPLE.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = parse_number_token(match.group(1))
        if value is not None:
            fields[key] = value
    guidance = re.search(
        r"GUIDANCE INGRESOS 2026:\s*([0-9][0-9.,]*)\s*[-–]\s*([0-9][0-9.,]*)",
        text,
        flags=re.IGNORECASE,
    )
    guidance_text = ""
    if guidance:
        low = parse_number_token(guidance.group(1))
        high = parse_number_token(guidance.group(2))
        if low is not None:
            fields["guidance_baja_m"] = low
        if high is not None:
            fields["guidance_alta_m"] = high
        if low is not None and high is not None:
            guidance_text = (
                f"Ingresos 2026 entre {fmt_number(low)} y {fmt_number(high)} millones EUR"
            )
    delay = re.search(r"retraso de\s+(\d+)\s+meses", text, flags=re.IGNORECASE)
    if delay:
        fields["retraso_permiso_meses"] = float(delay.group(1))
    risk_match = re.search(r"RIESGO PRINCIPAL:\s*(.+)", text, flags=re.IGNORECASE)
    company_match = re.search(r"COMPA[NÑ][IÍ]A:\s*(.+)", text, flags=re.IGNORECASE)
    ticker_match = re.search(r"TICKER:\s*([A-Za-z0-9]+)", text, flags=re.IGNORECASE)
    return {
        "fields": fields,
        "risk_text": risk_match.group(1).strip() if risk_match else "",
        "guidance_text": guidance_text,
        "company": company_match.group(1).strip() if company_match else None,
        "ticker": ticker_match.group(1).strip().upper() if ticker_match else None,
    }


def page_of(pages: list[str], label: str) -> int | None:
    needle = label.lower()
    for index, page in enumerate(pages, start=1):
        if needle in page.lower():
            return index
    return None
