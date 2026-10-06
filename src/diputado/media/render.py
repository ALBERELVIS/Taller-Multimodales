"""Renderizado de capturas de móvil sintéticas (SMS, WhatsApp, correo, llamada y web).

Las usamos para la base de campañas conocidas, los casos de demo y las pruebas de
la lectura visual. Todas las marcas son genéricas o ficticias: no usamos logotipos reales.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from diputado.media.fonts import font, wrap

W, H = 720, 1440


def _status_bar(d: ImageDraw.ImageDraw, color=(20, 20, 20), hour: str = "10:42") -> None:
    d.text((36, 22), hour, font=font(26, True), fill=color)
    d.text((W - 150, 22), "4G  87%", font=font(24), fill=color)


def _bubble(d, x, y, text, max_w, fill, fg=(20, 20, 20), radius=26, size=30):
    f = font(size)
    lines = wrap(text, f, max_w - 48)
    line_h = int(size * 1.35)
    h = line_h * len(lines) + 40
    w = min(max_w, max(int(f.getlength(l)) for l in lines) + 48)
    d.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill)
    for i, line in enumerate(lines):
        d.text((x + 24, y + 20 + i * line_h), line, font=f, fill=fg)
    return y + h


def render_sms(sender: str, text: str, hour: str = "10:42", previous: list[str] | None = None) -> Image.Image:
    img = Image.new("RGB", (W, H), (250, 250, 252))
    d = ImageDraw.Draw(img)
    _status_bar(d, hour=hour)
    d.rectangle((0, 70, W, 210), fill=(242, 242, 247))
    d.ellipse((W // 2 - 40, 82, W // 2 + 40, 162), fill=(160, 166, 178))
    d.text((W // 2, 122), sender[:1].upper(), font=font(40, True), fill="white", anchor="mm")
    d.text((W // 2, 186), sender, font=font(28, True), fill=(20, 20, 20), anchor="mm")
    y = 260
    d.text((W // 2, y), "Mensaje de texto · Hoy " + hour, font=font(22), fill=(130, 130, 140), anchor="mm")
    y += 40
    for prev in previous or []:
        y = _bubble(d, 30, y, prev, 560, (229, 229, 234)) + 24
    _bubble(d, 30, y, text, 580, (229, 229, 234))
    d.rounded_rectangle((30, H - 110, W - 30, H - 40), radius=34, outline=(200, 200, 205), width=3)
    d.text((70, H - 75), "Mensaje de texto", font=font(26), fill=(160, 160, 165), anchor="lm")
    return img


def render_whatsapp(sender: str, text: str, hour: str = "21:17", unknown: bool = True) -> Image.Image:
    img = Image.new("RGB", (W, H), (236, 229, 221))
    d = ImageDraw.Draw(img)
    rnd = random.Random(sender)
    for _ in range(140):
        x, y = rnd.randint(0, W), rnd.randint(200, H)
        d.ellipse((x, y, x + 6, y + 6), fill=(226, 218, 208))
    d.rectangle((0, 0, W, 190), fill=(7, 94, 84))
    _status_bar(d, color="white", hour=hour)
    d.ellipse((90, 92, 170, 172), fill=(200, 210, 215))
    d.text((190, 108), sender, font=font(30, True), fill="white")
    d.text((190, 146), "en línea", font=font(22), fill=(210, 235, 230))
    d.text((40, 132), "<", font=font(40, True), fill="white", anchor="mm")
    y = 220
    if unknown:
        d.rounded_rectangle((60, y, W - 60, y + 120), radius=16, fill=(255, 245, 196))
        d.text((W // 2, y + 38), "Este número no está en tus contactos", font=font(23, True), fill=(90, 80, 40), anchor="mm")
        d.text((W // 2, y + 82), "Bloquear   ·   Añadir", font=font(23), fill=(7, 94, 84), anchor="mm")
        y += 160
    y = _bubble(d, 30, y, text, 600, "white", radius=18)
    d.text((540, y - 34), hour, font=font(19), fill=(130, 130, 130))
    d.rounded_rectangle((20, H - 100, W - 110, H - 30), radius=34, fill="white")
    d.text((60, H - 65), "Mensaje", font=font(26), fill=(160, 160, 160), anchor="lm")
    d.ellipse((W - 95, H - 100, W - 25, H - 30), fill=(0, 168, 132))
    return img


def render_email(sender: str, subject: str, text: str, hour: str = "08:03") -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    _status_bar(d, hour=hour)
    d.text((36, 100), "< Recibidos", font=font(28), fill=(10, 110, 230))
    y = 170
    for line in wrap(subject, font(36, True), W - 72):
        d.text((36, y), line, font=font(36, True), fill=(20, 20, 20))
        y += 48
    y += 20
    d.ellipse((36, y, 106, y + 70), fill=(220, 90, 70))
    d.text((71, y + 35), sender[:1].upper(), font=font(32, True), fill="white", anchor="mm")
    name = sender.split("<")[0].strip()
    addr = sender[sender.find("<") :] if "<" in sender else ""
    d.text((126, y + 4), name, font=font(27, True), fill=(20, 20, 20))
    d.text((126, y + 40), addr, font=font(21), fill=(110, 110, 120))
    y += 120
    for line in wrap(text, font(29), W - 72):
        d.text((36, y), line, font=font(29), fill=(40, 40, 40))
        y += 42
    y += 30
    d.rounded_rectangle((W // 2 - 190, y, W // 2 + 190, y + 80), radius=14, fill=(10, 110, 230))
    d.text((W // 2, y + 40), "ACCEDER AHORA", font=font(28, True), fill="white", anchor="mm")
    return img


def render_call(caller: str, transcript: str, hour: str = "11:05") -> Image.Image:
    img = Image.new("RGB", (W, H), (28, 32, 44))
    d = ImageDraw.Draw(img)
    _status_bar(d, color="white", hour=hour)
    d.text((W // 2, 220), "Llamada entrante", font=font(28), fill=(190, 195, 210), anchor="mm")
    d.text((W // 2, 290), caller.replace("Llamada entrante: ", ""), font=font(44, True), fill="white", anchor="mm")
    d.ellipse((W // 2 - 90, 370, W // 2 + 90, 550), fill=(70, 80, 100))
    d.rounded_rectangle((40, 640, W - 40, 1150), radius=24, fill=(45, 50, 66))
    d.text((70, 670), "Transcripción en directo", font=font(24, True), fill=(140, 200, 255))
    y = 720
    for line in wrap(f"«{transcript}»", font(28), W - 140)[:12]:
        d.text((70, y), line, font=font(28), fill=(235, 235, 240))
        y += 38
    d.ellipse((120, 1220, 260, 1360), fill=(230, 60, 60))
    d.ellipse((W - 260, 1220, W - 120, 1360), fill=(50, 190, 90))
    return img


def render_web(title: str, text: str) -> Image.Image:
    img = Image.new("RGB", (W, H), (246, 247, 249))
    d = ImageDraw.Draw(img)
    _status_bar(d)
    d.rounded_rectangle((24, 80, W - 24, 140), radius=30, fill=(232, 234, 238))
    d.text((60, 110), "noticias-economia-hoy.live", font=font(24), fill=(90, 90, 100), anchor="lm")
    d.rectangle((0, 170, W, 230), fill=(200, 30, 45))
    d.text((W // 2, 200), "EXCLUSIVA · Anuncio patrocinado", font=font(26, True), fill="white", anchor="mm")
    y = 270
    for line in wrap(title, font(40, True), W - 72):
        d.text((36, y), line, font=font(40, True), fill=(20, 20, 20))
        y += 52
    y += 20
    rnd = random.Random(title)
    chart = Image.new("RGB", (W - 72, 300), (255, 255, 255))
    cd = ImageDraw.Draw(chart)
    pts, v = [], 260
    for i in range(0, W - 72, 24):
        v = max(30, v - rnd.randint(-6, 22))
        pts.append((i, v))
    cd.line(pts, fill=(30, 170, 90), width=6)
    img.paste(chart, (36, y))
    y += 330
    for line in wrap(text, font(29), W - 72):
        d.text((36, y), line, font=font(29), fill=(40, 40, 40))
        y += 42
    y += 30
    d.rounded_rectangle((36, y, W - 36, y + 90), radius=14, fill=(30, 170, 90))
    d.text((W // 2, y + 45), "EMPIEZA A GANAR HOY", font=font(30, True), fill="white", anchor="mm")
    return img


def render_letter(header: str, text: str) -> Image.Image:
    img = Image.new("RGB", (1000, 1300), (252, 250, 244))
    d = ImageDraw.Draw(img)
    d.rectangle((60, 60, 940, 150), outline=(60, 60, 60), width=3)
    d.text((500, 105), header, font=font(34, True), fill=(30, 30, 30), anchor="mm")
    y = 220
    for line in wrap(text, font(30), 860):
        d.text((70, y), line, font=font(30), fill=(30, 30, 30))
        y += 46
    return img.rotate(1.2, expand=True, fillcolor=(90, 90, 90)).filter(ImageFilter.GaussianBlur(0.6))


def render_campaign(c: dict) -> Image.Image:
    canal = c["canal"]
    if canal == "sms":
        return render_sms(c["remitente"], c["texto"])
    if canal == "whatsapp":
        return render_whatsapp(c["remitente"], c["texto"])
    if canal == "email":
        return render_email(c["remitente"], c["nombre"], c["texto"])
    if canal == "llamada":
        return render_call(c["remitente"], c["texto"])
    return render_web(c["nombre"], c["texto"])


def save(img: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    return path
