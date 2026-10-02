"""Embeddings de texto. Se cargan solo cuando hace falta el índice vectorial."""

from __future__ import annotations

import numpy as np

from helios.config import Settings
from helios.models.errors import ModelUnavailable

_MODEL = None
_NAME = ""


def embed_texts(texts: list[str], settings: Settings) -> np.ndarray:
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    model = _load(settings)
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vectors, dtype=np.float32)


def _load(settings: Settings):
    global _MODEL, _NAME
    if _MODEL is not None and _NAME == settings.embed_model:
        return _MODEL
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ModelUnavailable("sentence-transformers no está instalado.") from exc
    _MODEL = SentenceTransformer(settings.embed_model)
    _NAME = settings.embed_model
    return _MODEL
