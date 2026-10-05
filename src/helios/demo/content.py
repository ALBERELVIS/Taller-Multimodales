"""Textos del caso demo, compartidos por el PDF, la prensa y la evaluación."""

from __future__ import annotations

from helios.analysis.format import fmt_number
from helios.demo.truth import COMPANY, FIELDS, RISK_TEXT, TICKER


def fact_lines() -> list[str]:
    return [
        f"COMPAÑÍA: {COMPANY}",
        f"TICKER: {TICKER}",
        f"INGRESOS 2025: {int(FIELDS['ingresos_2025_m'])} millones EUR",
        f"EBITDA 2025: {int(FIELDS['ebitda_2025_m'])} millones EUR",
        f"MARGEN EBITDA: {fmt_number(FIELDS['margen_ebitda_pct'], 1)} %",
        f"CAPEX 2025: {int(FIELDS['capex_2025_m'])} millones EUR",
        f"DEUDA NETA: {int(FIELDS['deuda_neta_m'])} millones EUR",
        (
            "GUIDANCE INGRESOS 2026: "
            f"{int(FIELDS['guidance_baja_m'])}-{int(FIELDS['guidance_alta_m'])} millones EUR"
        ),
    ]


def risk_line() -> str:
    return f"RIESGO PRINCIPAL: {RISK_TEXT}"


def news_items() -> list[dict[str, str]]:
    ingresos = int(FIELDS["ingresos_2025_m"])
    ebitda = int(FIELDS["ebitda_2025_m"])
    margin = fmt_number(FIELDS["margen_ebitda_pct"], 1)
    capex = int(FIELDS["capex_2025_m"])
    debt = int(FIELDS["deuda_neta_m"])
    low = int(FIELDS["guidance_baja_m"])
    high = int(FIELDS["guidance_alta_m"])
    months = int(FIELDS["retraso_permiso_meses"])
    return [
        {
            "id": "n1",
            "title": "NorteGrid retrasa Cabo Prior",
            "date": "2026-02-12",
            "source": "Helios Wire",
            "body": (
                f"NorteGrid comunicó un retraso de {months} meses en el permiso del parque eólico de Cabo Prior. "
                f"La compañía indicó que el retraso puede desplazar parte del capex de {capex} millones EUR."
            ),
        },
        {
            "id": "n2",
            "title": "NorteGrid cierra 2025 con margen del 28,4%",
            "date": "2026-02-18",
            "source": "Helios Wire",
            "body": (
                f"Los ingresos de 2025 fueron {ingresos} millones EUR y el EBITDA {ebitda} millones EUR, "
                f"con un margen EBITDA del {margin}%. La deuda neta cerró en {debt} millones EUR."
            ),
        },
        {
            "id": "n3",
            "title": "Guía de ingresos 2026",
            "date": "2026-02-18",
            "source": "Helios Wire",
            "body": (
                f"La guía de ingresos para 2026 se sitúa entre {low} y {high} millones EUR, "
                "condicionada a que el permiso de Cabo Prior no sufra un segundo retraso."
            ),
        },
    ]
