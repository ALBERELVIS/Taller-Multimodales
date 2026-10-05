"""Búsqueda híbrida. Si no hay vectores, el léxico sostiene la pregunta."""

from __future__ import annotations

import numpy as np

from helios.analysis.textutil import lexical_score
from helios.types import Hit, ImageDoc, TextChunk

IMAGE_KEYWORDS = ("grafico", "gráfica", "grafica", "gráfico", "vela", "velas", "tendencia", "chart", "imagen")


def rank_texts(
    chunks: list[TextChunk],
    question: str,
    query_vector: list[float] | None = None,
    k: int = 4,
) -> list[Hit]:
    if not chunks:
        return []
    lexical = np.array([lexical_score(question, chunk.text) for chunk in chunks], dtype=float)
    title = np.array(
        [lexical_score(question, f"{chunk.title} {chunk.locator}") for chunk in chunks],
        dtype=float,
    )
    mode = "lexico"
    scores = lexical
    if query_vector is not None and any(chunk.vector for chunk in chunks):
        query = np.asarray(query_vector, dtype=float)
        norm = np.linalg.norm(query) or 1.0
        query = query / norm
        matrix = []
        for chunk in chunks:
            if chunk.vector:
                vector = np.asarray(chunk.vector, dtype=float)
                vector = vector / (np.linalg.norm(vector) or 1.0)
            else:
                vector = np.zeros_like(query)
            matrix.append(vector)
        stacked = np.vstack(matrix)
        cosine = stacked @ query
        scores = 0.75 * cosine + 0.25 * lexical
        mode = "hibrido"
    scores = scores + 0.05 * title
    order = np.argsort(scores)[::-1]
    hits: list[Hit] = []
    for index in order[:k]:
        score = float(scores[index])
        if score <= 0 and mode == "lexico":
            continue
        chunk = chunks[int(index)]
        hits.append(
            Hit(
                title=chunk.title,
                text=chunk.text,
                locator=chunk.locator,
                modality=chunk.modality,
                score=score,
                mode=mode,
            )
        )
    return hits


def image_keyword_hit(question: str) -> bool:
    folded = question.lower()
    return any(keyword in folded for keyword in IMAGE_KEYWORDS)


def rank_images(
    images: list[ImageDoc],
    query_vector: list[float] | None,
    question: str,
    min_sim: float = 0.24,
) -> list[Hit]:
    if not images:
        return []
    if query_vector is None or all(image.vector is None for image in images):
        if image_keyword_hit(question):
            image = images[0]
            return [_image_hit(image, 1.0, "palabra")]
        return []
    query = np.asarray(query_vector, dtype=float)
    query = query / (np.linalg.norm(query) or 1.0)
    best: tuple[float, ImageDoc] | None = None
    for image in images:
        if not image.vector:
            continue
        vector = np.asarray(image.vector, dtype=float)
        vector = vector / (np.linalg.norm(vector) or 1.0)
        score = float(vector @ query)
        if best is None or score > best[0]:
            best = (score, image)
    if best is None:
        return []
    score, image = best
    if score >= min_sim or image_keyword_hit(question):
        return [_image_hit(image, score, "clip")]
    return []


def _image_hit(image: ImageDoc, score: float, mode: str) -> Hit:
    return Hit(
        title=image.title,
        text=image.caption,
        locator="Gráfico",
        modality="chart",
        score=score,
        mode=mode,
    )
