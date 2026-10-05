"""Infografía numérica. Las cifras salen de la ficha, no de un modelo generativo."""

from __future__ import annotations

from pathlib import Path

from helios.analysis.format import fmt_number, fmt_ratio_as_pct
from helios.compliance.disclaimer import SHORT_DISCLAIMER
from helios.types import FactSheet

BG = (14, 20, 32)
CARD = (24, 34, 50)
GOLD = (224, 177, 90)
TEXT = (244, 241, 234)
MUTED = (154, 164, 178)
GREEN = (61, 220, 151)
RED = (255, 107, 107)
LINE = (46, 58, 79)


def render_infographic(
    facts: FactSheet,
    out_path: Path,
    closes: list[float] | None = None,
    modalities: list[str] | None = None,
) -> Path:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1600, 1000), BG)
    draw = ImageDraw.Draw(image)
    title = _font(42, bold=True)
    small = _font(16)
    label = _font(14, bold=True)
    value_font = _font(34, bold=True)
    body = _font(22)
    tiny = _font(15)

    draw.rectangle((0, 0, 1600, 8), fill=GOLD)
    draw.text((48, 36), "HELIOS", font=title, fill=GOLD)
    draw.text((1120, 52), "INFORME DE MESA", font=small, fill=MUTED)
    draw.text((48, 100), facts.company, font=_font(36, bold=True), fill=TEXT)
    ticker = facts.ticker + ("   ·   caso sintético" if facts.synthetic else "")
    draw.text((48, 150), ticker, font=small, fill=MUTED)
    _pill(draw, facts.stance, 1280, 108)

    cards = [
        ("Ingresos 2025", _metric(facts, "ingresos_2025_m", 0), "millones EUR"),
        ("Margen EBITDA", _metric(facts, "margen_ebitda_pct", 1, suffix="%"), "sobre ingresos"),
        ("Capex 2025", _metric(facts, "capex_2025_m", 0), "millones EUR"),
        ("Deuda neta", _metric(facts, "deuda_neta_m", 0), "millones EUR"),
    ]
    _cards(draw, cards, 48, 210, 1504, 150, label, value_font, small)
    drawdown = fmt_ratio_as_pct(facts.price_stats["max_drawdown"]) if facts.price_stats else "No consta"
    volatility = fmt_ratio_as_pct(facts.price_stats["annualized_volatility"]) if facts.price_stats else "No consta"
    second = [
        ("Guía", facts.guidance_text or "No consta", ""),
        ("Drawdown máximo", drawdown, "caída desde máximos"),
        ("Volatilidad", volatility, "anualizada"),
    ]
    _wide_cards(draw, second, 48, 380, 1504, 130, label, _font(26, bold=True), small)

    draw.rounded_rectangle((48, 530, 860, 860), radius=18, fill=CARD)
    draw.text((72, 552), "SERIE LOCAL", font=label, fill=MUTED)
    if closes and len(closes) > 2:
        _sparkline(draw, closes, (80, 610, 820, 820), GOLD)
    else:
        draw.text((72, 640), "Sin serie de precios en este expediente.", font=body, fill=MUTED)

    draw.rounded_rectangle((884, 530, 1552, 860), radius=18, fill=CARD)
    draw.text((908, 552), "RIESGO OPERATIVO", font=label, fill=MUTED)
    risk = facts.risk_text or "No consta un riesgo explícito en el expediente."
    _write_lines(draw, risk, (908, 600), 600, body, TEXT, 6)

    footer = f"{SHORT_DISCLAIMER}  Modalidades: {', '.join(modalities or ['expediente'])}."
    _write_lines(draw, footer, (48, 890), 1500, tiny, MUTED, 2)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, format="PNG")
    return out_path


def _metric(facts: FactSheet, key: str, decimals: int, suffix: str = "") -> str:
    if key not in facts.metrics:
        return "No consta"
    return f"{fmt_number(facts.metrics[key], decimals)}{suffix}"


def _cards(draw, cards, x, y, width, height, label_font, value_font, sub_font) -> None:
    gap = 16
    card_w = (width - gap * (len(cards) - 1)) / len(cards)
    for index, (label, value, sub) in enumerate(cards):
        left = x + index * (card_w + gap)
        box = (left, y, left + card_w, y + height)
        draw.rounded_rectangle(box, radius=18, fill=CARD)
        draw.text((left + 22, y + 18), label.upper(), font=label_font, fill=MUTED)
        draw.text((left + 22, y + 52), value, font=value_font, fill=TEXT)
        if sub:
            draw.text((left + 22, y + 108), sub, font=sub_font, fill=GOLD)


def _wide_cards(draw, cards, x, y, width, height, label_font, value_font, sub_font) -> None:
    weights = [2.2, 1, 1]
    gap = 16
    total = sum(weights)
    usable = width - gap * (len(cards) - 1)
    cursor = x
    for (label, value, sub), weight in zip(cards, weights):
        card_w = usable * weight / total
        draw.rounded_rectangle((cursor, y, cursor + card_w, y + height), radius=18, fill=CARD)
        draw.text((cursor + 22, y + 16), label.upper(), font=label_font, fill=MUTED)
        shown = value if len(value) < 48 else value[:45] + "..."
        draw.text((cursor + 22, y + 48), shown, font=value_font, fill=TEXT)
        if sub:
            draw.text((cursor + 22, y + 92), sub, font=sub_font, fill=GOLD)
        cursor += card_w + gap


def _pill(draw, stance: str, x: int, y: int) -> None:
    colors = {"Vigilar": GOLD, "Constructivo": GREEN, "Defensivo": RED}
    color = colors.get(stance, MUTED)
    font = _font(20, bold=True)
    width = max(160, int(draw.textlength(stance, font=font)) + 36)
    draw.rounded_rectangle((x, y, x + width, y + 46), radius=23, fill=color)
    ink = BG if stance != "Neutral" else TEXT
    draw.text((x + 18, y + 10), stance, font=font, fill=ink)


def _sparkline(draw, closes: list[float], box: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = box
    low = min(closes)
    high = max(closes)
    span = high - low or 1.0
    points = []
    last_index = max(1, len(closes) - 1)
    for index, value in enumerate(closes):
        x = x0 + (x1 - x0) * index / last_index
        y = y1 - (y1 - y0) * ((value - low) / span)
        points.append((x, y))
    draw.line(points, fill=color, width=3)
    draw.line((x0, y1, x1, y1), fill=LINE, width=1)


def _write_lines(draw, text: str, origin: tuple[int, int], max_width: int, font, fill, limit: int) -> None:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= limit:
            break
    if current and len(lines) < limit:
        lines.append(current)
    x, y = origin
    for line in lines[:limit]:
        draw.text((x, y), line, font=font, fill=fill)
        y += int(font.size * 1.35) if hasattr(font, "size") else 22


def _font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()
