"""Diagrama de la orquestación para el README y la ficha de arquitectura."""

from __future__ import annotations

from pathlib import Path

BG = (14, 20, 32)
CARD = (24, 34, 50)
GOLD = (224, 177, 90)
TEXT = (244, 241, 234)
MUTED = (154, 164, 178)


def render_architecture(out_path: Path) -> Path:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1600, 520), BG)
    draw = ImageDraw.Draw(image)
    title = _font(28, bold=True)
    label = _font(18, bold=True)
    draw.text((40, 28), "Helios  ·  orquestación multimodal", font=title, fill=TEXT)
    sources = ["PDF", "Gráfico", "Audio", "Prensa", "Precios"]
    _row(draw, sources, 40, 110, 1520, 70, label)
    _arrow_down(draw, 800, 190)
    _row(draw, ["Orquestador", "Cifras en código", "Tesis citada", "Infografía y voz"], 40, 250, 1520, 80, label)
    note = _font(16)
    draw.text(
        (40, 380),
        "El modelo de lenguaje no publica una cifra que no esté en el PDF, la prensa o la serie.",
        font=note,
        fill=MUTED,
    )
    draw.text(
        (40, 420),
        "Visión, transcripción y embeddings son etapas distintas. Si una falta, la mesa sigue y lo marca.",
        font=note,
        fill=MUTED,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, format="PNG")
    return out_path


def _row(draw, labels: list[str], x: int, y: int, width: int, height: int, font) -> None:
    gap = 16
    card_w = (width - gap * (len(labels) - 1)) / len(labels)
    for index, label in enumerate(labels):
        left = x + index * (card_w + gap)
        draw.rounded_rectangle((left, y, left + card_w, y + height), radius=16, fill=CARD, outline=GOLD, width=2)
        text_w = draw.textlength(label, font=font)
        draw.text((left + (card_w - text_w) / 2, y + height / 2 - 12), label, font=font, fill=TEXT)


def _arrow_down(draw, x: int, y: int) -> None:
    draw.line((x, y, x, y + 40), fill=GOLD, width=3)
    draw.polygon([(x - 8, y + 32), (x + 8, y + 32), (x, y + 46)], fill=GOLD)


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
