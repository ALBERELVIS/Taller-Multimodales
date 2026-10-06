"""Embeddings de texto (multilingual-e5) e imagen-texto (SigLIP2 y CLIP), en CPU."""

from __future__ import annotations

import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from diputado import config
from diputado.ai.gpu import SMALL_DEVICE

_lock = threading.Lock()


def _normalize(x: torch.Tensor) -> np.ndarray:
    return torch.nn.functional.normalize(x.float(), dim=-1).cpu().numpy()


@lru_cache(maxsize=1)
def _e5():
    from transformers import AutoModel, AutoTokenizer

    mid = config.HF_MODELS["text_emb"]["id"]
    tok = AutoTokenizer.from_pretrained(mid)
    model = AutoModel.from_pretrained(mid).to(SMALL_DEVICE).eval()
    return tok, model


@torch.inference_mode()
def embed_text(texts: list[str] | str, prefix: str = "query: ", batch_size: int = 32) -> np.ndarray:
    """Embeddings e5 normalizados (dimensión 384). e5 exige el prefijo `query: `."""
    if isinstance(texts, str):
        texts = [texts]
    with _lock:
        tok, model = _e5()
        out = []
        for i in range(0, len(texts), batch_size):
            batch = [prefix + (t or "") for t in texts[i : i + batch_size]]
            enc = tok(batch, padding=True, truncation=True, max_length=512, return_tensors="pt").to(SMALL_DEVICE)
            hidden = model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-6)
            out.append(_normalize(pooled))
    return np.concatenate(out, axis=0)


@lru_cache(maxsize=2)
def _vision_text(kind: str):
    from transformers import AutoModel, AutoProcessor

    mid = config.HF_MODELS[kind]["id"]
    proc = AutoProcessor.from_pretrained(mid)
    model = AutoModel.from_pretrained(mid).to(SMALL_DEVICE).eval()
    return proc, model


def _load_images(images: list) -> list[Image.Image]:
    return [Image.open(i).convert("RGB") if isinstance(i, (str, Path)) else i.convert("RGB") for i in images]


@torch.inference_mode()
def embed_images(images: list, kind: str = "siglip") -> np.ndarray:
    with _lock:
        proc, model = _vision_text(kind)
        inputs = proc(images=_load_images(images), return_tensors="pt").to(SMALL_DEVICE)
        feats = model.get_image_features(**inputs)
    return _normalize(feats)


@torch.inference_mode()
def embed_image_texts(texts: list[str], kind: str = "siglip") -> np.ndarray:
    with _lock:
        proc, model = _vision_text(kind)
        if kind == "siglip":
            inputs = proc(text=texts, padding="max_length", max_length=64, truncation=True, return_tensors="pt")
        else:
            inputs = proc(text=texts, padding=True, truncation=True, return_tensors="pt")
        feats = model.get_text_features(**inputs.to(SMALL_DEVICE))
    return _normalize(feats)


def image_text_score(image, text: str, kind: str = "siglip") -> float:
    """Similitud coseno imagen-texto; la usamos como control de calidad automático (IQA)."""
    return float(embed_images([image], kind)[0] @ embed_image_texts([text], kind)[0])
