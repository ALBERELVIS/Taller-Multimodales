"""CLIP pequeño para cruzar una pregunta de texto con el gráfico."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from helios.config import Settings
from helios.models.errors import ModelUnavailable

_MODEL = None
_PREPROCESS = None
_TOKENIZER = None
_KEY = ""


def embed_image(path: Path, settings: Settings) -> np.ndarray:
    from PIL import Image

    model, preprocess, _tokenizer = _load(settings)
    image = preprocess(Image.open(path).convert("RGB")).unsqueeze(0)
    vector = _encode_image(model, image)
    return vector[0]


def embed_texts(texts: list[str], settings: Settings) -> np.ndarray:
    model, _preprocess, tokenizer = _load(settings)
    tokens = tokenizer(texts)
    return _encode_text(model, tokens)


def _load(settings: Settings):
    global _MODEL, _PREPROCESS, _TOKENIZER, _KEY
    key = f"{settings.clip_model}|{settings.clip_pretrained}"
    if _MODEL is not None and _KEY == key:
        return _MODEL, _PREPROCESS, _TOKENIZER
    try:
        import open_clip
    except ImportError as exc:
        raise ModelUnavailable("open-clip-torch no está instalado.") from exc
    model, _, preprocess = open_clip.create_model_and_transforms(
        settings.clip_model,
        pretrained=settings.clip_pretrained,
    )
    model.eval()
    _MODEL = model
    _PREPROCESS = preprocess
    _TOKENIZER = open_clip.get_tokenizer(settings.clip_model)
    _KEY = key
    return _MODEL, _PREPROCESS, _TOKENIZER


def _encode_image(model, image) -> np.ndarray:
    import torch

    with torch.no_grad():
        features = model.encode_image(image)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().numpy().astype(np.float32)


def _encode_text(model, tokens) -> np.ndarray:
    import torch

    with torch.no_grad():
        features = model.encode_text(tokens)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().numpy().astype(np.float32)
