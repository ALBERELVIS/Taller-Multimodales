"""Base de campañas de fraude conocidas y búsqueda multimodal sobre ella.

Cada campaña tiene un texto de ejemplo y una captura. Indexamos:
* texto  -> e5 (texto-texto)
* imagen -> SigLIP2 (imagen-imagen)
* descripción -> SigLIP2 texto (búsqueda cruzada imagen-texto)
"""

from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from diputado import config

CAMPAIGNS_JSON = config.CAMPAIGNS_DIR / "campaigns.json"
INDEX_PATH = config.CAMPAIGNS_DIR / "index.npz"
IMAGES_DIR = config.CAMPAIGNS_DIR / "img"


@lru_cache(maxsize=1)
def load() -> list[dict]:
    return json.loads(CAMPAIGNS_JSON.read_text(encoding="utf-8"))


def image_path(cid: str):
    return IMAGES_DIR / f"{cid}.png"


def build_index() -> None:
    from diputado.ai import embeddings
    from diputado.media import render

    items = load()
    for c in items:
        if not image_path(c["id"]).exists():
            render.save(render.render_campaign(c), image_path(c["id"]))
    text = embeddings.embed_text([f"{c['nombre']}. {c['texto']}" for c in items])
    img = embeddings.embed_images([image_path(c["id"]) for c in items])
    desc = embeddings.embed_image_texts([c["descripcion"] for c in items])
    np.savez_compressed(INDEX_PATH, ids=np.array([c["id"] for c in items]), text=text, image=img, desc=desc)
    _index.cache_clear()


@lru_cache(maxsize=1)
def _index():
    if not INDEX_PATH.exists():
        build_index()
    z = np.load(INDEX_PATH)
    return {k: z[k] for k in z.files}


RANGES_PATH = config.ARTIFACTS_DIR / "campaign_ranges.json"
DEFAULT_RANGES = {"texto": (0.78, 0.93), "imagen": (0.55, 0.95), "imagen_texto": (0.0, 0.15)}


@lru_cache(maxsize=1)
def _ranges() -> dict[str, tuple[float, float]]:
    if RANGES_PATH.exists():
        saved = json.loads(RANGES_PATH.read_text(encoding="utf-8"))
        return {k: tuple(saved.get(k, v)) for k, v in DEFAULT_RANGES.items()}
    return DEFAULT_RANGES


def search(text_emb: np.ndarray | None = None, image_emb: np.ndarray | None = None, k: int = 3) -> list[dict]:
    """Devuelve las k campañas más parecidas combinando las similitudes disponibles."""
    idx = _index()
    by_id = {c["id"]: c for c in load()}
    parts = {}
    if text_emb is not None:
        parts["texto"] = idx["text"] @ text_emb
    if image_emb is not None:
        parts["imagen"] = idx["image"] @ image_emb
        parts["imagen_texto"] = idx["desc"] @ image_emb
    if not parts:
        return []
    # e5 da similitudes altas incluso entre textos no relacionados (~0.75); reescalamos
    # cada canal a [0, 1] con rangos medidos en el notebook 04 para poder combinarlos.
    ranges = _ranges()
    scaled = {name: np.clip((s - ranges[name][0]) / (ranges[name][1] - ranges[name][0]), 0, 1) for name, s in parts.items()}
    combined = np.max(np.stack(list(scaled.values())), axis=0)
    order = np.argsort(-combined)[:k]
    out = []
    for i in order:
        c = by_id[str(idx["ids"][i])]
        out.append({
            "id": c["id"],
            "nombre": c["nombre"],
            "canal": c["canal"],
            "descripcion": c["descripcion"],
            "similitud": float(combined[i]),
            "detalle": {name: float(parts[name][i]) for name in parts},
            "imagen": str(image_path(c["id"])),
        })
    return out
