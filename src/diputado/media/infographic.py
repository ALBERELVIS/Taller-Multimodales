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
COLORS = {"rojo": (215, 38, 61), "ambar": (232, 145, 40), "verde": (42, 157, 143)}
BANNERS = {"rojo": "ALERTA DE ESTAFA", "ambar": "PRECAUCIÓN", "verde": "PARECE SEGURO"}

SCENES = {
    "suplantacion_entidad": "a worried elderly woman holding a smartphone that shows a fake bank message, a big red warning shield",
    "falso_familiar": "an elderly mother looking at a smartphone chat from an unknown number, a theatrical mask hiding behind the phone",
    "credenciales_otp": "a smartphone showing a secret code and a padlock, a thief hand reaching out to steal the code",
    "enlace_sospechoso": "a smartphone with a message link shaped like a fishing hook, phishing concept",
    "pago_transferencia": "a hand about to send money from a smartphone, euro coins flying away, a big red warning triangle",
    "premio_inversion": "a golden gift box and bitcoin coins on top of a mouse trap, too good to be true",
    "urgencia_amenaza": "a ringing alarm clock next to a smartphone with an urgent red alert",
    "verde": "a smiling elderly couple holding a smartphone with a green check mark shield, feeling safe",
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


def _fallback_hero(level: str, size=(W, 560)) -> Image.Image:
    """Ilustración de plantilla para equipos sin GPU: degradado y escudo vectorial."""
    c = COLORS[level]
    hero = Image.new("RGB", size, c)
    d = ImageDraw.Draw(hero)
    for y in range(size[1]):
        k = y / size[1]
        d.line([(0, y), (size[0], y)], fill=tuple(int(v * (1 - 0.35 * k) + 255 * 0.25 * (1 - k)) for v in c))
    cx, cy, s = size[0] // 2, size[1] // 2 - 70, 150
    d.polygon([(cx, cy - s), (cx + s, cy - s // 2), (cx + s * 0.8, cy + s * 0.6), (cx, cy + s), (cx - s * 0.8, cy + s * 0.6), (cx - s, cy - s // 2)],
              fill=(255, 255, 255))
    mark = "!" if level != "verde" else "✓"
    d.text((cx, cy + 10), mark, font=font(180, True), fill=c, anchor="mm")
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
        img, m = imagegen.generate(prompt, seed=seed + k)
        score = embeddings.image_text_score(img, prompt)
        tries.append({"seed": seed + k, "siglip_score": round(score, 4)})
        if best is None or score > best[1]:
            best = (img, score)
        if score >= QUALITY_THRESHOLD:
            break
    img = best[0].resize((W, W), Image.LANCZOS)
    top = (W - 560) // 2
    hero = img.crop((0, top, W, top + 560))
    return hero, {"model": config.HF_MODELS["sdxl"]["id"], "ms": (time.perf_counter() - t0) * 1000, "prompt": prompt,
                  "intentos": tries, "siglip_score": round(best[1], 4)}


def compose(level: str, title: str, signals: list[str], advice: list[str], hero: Image.Image) -> Image.Image:
    c = COLORS[level]
    card = Image.new("RGB", (W, H), (250, 248, 245))
    card.paste(hero, (0, 120))
    d = ImageDraw.Draw(card)
    d.rectangle((0, 0, W, 120), fill=c)
    d.text((48, 60), BANNERS[level], font=font(54, True), fill="white", anchor="lm")
    d.text((W - 48, 60), config.BRAND_NAME, font=font(30, True), fill="white", anchor="rm")
    shade_h = 280
    shade = Image.new("RGBA", (W, shade_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for y in range(shade_h):
        sd.line([(0, y), (W, y)], fill=(10, 12, 20, int(225 * min(1.0, 1.4 * y / shade_h))))
    card.paste(shade, (0, 680 - shade_h), shade)
    title_lines = wrap(title, font(46, True), W - 96)[:2]
    for i, line in enumerate(title_lines):
        d.text((48, 600 + i * 56 - 56 * (len(title_lines) - 1)), line, font=font(46, True), fill="white", anchor="lm")
    y = 712
    d.text((48, y), "Lo que hemos detectado" if level != "verde" else "Lo que hemos comprobado", font=font(34, True), fill=c)
    y += 58
    for s in signals[:3]:
        d.ellipse((52, y + 10, 72, y + 30), fill=c)
        for j, line in enumerate(wrap(s, font(32), W - 160)[:2]):
            d.text((96, y + j * 40), line, font=font(32), fill=(35, 35, 40))
        y += 40 * min(2, len(wrap(s, font(32), W - 160))) + 18
    y += 14
    d.text((48, y), "Qué hacer ahora", font=font(34, True), fill=c)
    y += 58
    for i, a in enumerate(advice[:3], 1):
        d.rounded_rectangle((48, y, 92, y + 44), radius=10, fill=c)
        d.text((70, y + 22), str(i), font=font(28, True), fill="white", anchor="mm")
        for j, line in enumerate(wrap(a, font(31), W - 170)[:2]):
            d.text((112, y + 4 + j * 40), line, font=font(31), fill=(35, 35, 40))
        y += 40 * min(2, len(wrap(a, font(31), W - 170))) + 22
    d.rectangle((0, H - 70, W, H), fill=(35, 38, 48))
    d.text((48, H - 35), config.AI_WATERMARK, font=font(22), fill=(200, 200, 210), anchor="lm")
    d.text((W - 48, H - 35), "Tu banco nunca te pedirá claves", font=font(22, True), fill="white", anchor="rm")
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
