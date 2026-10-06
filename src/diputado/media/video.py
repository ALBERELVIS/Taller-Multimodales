"""Vídeo-alerta para compartir con la familia: infografía + narración + subtítulos."""

from __future__ import annotations

import re
import time
import uuid
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from diputado import config
from diputado.media.fonts import font, wrap

VW, VH = 720, 900
PAN = 1.06
FPS = 12


def _caption(text: str) -> np.ndarray:
    img = Image.new("RGBA", (VW, 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lines = wrap(text, font(30, True), VW - 80)[:3]
    h = 44 * len(lines) + 28
    d.rounded_rectangle((24, 170 - h - 12, VW - 24, 158), radius=18, fill=(15, 15, 20, 238))
    for i, line in enumerate(lines):
        d.text((VW // 2, 170 - h + 6 + i * 44), line, font=font(30, True), fill="white", anchor="ma")
    return np.array(img)


def make(infographic: str, narration_wav: str, narration_text: str, out_dir: Path | None = None) -> tuple[str, dict]:
    config.ensure_ffmpeg_on_path()
    from moviepy import AudioFileClip, VideoClip

    import soundfile as sf

    t0 = time.perf_counter()
    out_dir = out_dir or config.OUTPUTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    # moviepy lee un bloque más allá del final del audio: lo acolchamos con silencio y
    # cortamos el vídeo un poco antes del final del fichero.
    wav, sr = sf.read(narration_wav, dtype="float32")
    speech_s = len(wav) / sr
    padded = out_dir / f"_narracion_{uuid.uuid4().hex[:8]}.wav"
    sf.write(padded, np.concatenate([np.zeros(int(0.3 * sr), "float32"), wav, np.zeros(int(1.2 * sr), "float32")]), sr)
    audio = AudioFileClip(str(padded))
    duration = speech_s + 1.3
    # Paneo vertical lento en lugar de zoom y subtítulos mezclados a mano solo en su franja:
    # CompositeVideoClip y el reescalado por fotograma cuestan >100 ms por fotograma.
    tall = np.array(Image.open(infographic).convert("RGB").resize((VW, int(VH * PAN)), Image.LANCZOS))
    travel = tall.shape[0] - VH

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", narration_text) if s.strip()]
    total_chars = sum(len(s) for s in sentences) or 1
    captions, start = [], 0.3
    for s in sentences:
        dur = speech_s * len(s) / total_chars
        cap = _caption(s).astype(np.float32)
        captions.append((start, start + dur, cap[:, :, :3], cap[:, :, 3:] / 255.0))
        start += dur
    y0 = VH - 190

    def frame(t: float) -> np.ndarray:
        f = tall[int(travel * min(t / duration, 1.0)):][:VH].copy()
        for s0, s1, rgb, alpha in captions:
            if s0 <= t < s1:
                strip = f[y0 : y0 + rgb.shape[0]].astype(np.float32)
                f[y0 : y0 + rgb.shape[0]] = (strip * (1 - alpha) + rgb * alpha).astype(np.uint8)
                break
        return f

    video = VideoClip(frame, duration=duration).with_audio(audio.subclipped(0, duration))
    path = out_dir / f"video_alerta_{uuid.uuid4().hex[:8]}.mp4"
    video.write_videofile(str(path), fps=FPS, codec="libx264", audio_codec="aac", preset="ultrafast",
                          threads=8, logger=None, ffmpeg_params=["-pix_fmt", "yuv420p"], temp_audiofile_path=str(out_dir))
    audio.close()
    video.close()
    padded.unlink(missing_ok=True)
    return str(path), {"model": "moviepy + ffmpeg", "ms": (time.perf_counter() - t0) * 1000, "duracion_s": round(duration, 1)}
