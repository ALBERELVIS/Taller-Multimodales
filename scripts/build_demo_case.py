"""Genera el expediente sintético de NorteGrid: PDF, velas, guion, audio y verdad terreno."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from helios.analysis.risk import compute_stats
from helios.config import Settings
from helios.demo.content import fact_lines, news_items, risk_line
from helios.demo.series import assert_planted_drop, synthetic_ohlc, write_csv
from helios.demo.truth import CHART_PATTERN, COMPANY, EARNINGS_SCRIPT, FIELDS, RISK_TEXT, TICKER, TRANSCRIPT_KEYWORDS
from helios.viz.architecture import render_architecture


def main() -> int:
    folder = ROOT / "data" / "samples" / "nortegrid"
    folder.mkdir(parents=True, exist_ok=True)
    frame = synthetic_ohlc()
    drawdown = assert_planted_drop(frame)
    write_csv(frame, folder / "precios.csv")
    _write_pdf(folder / "resultados.pdf")
    _write_chart(frame, folder / "velas.png")
    (folder / "guion.txt").write_text(EARNINGS_SCRIPT + "\n", encoding="utf-8")
    (folder / "noticias.json").write_text(json.dumps(news_items(), ensure_ascii=False, indent=2), encoding="utf-8")
    audio_path, audio_engine = _write_audio(folder)
    stats = compute_stats(frame["close"])
    truth = {
        "company": COMPANY,
        "ticker": TICKER,
        "synthetic": True,
        "currency": "EUR",
        "fields": FIELDS,
        "risk_text": RISK_TEXT,
        "chart_pattern": CHART_PATTERN,
        "max_drawdown": drawdown,
        "price_stats": stats,
        "transcript_keywords": TRANSCRIPT_KEYWORDS,
        "audio_file": audio_path.name if audio_path else None,
        "audio_engine": audio_engine,
    }
    (folder / "verdad.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    docs = ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    render_architecture(docs / "arquitectura.png")
    print(f"Caso demo en {folder}")
    print(f"Drawdown plantado: {drawdown:.2%}")
    print(f"Audio: {audio_engine}")
    return 0


def _write_pdf(path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    regular, bold = _register_fonts(pdfmetrics, TTFont)
    document = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    def chrome(subtitle: str) -> None:
        document.setFillColorRGB(0.055, 0.078, 0.125)
        document.rect(0, height - 2.3 * cm, width, 2.3 * cm, fill=1, stroke=0)
        document.setFillColorRGB(0.878, 0.694, 0.353)
        document.setFont(bold, 16)
        document.drawString(1.6 * cm, height - 1.35 * cm, "NORTEGRID")
        document.setFillColorRGB(0.96, 0.95, 0.93)
        document.setFont(regular, 10)
        document.drawRightString(width - 1.6 * cm, height - 1.35 * cm, subtitle)

    chrome("DOCUMENTO SINTÉTICO")
    document.setFillColorRGB(0.12, 0.14, 0.18)
    y = height - 3.3 * cm
    document.setFont(bold, 18)
    document.drawString(1.6 * cm, y, "Informe de resultados 2025")
    y -= 0.8 * cm
    document.setFont(regular, 11)
    for paragraph in _wrap(
        "NorteGrid desarrolla y opera nudos de red para energía renovable en el norte de la península. "
        "Las cifras de este informe están redondeadas a millones de euros. "
        "No es una comunicación oficial ni una recomendación de inversión.",
        95,
    ):
        document.drawString(1.6 * cm, y, paragraph)
        y -= 0.55 * cm
    y -= 0.4 * cm
    document.setFont(regular, 12)
    for line in fact_lines():
        document.drawString(1.6 * cm, y, line)
        y -= 0.7 * cm
    document.setFont(regular, 9)
    document.setFillColorRGB(0.35, 0.38, 0.42)
    document.drawString(1.6 * cm, 1.4 * cm, "DATOS SINTÉTICOS · NO CONSTITUYE ASESORAMIENTO DE INVERSIÓN")
    document.showPage()

    chrome("RIESGO Y GUÍA")
    document.setFillColorRGB(0.12, 0.14, 0.18)
    y = height - 3.3 * cm
    document.setFont(bold, 16)
    document.drawString(1.6 * cm, y, "Riesgo principal y guía")
    y -= 1.0 * cm
    document.setFont(regular, 12)
    document.drawString(1.6 * cm, y, risk_line())
    y -= 1.0 * cm
    document.setFont(regular, 11)
    prose = (
        "El equipo directivo comunicó que el retraso de 6 meses puede desplazar una parte del capex de 310 millones EUR "
        "ya anunciado. La guía de ingresos se mantiene entre 910 y 940 millones EUR, condicionada a que el permiso "
        "de Cabo Prior no sufra un segundo retraso. El balance sigue con una deuda neta de 540 millones EUR."
    )
    for paragraph in _wrap(prose, 95):
        document.drawString(1.6 * cm, y, paragraph)
        y -= 0.55 * cm
    document.setFont(regular, 9)
    document.setFillColorRGB(0.35, 0.38, 0.42)
    document.drawString(1.6 * cm, 1.4 * cm, "PÁGINA 2 · CASO SINTÉTICO NORTEGRID (NRGX)")
    document.save()


def _register_fonts(pdfmetrics, ttfont) -> tuple[str, str]:
    pairs = [
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for regular, bold in pairs:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(ttfont("HeliosBody", regular))
            pdfmetrics.registerFont(ttfont("HeliosBold", bold))
            return "HeliosBody", "HeliosBold"
    return "Times-Roman", "Times-Bold"


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if len(trial) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _write_chart(frame, path: Path) -> None:
    try:
        _write_chart_mplfinance(frame, path)
    except Exception:
        _write_chart_matplotlib(frame, path)


def _write_chart_mplfinance(frame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import mplfinance as mpf
    import pandas as pd

    plot = pd.DataFrame(
        {
            "Open": frame["open"],
            "High": frame["high"],
            "Low": frame["low"],
            "Close": frame["close"],
            "Volume": frame["volume"],
        },
        index=pd.to_datetime(list(frame["date"])),
    )
    figure, _axes = mpf.plot(
        plot,
        type="candle",
        volume=True,
        style="nightclouds",
        returnfig=True,
        figsize=(10, 6),
        title="NRGX  NorteGrid  serie sintetica",
    )
    figure.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(figure)


def _write_chart_matplotlib(frame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    opens = list(frame["open"])
    highs = list(frame["high"])
    lows = list(frame["low"])
    closes = list(frame["close"])
    volume = list(frame["volume"])
    figure, (price, volumes) = plt.subplots(
        2, 1, figsize=(10, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    figure.patch.set_facecolor("#0B1220")
    for axis in (price, volumes):
        axis.set_facecolor("#0B1220")
        axis.tick_params(colors="#C5CDD8")
        for spine in axis.spines.values():
            spine.set_color("#2E3A4F")
    for index, (open_, high, low, close) in enumerate(zip(opens, highs, lows, closes, strict=True)):
        color = "#3DDC97" if close >= open_ else "#FF6B6B"
        price.plot([index, index], [low, high], color=color, linewidth=0.7)
        body = abs(close - open_) or 0.03
        price.add_patch(Rectangle((index - 0.28, min(open_, close)), 0.56, body, facecolor=color, edgecolor=color))
    volumes.bar(range(len(volume)), volume, color="#E0B15A", width=0.7)
    price.set_title("NRGX  NorteGrid  serie sintetica", color="#F4F1EA")
    figure.tight_layout()
    figure.savefig(path, dpi=120, facecolor=figure.get_facecolor())
    plt.close(figure)


def _write_audio(folder: Path) -> tuple[Path | None, str]:
    from helios.models.tts import synthesize

    try:
        path, engine = synthesize(EARNINGS_SCRIPT, folder / "llamada.mp3", Settings.from_env())
        return path, engine
    except Exception as exc:
        print(f"Audio no generado: {exc}")
        return None, "no generado"


if __name__ == "__main__":
    raise SystemExit(main())
