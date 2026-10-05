"""Lectura de PDF: capa de texto y páginas renderizadas para el modelo de visión."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from helios.ingest.fields import extract_document, page_of


@dataclass
class PdfDocument:
    text: str
    pages: list[str]
    fields: dict[str, float]
    risk_text: str
    guidance_text: str
    company: str | None
    ticker: str | None
    images: list[bytes] = field(default_factory=list)
    field_pages: dict[str, int] = field(default_factory=dict)


def read_pdf(path: Path, max_pages: int = 2) -> PdfDocument:
    import pymupdf

    document = pymupdf.open(path)
    pages: list[str] = []
    images: list[bytes] = []
    try:
        for index, page in enumerate(document):
            pages.append(page.get_text("text"))
            if index < max_pages:
                pixmap = page.get_pixmap(dpi=140)
                images.append(pixmap.tobytes("png"))
    finally:
        document.close()
    text = "\n".join(pages)
    extracted = extract_document(text)
    field_pages: dict[str, int] = {}
    labels = {
        "ingresos_2025_m": "INGRESOS 2025",
        "ebitda_2025_m": "EBITDA 2025",
        "margen_ebitda_pct": "MARGEN EBITDA",
        "capex_2025_m": "CAPEX 2025",
        "deuda_neta_m": "DEUDA NETA",
        "guidance_baja_m": "GUIDANCE INGRESOS 2026",
        "guidance_alta_m": "GUIDANCE INGRESOS 2026",
        "retraso_permiso_meses": "RIESGO PRINCIPAL",
        "risk": "RIESGO PRINCIPAL",
    }
    for key, label in labels.items():
        found = page_of(pages, label)
        if found:
            field_pages[key] = found
    return PdfDocument(
        text=text,
        pages=pages,
        fields=dict(extracted["fields"]),  # type: ignore[arg-type]
        risk_text=str(extracted["risk_text"]),
        guidance_text=str(extracted["guidance_text"]),
        company=extracted["company"] if isinstance(extracted["company"], str) else None,
        ticker=extracted["ticker"] if isinstance(extracted["ticker"], str) else None,
        images=images,
        field_pages=field_pages,
    )
