"""Estructuras de datos que viajan entre capas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CaseInput:
    text: str | None = None
    image: str | None = None
    audio: str | None = None
    channel_hint: str | None = None
    source: str = "app"

    def modalities(self) -> list[str]:
        return [m for m, v in (("texto", self.text), ("imagen", self.image), ("audio", self.audio)) if v]


@dataclass
class Step:
    etapa: str
    modelo: str
    ms: float
    detalle: str = ""


@dataclass
class AnalysisResult:
    case_id: int | None = None
    canal: str = "texto"
    modalidades: list[str] = field(default_factory=list)
    stage: str = "inicio"
    done: bool = False
    transcript: dict | None = None
    vision: dict | None = None
    acoustic: dict | None = None
    voice: dict | None = None
    evidence_text: str = ""
    extract: dict | None = None
    tactic_model: dict | None = None
    campaigns: list[dict] = field(default_factory=list)
    llm: dict | None = None
    risk: float | None = None
    level: str | None = None
    contributions: dict[str, float] = field(default_factory=dict)
    signal_inputs: dict[str, float] = field(default_factory=dict)
    hard_rule: bool = False
    tactics: dict[str, float] = field(default_factory=dict)
    headline: str = ""
    explanation: str = ""
    advice: list[str] = field(default_factory=list)
    entity: str = ""
    highlights: list[tuple[str, str | None]] = field(default_factory=list)
    timeline: list[Step] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    audio_out: str | None = None
    infographic: str | None = None
    infographic_meta: dict | None = None
    video: str | None = None

    def add_step(self, etapa: str, metrics: dict | None, detalle: str = "") -> None:
        metrics = metrics or {}
        self.timeline.append(Step(etapa, str(metrics.get("model", "-")), round(float(metrics.get("ms", 0)), 1), detalle))

    def total_ms(self) -> float:
        return sum(s.ms for s in self.timeline)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
