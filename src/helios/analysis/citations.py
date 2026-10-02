"""Control de cifras: una frase con un número no respaldado no se publica."""

from __future__ import annotations

from helios.analysis.numbers import extract_numbers, is_supported, strip_citations, support_ratio
from helios.analysis.textutil import split_sentences
from helios.types import FilterOutcome, RejectedSentence


def filter_unsupported_sentences(text: str, allowed: list[float]) -> FilterOutcome:
    kept: list[str] = []
    rejected: list[RejectedSentence] = []
    for sentence in split_sentences(text):
        numbers = extract_numbers(strip_citations(sentence))
        bad = [ _show(number) for number in numbers if not is_supported(number, allowed) ]
        if bad:
            rejected.append(RejectedSentence(text=sentence, numbers=bad))
        else:
            kept.append(sentence)
    published = " ".join(kept).strip()
    return FilterOutcome(
        text=published,
        rejected=rejected,
        support_ratio=support_ratio(published, allowed),
    )


def _show(number: float) -> str:
    if abs(number - round(number)) < 1e-6:
        return str(int(round(number)))
    return f"{number:.4g}"
