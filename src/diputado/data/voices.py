"""Dataset de voz real frente a voz sintética para VozSinteticaNet.

* Real: Multilingual LibriSpeech en español (lectura humana, locutores distintos
  en el split de entrenamiento `1_hours` y en el de evaluación `dev`).
* Sintética: Bark (Suno) y MMS-TTS (Meta), dos generadores con arquitecturas muy
  distintas, para poder evaluar dejando fuera un generador completo.
Todo pasa por el mismo canal telefónico simulado antes de extraer embeddings CLAP.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

from diputado import config
from diputado.ai.audio_io import resample

AUDIO_DIR = config.SYNTHETIC_DIR / "audio_cache"
SR = 16_000


def real_clips(split: str = "1_hours", n: int = 200, seed: int = 0, max_s: float = 12.0) -> pd.DataFrame:
    from huggingface_hub import hf_hub_download

    path = hf_hub_download("facebook/multilingual_librispeech", f"spanish/{split}-00000-of-00001.parquet", repo_type="dataset")
    df = pd.read_parquet(path, columns=["audio", "speaker_id", "transcript"]).sample(frac=1, random_state=seed)
    out_dir = AUDIO_DIR / f"real_{split}"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, r in enumerate(df.itertuples()):
        if len(rows) >= n:
            break
        audio, sr = sf.read(io.BytesIO(r.audio["bytes"]), dtype="float32")
        audio = resample(audio, sr, SR)[: int(max_s * SR)]
        p = out_dir / f"{split}_{i:04d}.wav"
        sf.write(p, audio, SR)
        rows.append({"path": str(p), "label": 0, "generador": "humano", "locutor": str(r.speaker_id), "split_origen": split, "texto": r.transcript})
    return pd.DataFrame(rows)


def mms_clips(texts: list[str]) -> pd.DataFrame:
    from diputado.ai import tts

    out_dir = AUDIO_DIR / "mms"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, t in enumerate(texts):
        p = out_dir / f"mms_{i:04d}.wav"
        if not p.exists():
            rate = 0.85 + 0.3 * ((i * 37) % 10) / 10
            audio, sr = tts.synthesize_mms(t, speaking_rate=rate, seed=i)
            sf.write(p, resample(audio, sr, SR), SR)
        rows.append({"path": str(p), "label": 1, "generador": "mms", "locutor": "mms", "split_origen": "sintetico", "texto": t})
    return pd.DataFrame(rows)


def bark_clips(texts: list[str], log=print) -> pd.DataFrame:
    from diputado.ai import bark

    out_dir = AUDIO_DIR / "bark"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, t in enumerate(texts):
        p = out_dir / f"bark_{i:04d}.wav"
        voice = bark.SPANISH_VOICES[i % len(bark.SPANISH_VOICES)]
        if not p.exists():
            audio, sr = bark.synthesize(t, voice=voice, seed=i)
            sf.write(p, resample(audio, sr, SR), SR)
            if i % 10 == 0:
                log(f"  bark {i}/{len(texts)}")
        rows.append({"path": str(p), "label": 1, "generador": "bark", "locutor": voice, "split_origen": "sintetico", "texto": t})
    return pd.DataFrame(rows)


def load_wav(path: str | Path) -> np.ndarray:
    audio, sr = sf.read(path, dtype="float32")
    return resample(audio, sr, SR)


MANIFEST = config.SYNTHETIC_DIR / "voz_manifest.csv"
EMBEDDINGS = config.SYNTHETIC_DIR / "voz_clap.npz"


def synthetic_texts(n: int, seed: int = 0) -> list[str]:
    """Frases para los generadores: mitad transcripciones de MLS (mismo contenido que la voz real)
    y mitad mensajes del dataset sintético (contenido de estafa), para que el tema no sea un atajo."""
    from huggingface_hub import hf_hub_download

    rng = np.random.default_rng(seed)
    path = hf_hub_download("facebook/multilingual_librispeech", "spanish/dev-00000-of-00001.parquet", repo_type="dataset")
    mls = pd.read_parquet(path, columns=["transcript"])["transcript"].tolist()
    msgs = []
    csv = config.SYNTHETIC_DIR / "textos_sinteticos.csv"
    if csv.exists():
        msgs = pd.read_csv(csv)["texto"].tolist()
    pool = [t for t in rng.permutation(mls)[: n] if 40 < len(t) < 200]
    pool += [t for t in rng.permutation(msgs)[: n] if 40 < len(t) < 200] if msgs else []
    # Bark degrada y se ralentiza con textos largos: frases de ~120 caracteres (5-8 s de voz).
    pool = [str(t)[:120].rsplit(" ", 1)[0] for t in rng.permutation(pool)]
    return pool[:n]


MAX_S = 8.0


def build_dataset(n_real_train: int = 160, n_real_test: int = 120, n_mms: int = 160, n_bark: int = 80, log=print) -> pd.DataFrame:
    """Construye (o reutiliza) los clips y el manifiesto del dataset de voz.

    Todos los clips se recortan a MAX_S segundos para que la duración no sea un atajo."""
    if MANIFEST.exists():
        return pd.read_csv(MANIFEST)
    log("Voz real (MLS español)…")
    real_tr = real_clips("1_hours", n_real_train, seed=0, max_s=MAX_S)
    real_te = real_clips("dev", n_real_test, seed=1, max_s=MAX_S)
    texts = synthetic_texts(max(n_mms, n_bark), seed=2)
    log(f"MMS-TTS ({n_mms} clips)…")
    mms = mms_clips(texts[:n_mms])
    log(f"Bark ({n_bark} clips)…")
    bark = bark_clips(texts[:n_bark], log=log)
    df = pd.concat([real_tr, real_te, mms, bark], ignore_index=True)
    df["duracion_s"] = [round(sf.info(p).duration, 2) for p in df["path"]]
    df = df[df["duracion_s"] >= 1.0].reset_index(drop=True)
    df["path"] = [str(Path(p).relative_to(config.ROOT)) for p in df["path"]]
    df.to_csv(MANIFEST, index=False)
    return df


def build_embeddings(df: pd.DataFrame, seed: int = 0, log=print) -> dict[str, np.ndarray]:
    """Embeddings CLAP de cada clip en dos versiones: audio original y tras el canal telefónico."""
    if EMBEDDINGS.exists():
        return dict(np.load(EMBEDDINGS))
    from diputado.ai import audio_clap
    from diputado.data.telephony import phone_channel

    rng = np.random.default_rng(seed)
    clean, phone = [], []
    for i, p in enumerate(df["path"]):
        a16 = load_wav(config.ROOT / p)[: int(MAX_S * SR)]
        clean.append(audio_clap.embed_audio(resample(a16, SR, audio_clap.SR)))
        tel = phone_channel(a16, SR, rng, out_sr=SR)
        phone.append(audio_clap.embed_audio(resample(tel, SR, audio_clap.SR)))
        if i % 100 == 0:
            log(f"  CLAP {i}/{len(df)}")
    out = {"limpio": np.stack(clean).astype(np.float32), "telefono": np.stack(phone).astype(np.float32)}
    np.savez_compressed(EMBEDDINGS, **out)
    return out
