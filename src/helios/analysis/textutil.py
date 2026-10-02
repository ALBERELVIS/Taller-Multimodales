"""Tokenización, solapamiento léxico y tasa de error de palabras."""

from __future__ import annotations

import re
import unicodedata

_TOKEN = re.compile(r"[^\w]+", flags=re.UNICODE)
STOPWORDS = {
    "el", "la", "los", "las", "de", "del", "un", "una", "y", "o", "u", "en", "que", "qué",
    "es", "por", "para", "con", "al", "se", "su", "sus", "como", "más", "mas", "si", "no",
    "lo", "le", "les", "este", "esta", "esto", "esa", "ese", "son", "fue", "ser", "ha",
    "han", "the", "a", "of", "and", "cual", "cuál", "donde", "dónde", "cuando", "cuándo",
}


def fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def tokenize(text: str, drop_stops: bool = False) -> list[str]:
    raw = [token for token in _TOKEN.split(fold(text)) if token]
    if not drop_stops:
        return raw
    return [token for token in raw if token not in STOPWORDS and not token.isdigit()]


def lexical_score(query: str, text: str) -> float:
    query_tokens = set(tokenize(query, drop_stops=True))
    text_tokens = set(tokenize(text, drop_stops=True))
    if not query_tokens or not text_tokens:
        return 0.0
    return len(query_tokens & text_tokens) / len(query_tokens)


def split_sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate sobre tokens en minúsculas, sin puntuación."""
    ref = tokenize(reference)
    hyp = tokenize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)


def keyword_hit_rate(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    folded = fold(text)
    hits = sum(1 for keyword in keywords if fold(keyword) in folded)
    return hits / len(keywords)


def _levenshtein(left: list[str], right: list[str]) -> int:
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, token in enumerate(left, start=1):
        current = [i]
        for j, other in enumerate(right, start=1):
            cost = 0 if token == other else 1
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1]
