"""Infografía educativa: ilustración de SDXL-Turbo + texto compuesto con Pillow.

SDXL no sabe escribir texto legible, así que separamos responsabilidades:
el modelo genera solo la ilustración y nosotros maquetamos el texto encima.
Antes de aceptar una ilustración la puntuamos con SigLIP2 (similitud con el prompt)
y, si queda por debajo del umbral, probamos otra semilla: un control de calidad
automático inspirado en el notebook de IQA.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

from diputado import config
from diputado.media.fonts import font, wrap

W, H = 1080, 1350
BG = (7, 11, 18)
INK = (231, 244, 251)
CYAN = (62, 224, 255)
COLORS = {"rojo": (255, 59, 84), "ambar": (255, 176, 32), "verde": (29, 255, 176)}
BANNERS = {"rojo": "ALERTA DE ESTAFA", "ambar": "PRECAUCIÓN", "verde": "PARECE SEGURO"}

# Objetos de ciberseguridad, no caras: SDXL-Turbo en pocos pasos dibuja mal a las personas.
SCENES = {
    "suplantacion_entidad": "a holographic shield cracking over a dark smartphone, cyan circuit lines",
    "falso_familiar": "a digital mask hovering over a dark chat window, cyan wireframe",
    "credenciales_otp": "a glowing padlock and six neon dots on a dark screen",
    "enlace_sospechoso": "a neon fishing hook made of light, dark circuit grid",
    "pago_transferencia": "coins dissolving into red digital particles over a dark phone",
    "premio_inversion": "a neon trap box on a dark circuit board",
    "urgencia_amenaza": "a red hexagonal alert and a radar pulse on a dark HUD",
    "verde": "a cyan shield with a check mark on a dark circuit background",
}
QUALITY_THRESHOLD = 0.06
# De la táctica más específica (la que mejor resume la estafa) a la más genérica.
SCENE_PRIORITY = ["falso_familiar", "premio_inversion", "credenciales_otp", "enlace_sospechoso",
                  "suplantacion_entidad", "pago_transferencia", "urgencia_amenaza"]


def prompt_for(level: str, tactics: dict[str, float]) -> str:
    if level == "verde":
        return SCENES["verde"]
    for t in SCENE_PRIORITY:
        if tactics.get(t, 0) >= 0.5:
            return SCENES[t]
    return SCENES["suplantacion_entidad"]


def _fallback_hero(level: str, size=(880, 880)) -> Image.Image:
    """Ilustración de plantilla para equipos sin GPU: retícula y escudo, sin caras."""
    c = COLORS[level]
    hero = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(hero)
    for x in range(0, size[0], 40):
        d.line([(x, 0), (x, size[1])], fill=(16, 36, 48))
    for y in range(0, size[1], 40):
        d.line([(0, y), (size[0], y)], fill=(16, 36, 48))
    d.regular_polygon((440, 400, 210), 6, outline=CYAN, width=6)
    d.regular_polygon((440, 400, 150), 6, outline=c, width=4)
    mark = "OK" if level == "verde" else "!"
    d.text((440, 400), mark, font=font(120, True), fill=c, anchor="mm")
    return hero


def illustration(level: str, tactics: dict[str, float], seed: int = 0) -> tuple[Image.Image, dict]:
    from diputado.ai import imagegen

    prompt = prompt_for(level, tactics)
    if not imagegen.enabled():
        return _fallback_hero(level), {"model": "plantilla (sin GPU)", "ms": 0, "prompt": prompt}
    from diputado.ai import embeddings

    t0 = time.perf_counter()
    tries = []
    best = None
    for k in range(2):
        img, m = imagegen.generate(prompt, seed=seed + k, steps=4)
        score = embeddings.image_text_score(img, prompt)
        tries.append({"seed": seed + k, "siglip_score": round(score, 4)})
        if best is None or score > best[1]:
            best = (img, score)
        if score >= QUALITY_THRESHOLD:
            break
    hero = best[0].resize((880, 880), Image.LANCZOS)
    return hero, {"model": config.HF_MODELS["sdxl"]["id"], "ms": (time.perf_counter() - t0) * 1000, "prompt": prompt,
                  "intentos": tries, "siglip_score": round(best[1], 4)}


def _fit(hero: Image.Image, w: int, h: int) -> Image.Image:
    img = hero.convert("RGB")
    scale = max(w / img.width, h / img.height)
    nw, nh = max(w, int(img.width * scale)), max(h, int(img.height * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _brackets(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int], arm: int = 28) -> None:
    x0, y0, x1, y1 = box
    for xa, ya, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(xa, ya), (xa + dx * arm, ya)], fill=color, width=3)
        d.line([(xa, ya), (xa, ya + dy * arm)], fill=color, width=3)


def compose(level: str, title: str, signals: list[str], advice: list[str], hero: Image.Image) -> Image.Image:
    c = COLORS[level]
    card = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(card)
    for x in range(0, W, 36):
        d.line([(x, 0), (x, H)], fill=(12, 22, 32))
    d.rectangle((0, 0, W, 108), fill=(5, 10, 16))
    d.rectangle((0, 104, W, 108), fill=c)
    d.text((56, 52), BANNERS[level], font=font(36, True), fill=c, anchor="lm")
    d.text((W - 56, 52), config.BRAND_NAME, font=font(24, True), fill=CYAN, anchor="rm")

    frame = (56, 140, W - 56, 680)
    picture = _fit(hero, frame[2] - frame[0], frame[3] - frame[1])
    card.paste(picture, (frame[0], frame[1]))
    d.rectangle(frame, outline=CYAN, width=2)
    _brackets(d, (frame[0] - 8, frame[1] - 8, frame[2] + 8, frame[3] + 8), CYAN)

    y = 720
    for i, line in enumerate(wrap(title, font(44, True), W - 112)[:2]):
        d.text((56, y + i * 52), line, font=font(44, True), fill=INK)
    y += 52 * min(2, len(wrap(title, font(44, True), W - 112))) + 28
    d.text((56, y), "LO DETECTADO" if level != "verde" else "COMPROBADO", font=font(26, True), fill=CYAN)
    y += 48
    for s in signals[:3]:
        d.rectangle((56, y + 10, 74, y + 28), outline=c, width=2)
        lines = wrap(s, font(30), W - 180)[:2]
        for j, line in enumerate(lines):
            d.text((96, y + j * 38), line, font=font(30), fill=INK)
        y += 38 * len(lines) + 12
    y += 10
    d.text((56, y), "QUÉ HACER", font=font(26, True), fill=CYAN)
    y += 48
    for i, a in enumerate(advice[:3], 1):
        d.ellipse((56, y + 2, 98, y + 44), outline=c, width=2)
        d.text((77, y + 23), str(i), font=font(22, True), fill=c, anchor="mm")
        lines = wrap(a, font(28), W - 190)[:2]
        for j, line in enumerate(lines):
            d.text((116, y + j * 36), line, font=font(28), fill=INK)
        y += 36 * len(lines) + 14
    d.rectangle((0, H - 72, W, H), fill=(5, 8, 12))
    d.rectangle((0, H - 72, W, H - 69), fill=CYAN)
    d.text((56, H - 36), config.AI_WATERMARK, font=font(20), fill=(142, 175, 192), anchor="lm")
    d.text((W - 56, H - 36), "Tu banco nunca te pedirá claves", font=font(20, True), fill=CYAN, anchor="rm")
    return card


def make(level: str, title: str, signals: list[str], advice: list[str], tactics: dict[str, float],
         out_dir: Path | None = None, seed: int = 0) -> tuple[str, dict]:
    hero, meta = illustration(level, tactics, seed)
    card = compose(level, title, signals, advice, hero)
    out_dir = out_dir or config.OUTPUTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"infografia_{uuid.uuid4().hex[:8]}.png"
    card.save(path, optimize=True)
    return str(path), meta
