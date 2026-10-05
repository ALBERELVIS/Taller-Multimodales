"""Puntuación del extractor frente a la verdad terreno del caso."""

from __future__ import annotations


def score_fields(predicted: dict[str, float], truth: dict[str, float]) -> dict[str, object]:
    matched: list[str] = []
    missing: list[str] = []
    mismatched: list[str] = []
    for key, expected in truth.items():
        if key not in predicted:
            missing.append(key)
            continue
        if _close(float(predicted[key]), float(expected)):
            matched.append(key)
        else:
            mismatched.append(key)
    extra = [key for key in predicted if key not in truth]
    true_positive = len(matched)
    recall = true_positive / len(truth) if truth else 1.0
    precision_den = true_positive + len(mismatched) + len(extra)
    precision = true_positive / precision_den if precision_den else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matched": matched,
        "missing": missing,
        "mismatched": mismatched,
        "extra": extra,
    }


def _close(predicted: float, expected: float) -> bool:
    return abs(predicted - expected) <= max(0.05, abs(expected) * 0.001)
