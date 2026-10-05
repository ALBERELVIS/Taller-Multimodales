"""Estructuras que cruzan ingesta, análisis e interfaz."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CaseInput:
    company: str = "Compañía"
    ticker: str = "TICKER"
    pdf_path: Path | None = None
    chart_path: Path | None = None
    audio_path: Path | None = None
    news_path: Path | None = None
    prices_path: Path | None = None
    live_prices: bool = False
    synthetic: bool = False


@dataclass
class StageLog:
    name: str
    model: str
    seconds: float
    status: str
    detail: str
    cached: bool = False

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass
class StepResult:
    value: object = None
    detail: str = "ok"
    status: str = "ok"
    cached: bool = False
    model: str | None = None


@dataclass
class Evidence:
    id: str
    modality: str
    title: str
    text: str
    locator: str
    page: int | None = None
    start_sec: float | None = None


@dataclass
class TextChunk:
    evidence_id: str
    modality: str
    title: str
    text: str
    locator: str
    vector: list[float] | None = None


@dataclass
class ImageDoc:
    evidence_id: str
    path: str
    title: str
    caption: str
    vector: list[float] | None = None


@dataclass
class FactSheet:
    company: str
    ticker: str
    synthetic: bool
    metrics: dict[str, float]
    metric_sources: dict[str, str]
    risk_text: str
    guidance_text: str
    chart_caption: str
    price_stats: dict[str, float]
    stance: str
    numbers_origin: str


@dataclass
class RejectedSentence:
    text: str
    numbers: list[str]


@dataclass
class FilterOutcome:
    text: str
    rejected: list[RejectedSentence]
    support_ratio: float


@dataclass
class Hit:
    title: str
    text: str
    locator: str
    modality: str
    score: float
    mode: str


@dataclass
class Answer:
    text: str
    hits: list[Hit]
    image_caption: str | None
    mode: str
    rejected: list[RejectedSentence]
    support_ratio: float


@dataclass
class AnalysisResult:
    fact_sheet: FactSheet
    thesis_raw: str
    thesis: str
    thesis_mode: str
    rejected: list[RejectedSentence]
    raw_support_ratio: float
    published_support_ratio: float
    evidences: list[Evidence]
    stages: list[StageLog]
    chunks: list[TextChunk]
    images: list[ImageDoc]
    infographic_path: str | None
    audio_path: str | None
    audio_engine: str
    briefing_script: str
    disclaimer: str
    allowed_numbers: list[float] = field(default_factory=list)
