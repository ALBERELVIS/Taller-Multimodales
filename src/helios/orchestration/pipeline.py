"""Orquesta las modalidades. Las cifras las calcula el código; los modelos redactan."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from helios.analysis.citations import filter_unsupported_sentences
from helios.analysis.numbers import collect_allowed, support_ratio
from helios.analysis.stance import decide_stance
from helios.analysis.thesis import coded_market_caption, render_briefing, render_template
from helios.cache import digest, remember
from helios.compliance.disclaimer import DISCLAIMER
from helios.config import Settings
from helios.ingest.chart import load_chart
from helios.ingest.fields import extract_document
from helios.ingest.market import MarketSnapshot, load_prices
from helios.ingest.news import NewsItem, load_news
from helios.ingest.pdf import PdfDocument, read_pdf
from helios.models.whisper_asr import Transcript
from helios.types import (
    AnalysisResult,
    CaseInput,
    Evidence,
    FactSheet,
    ImageDoc,
    StageLog,
    StepResult,
    TextChunk,
)

SCAN_MIN_CHARS = 80
MIN_THESIS_CHARS = 280

OnStage = Callable[[StageLog], None]


class Recorder:
    def __init__(self, on_stage: OnStage | None):
        self.logs: list[StageLog] = []
        self.on_stage = on_stage

    def run(self, name: str, model: str, fn) -> object:
        started = time.perf_counter()
        try:
            out = fn()
        except Exception as exc:
            self._push(StageLog(name, model, _elapsed(started), "error", f"{type(exc).__name__}: {exc}"))
            return None
        if isinstance(out, StepResult):
            self._push(
                StageLog(
                    name,
                    out.model or model,
                    _elapsed(started),
                    out.status,
                    out.detail,
                    out.cached,
                )
            )
            return out.value
        self._push(StageLog(name, model, _elapsed(started), "ok", "ok"))
        return out

    def _push(self, log: StageLog) -> None:
        self.logs.append(log)
        if self.on_stage is not None:
            self.on_stage(log)


def run_analysis(
    case: CaseInput,
    settings: Settings | None = None,
    on_stage: OnStage | None = None,
    use_cache: bool = True,
    use_models: bool = True,
) -> AnalysisResult:
    settings = settings or Settings.from_env()
    if not use_cache:
        settings = replace(settings, cache_enabled=False)
    if not _has_material(case):
        raise ValueError("Carga un PDF, un gráfico, un audio, noticias o una serie de precios.")

    recorder = Recorder(on_stage)
    out_dir = settings.root / "data" / "output" / _safe_ticker(case.ticker)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf = recorder.run("Lectura del PDF", "pymupdf", lambda: _read_pdf_step(case))
    pdf_doc = pdf if isinstance(pdf, PdfDocument) else None
    vision_pdf = recorder.run(
        "Visión del documento",
        settings.vision_model,
        lambda: _vision_step(
            pdf_doc.images if pdf_doc else [],
            (
                "Lee este informe financiero en español. No inventes cifras. "
                "Si una cifra se lee con claridad, cópiala tal cual y di en qué apartado está."
            ),
            settings,
            use_models,
        ),
    )
    market = recorder.run("Serie de precios y riesgo", "cálculo local", lambda: _market_step(case))
    snapshot = market if isinstance(market, MarketSnapshot) else None
    chart = recorder.run("Ficha del gráfico", "PIL", lambda: _chart_step(case))
    vision_chart = recorder.run(
        "Visión del gráfico",
        settings.vision_model,
        lambda: _vision_step(
            [_read_bytes(case.chart_path)] if case.chart_path and case.chart_path.exists() else [],
            (
                "Describe en español la tendencia de este gráfico de velas. "
                "No estimes precios ni porcentajes exactos. Di si hay caída, recuperación o lateral."
            ),
            settings,
            use_models,
        ),
    )
    heard = recorder.run("Transcripción", settings.whisper_model, lambda: _asr_step(case, settings, use_models))
    transcript = heard if isinstance(heard, Transcript) else None
    news = recorder.run("Noticias", "lectura local", lambda: _news_step(case))
    news_items = news if isinstance(news, list) else []

    built = _assemble(
        case,
        pdf_doc,
        vision_pdf if isinstance(vision_pdf, str) else "",
        snapshot,
        chart,
        vision_chart if isinstance(vision_chart, str) else "",
        transcript,
        news_items,
    )
    chunks: list[TextChunk] = built["chunks"]
    images: list[ImageDoc] = built["images"]
    facts: FactSheet = built["facts"]
    evidences: list[Evidence] = built["evidences"]
    allowed: list[float] = built["allowed"]
    template: str = built["template"]

    recorder.run("Índice multimodal", settings.embed_model, lambda: _index_step(chunks, images, settings, use_models))
    drafted = recorder.run("Tesis", settings.text_model, lambda: _thesis_step(facts, evidences, template, settings, use_models))
    draft = drafted if isinstance(drafted, dict) else {"text": template, "mode": "plantilla"}
    controlled = recorder.run(
        "Control de cifras",
        "reglas",
        lambda: _control_step(str(draft.get("text", "")), str(draft.get("mode", "plantilla")), template, allowed),
    )
    control = controlled if isinstance(controlled, dict) else {"text": template, "mode": "plantilla", "rejected": [], "raw_ratio": 1.0, "published_ratio": 1.0}
    picture = recorder.run(
        "Infografía",
        "PIL",
        lambda: _infographic_step(facts, built["modalities"], snapshot.closes if snapshot else [], out_dir / "infografia.png"),
    )
    voice = recorder.run("Briefing de voz", settings.tts_voice, lambda: _voice_step(facts, out_dir, settings))
    voice_info = voice if isinstance(voice, dict) else {"script": render_briefing(facts), "path": None, "engine": "off"}

    return AnalysisResult(
        fact_sheet=facts,
        thesis_raw=str(draft.get("text", "")),
        thesis=str(control.get("text", "")),
        thesis_mode=str(control.get("mode", "plantilla")),
        rejected=list(control.get("rejected", [])),
        raw_support_ratio=float(control.get("raw_ratio", 1.0)),
        published_support_ratio=float(control.get("published_ratio", 1.0)),
        evidences=evidences,
        stages=recorder.logs,
        chunks=chunks,
        images=images,
        infographic_path=picture if isinstance(picture, str) else None,
        audio_path=voice_info.get("path"),
        audio_engine=str(voice_info.get("engine", "")),
        briefing_script=str(voice_info.get("script", "")),
        disclaimer=DISCLAIMER,
        allowed_numbers=allowed,
    )


def _has_material(case: CaseInput) -> bool:
    paths = [case.pdf_path, case.chart_path, case.audio_path, case.news_path, case.prices_path]
    return any(path is not None for path in paths) or case.live_prices


def _safe_ticker(ticker: str) -> str:
    cleaned = re.sub(r"[^\w.-]+", "_", ticker.strip()) or "caso"
    return cleaned[:40]


def _elapsed(started: float) -> float:
    return round(time.perf_counter() - started, 3)


def _read_pdf_step(case: CaseInput) -> StepResult:
    if case.pdf_path is None or not case.pdf_path.exists():
        return StepResult(None, "sin PDF", status="omitido")
    document = read_pdf(case.pdf_path)
    return StepResult(document, f"{len(document.pages)} páginas, {len(document.fields)} campos")


def _market_step(case: CaseInput) -> StepResult:
    ticker = case.ticker if case.live_prices else None
    path = None if case.live_prices else case.prices_path
    if path is None and not ticker:
        if case.prices_path and case.prices_path.exists():
            path = case.prices_path
        else:
            return StepResult(None, "sin serie", status="omitido")
    snapshot = load_prices(path, ticker)
    if snapshot is None:
        return StepResult(None, "sin serie", status="omitido")
    drawdown = snapshot.stats.get("max_drawdown", 0.0)
    return StepResult(snapshot, f"{snapshot.source}; drawdown {drawdown:.1%}")


def _chart_step(case: CaseInput) -> StepResult:
    if case.chart_path is None or not case.chart_path.exists():
        return StepResult(None, "sin imagen", status="omitido")
    chart = load_chart(case.chart_path)
    return StepResult(chart, f"{chart.width}×{chart.height}")


def _news_step(case: CaseInput) -> StepResult:
    if case.news_path is None or not case.news_path.exists():
        return StepResult([], "sin prensa", status="omitido")
    items = load_news(case.news_path)
    return StepResult(items, f"{len(items)} piezas")


def _asr_step(case: CaseInput, settings: Settings, use_models: bool) -> StepResult:
    if case.audio_path is None or not case.audio_path.exists():
        return StepResult(None, "sin audio", status="omitido")
    if not use_models:
        return StepResult(None, "modelos desactivados", status="omitido")
    from helios.models.errors import ModelUnavailable
    from helios.models.whisper_asr import transcribe

    try:
        transcript, cached = transcribe(case.audio_path, settings)
    except ModelUnavailable as exc:
        return StepResult(None, str(exc), status="omitido")
    detail = transcript.language or "transcrito"
    return StepResult(transcript, detail, cached=cached, model=settings.whisper_model)


def _vision_step(images: list[bytes], prompt: str, settings: Settings, use_models: bool) -> StepResult:
    blobs = [blob for blob in images if blob]
    if not blobs:
        return StepResult(None, "sin imagen", status="omitido")
    if not use_models:
        return StepResult(None, "modelos desactivados", status="omitido")
    from helios.models.ollama_client import OllamaClient

    client = OllamaClient(settings)
    if not client.healthy():
        return StepResult(None, f"Ollama no responde en {settings.ollama_host}", status="omitido")
    model = client.resolve(settings.vision_model, settings.vision_fallbacks)
    if not model:
        return StepResult(None, "no hay un modelo de visión instalado", status="omitido")
    key = digest(model.encode("utf-8"), prompt.encode("utf-8"), *blobs)

    def produce() -> dict:
        text = client.chat(model, prompt, images=blobs, timeout=300)
        return {"text": text}

    try:
        payload, cached = remember("vision", key, settings, produce)
    except Exception as exc:
        return StepResult(None, str(exc), status="error", model=model)
    note = "modelo principal" if _same_model(model, settings.vision_model) else f"alternativa; faltaba {settings.vision_model}"
    return StepResult(str(payload.get("text", "")).strip(), note, cached=cached, model=model)


def _same_model(installed: str, wanted: str) -> bool:
    return installed == wanted or installed.split(":")[0] == wanted.split(":")[0] and installed.endswith(wanted.split(":")[-1])


def _read_bytes(path: Path | None) -> bytes:
    if path is None or not path.exists():
        return b""
    return path.read_bytes()


def _assemble(case, pdf, vision_pdf, snapshot, chart, vision_chart, transcript, news_items) -> dict:
    fields: dict[str, float] = {}
    risk_text = ""
    guidance_text = ""
    field_pages: dict[str, int] = {}
    pdf_corpus = ""
    numbers_origin = "text"
    company = case.company
    ticker = case.ticker
    if isinstance(pdf, PdfDocument):
        fields = dict(pdf.fields)
        risk_text = pdf.risk_text
        guidance_text = pdf.guidance_text
        field_pages = dict(pdf.field_pages)
        pdf_corpus = pdf.text
        if pdf.company:
            company = pdf.company
        if pdf.ticker:
            ticker = pdf.ticker
        if len(pdf.text.strip()) < SCAN_MIN_CHARS and vision_pdf:
            extracted = extract_document(vision_pdf)
            extracted_fields = extracted["fields"]
            if isinstance(extracted_fields, dict) and extracted_fields:
                fields = {key: float(value) for key, value in extracted_fields.items()}
                risk_text = str(extracted["risk_text"] or risk_text)
                guidance_text = str(extracted["guidance_text"] or guidance_text)
                pdf_corpus = vision_pdf
                numbers_origin = "vision"
    price_stats = dict(snapshot.stats) if isinstance(snapshot, MarketSnapshot) else {}
    news_title = news_items[0].title if news_items else None
    audio_locator = _audio_locator(transcript)
    chart_caption = vision_chart.strip() if isinstance(vision_chart, str) else ""
    synthetic = case.synthetic or "sintet" in pdf_corpus.lower()
    facts = FactSheet(
        company=company or "Compañía",
        ticker=ticker or case.ticker or "TICKER",
        synthetic=synthetic,
        metrics=fields,
        metric_sources={key: _source_label(field_pages, key, numbers_origin) for key in list(fields) + ["risk"]},
        risk_text=risk_text,
        guidance_text=guidance_text,
        chart_caption=chart_caption,
        price_stats=price_stats,
        stance=decide_stance(fields, price_stats, risk_text),
        numbers_origin=numbers_origin,
    )
    if "risk" not in facts.metric_sources:
        facts.metric_sources["risk"] = "Visión del PDF" if numbers_origin == "vision" else "PDF"
    corpus = [pdf_corpus, guidance_text, risk_text]
    corpus.extend(item.body for item in news_items)
    corpus.append(coded_market_caption(price_stats))
    allowed = collect_allowed(fields, price_stats, corpus)
    chunks = _build_chunks(pdf, vision_pdf, transcript, news_items, price_stats, chart_caption)
    images = _build_images(case, chart, chart_caption or coded_market_caption(price_stats))
    evidences = _build_evidences(pdf, vision_pdf, transcript, news_items, chart_caption, price_stats, snapshot)
    modalities = _modalities(pdf, chart, transcript, news_items, snapshot)
    template = render_template(facts, news_title=news_title, audio_locator=audio_locator)
    return {
        "facts": facts,
        "chunks": chunks,
        "images": images,
        "evidences": evidences,
        "allowed": allowed,
        "template": template,
        "modalities": modalities,
    }


def _source_label(field_pages: dict[str, int], key: str, origin: str) -> str:
    if origin == "vision":
        return "Visión del PDF"
    page = field_pages.get(key)
    return f"PDF p.{page}" if page else "PDF"


def _audio_locator(transcript: Transcript | None) -> str | None:
    if transcript is None or not (transcript.text or transcript.segments):
        return None
    for segment in transcript.segments:
        text = str(segment.get("text", "")).lower()
        if any(token in text for token in ("cabo", "permiso", "riesgo", "retraso")):
            return f"Audio {_mmss(float(segment.get('start', 0)))}"
    if transcript.segments:
        return f"Audio {_mmss(float(transcript.segments[0].get('start', 0)))}"
    return "Audio"


def _mmss(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def _build_chunks(pdf, vision_pdf, transcript, news_items, price_stats, chart_caption) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    if isinstance(pdf, PdfDocument):
        for index, page in enumerate(pdf.pages, start=1):
            for part, text in enumerate(_pack(page), start=1):
                chunks.append(TextChunk(f"pdf-{index}-{part}", "pdf", f"PDF página {index}", text, f"PDF p.{index}"))
    if vision_pdf:
        chunks.append(TextChunk("pdf-vision", "pdf_vision", "Lectura visual del PDF", vision_pdf, "Visión del PDF"))
    if isinstance(transcript, Transcript) and transcript.text:
        if transcript.segments:
            for index, segment in enumerate(transcript.segments, start=1):
                text = str(segment.get("text", "")).strip()
                if not text:
                    continue
                start = float(segment.get("start", 0))
                chunks.append(
                    TextChunk(
                        f"audio-{index}",
                        "audio",
                        "Conferencia de resultados",
                        text,
                        f"Audio {_mmss(start)}",
                    )
                )
        else:
            chunks.append(TextChunk("audio-1", "audio", "Conferencia de resultados", transcript.text, "Audio"))
    for item in news_items:
        chunks.append(
            TextChunk(item.id, "news", item.title, f"{item.title}. {item.body}", f"Noticia: {item.title}")
        )
    market_text = coded_market_caption(price_stats)
    if market_text:
        chunks.append(TextChunk("market", "market", "Serie de precios", market_text, "Serie de precios"))
    if chart_caption:
        chunks.append(TextChunk("chart-vision", "chart", "Lectura del gráfico", chart_caption, "Gráfico"))
    return chunks


def _pack(page: str, limit: int = 550) -> list[str]:
    lines = [line.strip() for line in page.splitlines() if line.strip()]
    packed: list[str] = []
    buffer = ""
    for line in lines:
        if buffer and len(buffer) + len(line) > limit:
            packed.append(buffer)
            buffer = line
        else:
            buffer = f"{buffer}\n{line}".strip()
    if buffer:
        packed.append(buffer)
    return packed


def _build_images(case: CaseInput, chart, caption: str) -> list[ImageDoc]:
    if chart is None or case.chart_path is None:
        return []
    return [
        ImageDoc(
            evidence_id="chart",
            path=str(case.chart_path),
            title="Gráfico de velas",
            caption=caption,
        )
    ]


def _build_evidences(pdf, vision_pdf, transcript, news_items, chart_caption, price_stats, snapshot) -> list[Evidence]:
    evidences: list[Evidence] = []
    if isinstance(pdf, PdfDocument) and pdf.text.strip():
        evidences.append(Evidence("pdf", "pdf", "Capa de texto del PDF", pdf.text.strip()[:1800], "PDF"))
    if vision_pdf:
        evidences.append(Evidence("pdf-vision", "pdf_vision", "Visión del documento", vision_pdf, "Visión del PDF"))
    if isinstance(transcript, Transcript) and transcript.text:
        evidences.append(Evidence("audio", "audio", "Transcripción", transcript.text, _audio_locator(transcript) or "Audio"))
    for item in news_items:
        evidences.append(Evidence(item.id, "news", item.title, item.body, f"Noticia: {item.title}"))
    if chart_caption:
        evidences.append(Evidence("chart", "chart", "Gráfico", chart_caption, "Gráfico"))
    if price_stats:
        source = snapshot.source if snapshot is not None else "Serie de precios"
        evidences.append(Evidence("market", "market", "Riesgo de mercado", coded_market_caption(price_stats), source))
    return evidences


def _modalities(pdf, chart, transcript, news_items, snapshot) -> list[str]:
    labels: list[str] = []
    if isinstance(pdf, PdfDocument):
        labels.append("PDF")
    if chart is not None:
        labels.append("Gráfico")
    if isinstance(transcript, Transcript):
        labels.append("Audio")
    if news_items:
        labels.append("Prensa")
    if snapshot is not None:
        labels.append("Precios")
    return labels


def _index_step(chunks: list[TextChunk], images: list[ImageDoc], settings: Settings, use_models: bool) -> StepResult:
    if not chunks and not images:
        return StepResult(None, "sin fragmentos", status="omitido", model="léxico")
    if not use_models:
        return StepResult(None, "búsqueda léxica", model="léxico")
    detail = "léxico"
    model_name = "léxico"
    try:
        from helios.models.embeddings import embed_texts

        vectors = embed_texts([chunk.text for chunk in chunks], settings)
        for chunk, vector in zip(chunks, vectors):
            chunk.vector = vector.tolist()
        detail = "texto"
        model_name = settings.embed_model
    except Exception as exc:
        return StepResult(None, f"búsqueda léxica ({exc})", model="léxico")
    if images:
        try:
            from helios.models.clip_encoder import embed_image

            for image in images:
                image.vector = embed_image(Path(image.path), settings).tolist()
            detail += " + CLIP"
        except Exception as exc:
            detail += f"; CLIP omitido ({exc})"
    return StepResult(None, detail, model=model_name)


def _thesis_step(facts: FactSheet, evidences: list[Evidence], template: str, settings: Settings, use_models: bool) -> StepResult:
    if not use_models:
        return StepResult({"text": template, "mode": "plantilla"}, "plantilla de control", model="reglas")
    from helios.models.ollama_client import OllamaClient

    client = OllamaClient(settings)
    if not client.healthy():
        return StepResult({"text": template, "mode": "plantilla"}, "plantilla; Ollama no responde", model="reglas")
    model = client.resolve(settings.text_model, settings.text_fallbacks)
    if not model:
        return StepResult({"text": template, "mode": "plantilla"}, "plantilla; sin modelo de texto", model="reglas")
    try:
        raw = client.chat(model, _thesis_prompt(facts, evidences), system=_THESIS_SYSTEM, json_mode=True, timeout=240)
        prose = _assemble_model_thesis(raw, facts)
    except Exception as exc:
        return StepResult({"text": template, "mode": "plantilla"}, f"plantilla; {exc}", model="reglas")
    note = "modelo principal" if _same_model(model, settings.text_model) else f"alternativa; faltaba {settings.text_model}"
    return StepResult({"text": prose, "mode": "modelo"}, note, model=model)


_THESIS_SYSTEM = (
    "Eres el redactor de Helios, una mesa de análisis para gestores independientes. "
    "Escribes en español, con frases cortas. Solo usas cifras presentes en la ficha. "
    "Citas así: [PDF p.1], [Audio 00:12], [Noticia: titulo], [Serie de precios], [Gráfico]. "
    "No das asesoramiento de inversión. Respondes únicamente en JSON."
)


def _thesis_prompt(facts: FactSheet, evidences: list[Evidence]) -> str:
    ficha = {
        "company": facts.company,
        "ticker": facts.ticker,
        "stance": facts.stance,
        "metrics": facts.metrics,
        "sources": facts.metric_sources,
        "guidance": facts.guidance_text,
        "risk": facts.risk_text,
        "price_stats": facts.price_stats,
    }
    excerpts = "\n".join(f"- {item.locator}: {item.text[:500]}" for item in evidences[:8])
    return (
        "Redacta la nota de mesa en JSON con las claves narrativa, alcista y bajista. "
        "narrativa es un párrafo. alcista y bajista son listas de una frase.\n"
        f"Ficha autorizada:\n{json.dumps(ficha, ensure_ascii=False)}\n"
        f"Fragmentos:\n{excerpts}\n"
        "El sesgo de mesa ya está decidido: no lo cambies. No inventes cifras."
    )


def _assemble_model_thesis(raw: str, facts: FactSheet) -> str:
    payload = _loose_json(raw)
    if not isinstance(payload, dict):
        return raw.strip()
    narrative = str(payload.get("narrativa") or payload.get("texto") or "").strip()
    bull = payload.get("alcista") or []
    bear = payload.get("bajista") or []
    sentences = [f"{facts.company} ({facts.ticker}). Sesgo de mesa: {facts.stance}."]
    if narrative:
        sentences.append(narrative)
    if isinstance(bull, list):
        for item in bull:
            if str(item).strip():
                sentences.append(f"A favor: {str(item).strip()}")
    if isinstance(bear, list):
        for item in bear:
            if str(item).strip():
                sentences.append(f"En contra: {str(item).strip()}")
    sentences.append(DISCLAIMER)
    return " ".join(sentences)


def _loose_json(raw: str) -> dict | None:
    text = raw.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _control_step(raw: str, mode: str, template: str, allowed: list[float]) -> StepResult:
    filtered = filter_unsupported_sentences(raw, allowed)
    final = filtered.text
    used_mode = mode
    if len(final) < MIN_THESIS_CHARS:
        fallback = filter_unsupported_sentences(template, allowed)
        final = fallback.text or template
        used_mode = "plantilla"
    published = support_ratio(final, allowed)
    if published < 1:
        final = filter_unsupported_sentences(template, allowed).text or template
        used_mode = "plantilla"
        published = support_ratio(final, allowed)
    payload = {
        "text": final,
        "mode": used_mode,
        "rejected": filtered.rejected,
        "raw_ratio": support_ratio(raw, allowed),
        "published_ratio": published,
    }
    detail = f"publicadas {published:.0%}; frases retiradas {len(filtered.rejected)}; modo {used_mode}"
    return StepResult(payload, detail)


def _infographic_step(facts: FactSheet, modalities: list[str], closes: list[float], out_path: Path) -> StepResult:
    from helios.viz.infographic import render_infographic

    path = render_infographic(facts, out_path, closes=closes, modalities=modalities)
    return StepResult(str(path), path.name)


def _voice_step(facts: FactSheet, out_dir: Path, settings: Settings) -> StepResult:
    script = render_briefing(facts)
    if settings.tts_mode in {"off", "none", "0"}:
        return StepResult({"script": script, "path": None, "engine": "off"}, "voz desactivada", status="omitido", model="off")
    from helios.models.tts import synthesize

    try:
        path, engine = synthesize(script, out_dir / "briefing.mp3", settings)
    except Exception as exc:
        return StepResult({"script": script, "path": None, "engine": "error"}, str(exc), status="error", model="tts")
    return StepResult({"script": script, "path": str(path), "engine": engine}, engine, model=engine)
