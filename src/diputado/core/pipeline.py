"""Orquestador multimodal de DiputadoDetector.

Elegimos un grafo determinista (y no un agente autónomo) para la decisión de riesgo:
en un contexto regulado necesitamos que cada análisis siga siempre los mismos pasos,
sea reproducible y deje una traza auditable. Reservamos el agente para la exploración
de datos del analista, donde la flexibilidad aporta más que la predictibilidad.

    audio  -> Whisper -> transcripción ─┐
           -> CLAP -> VozSinteticaNet   │
    imagen -> Qwen2.5-VL -> texto ──────┼─> extractores ─> e5 -> TacticNet ─┐
           -> SigLIP2 -> campañas ──────┘                ─> campañas ───────┼─> fusión -> semáforo
    texto  ─────────────────────────────────────────────> Qwen3 ────────────┘
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterator
from datetime import datetime

from diputado import config
from diputado.core import campaigns, cases_db, extractors, fusion
from diputado.core.schemas import AnalysisResult, CaseInput

HEADLINES = {
    "rojo": "Cuidado: esto tiene todas las señales de una estafa.",
    "ambar": "Atención: hay señales sospechosas. Compruébalo antes de hacer nada.",
    "verde": "Parece legítimo, aunque conviene mantener la precaución.",
}
ADVICE = {
    "rojo": ["No pulses enlaces, no pagues y no des ningún código.", "Cuelga o bloquea el número.",
             "Llama a tu banco al número que aparece en tu tarjeta."],
    "ambar": ["No respondas todavía.", "Comprueba la información por un canal oficial.",
              "Si dudas, consulta a un familiar o a tu banco."],
    "verde": ["No parece necesario hacer nada.", "Recuerda: tu banco nunca te pedirá claves.",
              "Ante cualquier duda, vuelve a preguntarnos."],
}
VERDICT_TO_LEVEL = {"estafa": "rojo", "sospechoso": "ambar", "legitimo": "verde"}
CHANNEL_NAMES = {"sms": "sms", "whatsapp": "whatsapp", "email": "email", "carta": "carta", "web": "web",
                 "red_social": "web", "otro": "imagen"}


def _safe(result: AnalysisResult, etapa: str, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        result.errors.append(f"{etapa}: {type(exc).__name__}: {exc}")
        result.add_step(etapa, {"model": "error", "ms": 0}, str(exc)[:160])
        return None


def _highlights(text: str, phrases: list[str]) -> list[tuple[str, str | None]]:
    spans = []
    low = text.lower()
    for ph in phrases:
        ph = ph.strip(" «»\"'.")
        if len(ph) < 4:
            continue
        i = low.find(ph.lower())
        if i >= 0:
            spans.append((i, i + len(ph), "frase sospechosa"))
    for name, pat in extractors.PATTERNS.items():
        for m in re.finditer(pat, low):
            spans.append((m.start(), m.end(), extractors.HUMAN_FLAGS[name]))
    for m in extractors.URL_RE.finditer(text):
        if "." in m.group(0):
            spans.append((m.start(), m.end(), "enlace"))
    spans.sort()
    out, pos = [], 0
    for s, e, lab in spans:
        if s < pos:
            continue
        if s > pos:
            out.append((text[pos:s], None))
        out.append((text[s:e], lab))
        pos = e
    if pos < len(text):
        out.append((text[pos:], None))
    return out


def analyze(case: CaseInput) -> Iterator[AnalysisResult]:
    """Ejecuta el análisis y va cediendo resultados parciales para la interfaz."""
    from diputado.ai import embeddings, keras_heads

    r = AnalysisResult(modalidades=case.modalities())
    r.canal = case.channel_hint or ("llamada" if case.audio else "imagen" if case.image else "texto")
    texts: list[str] = []
    audio_emb = image_emb = None

    # 1) Audio: transcripción + análisis acústico
    if case.audio:
        from diputado.ai import asr, audio_clap

        r.stage = "Escuchando la llamada (Whisper)"
        yield r
        tr = _safe(r, "Transcripción", asr.transcribe, case.audio)
        if tr:
            r.transcript, m = tr
            r.add_step("Transcripción", m, f"{r.transcript['duration_s']} s de audio")
            texts.append(r.transcript["text"])
        r.stage = "Analizando la voz (CLAP + VozSinteticaNet)"
        yield r
        t0 = time.perf_counter()
        audio = _safe(r, "Audio CLAP", audio_clap.load, case.audio)
        if audio is not None:
            audio_emb = _safe(r, "Audio CLAP", audio_clap.embed_audio, audio)
        if audio_emb is not None:
            r.acoustic = audio_clap.zero_shot(audio_emb)
            r.add_step("Contexto acústico", {"model": config.HF_MODELS["clap"]["id"], "ms": (time.perf_counter() - t0) * 1000},
                       next(iter(r.acoustic)))
            t0 = time.perf_counter()
            r.voice = keras_heads.predict_voice(audio_emb)
            if r.voice:
                r.add_step("Voz sintética", {"model": r.voice["model"], "ms": (time.perf_counter() - t0) * 1000},
                           f"p = {r.voice['synthetic_prob']:.2f}")
        yield r

    # 2) Imagen: lectura visual + embedding para campañas
    if case.image:
        from diputado.ai import vision

        r.stage = "Leyendo la imagen (Qwen2.5-VL)"
        yield r
        vr = _safe(r, "Lectura visual", vision.read_image, case.image)
        if vr:
            r.vision, m = vr
            r.add_step("Lectura visual", m, f"{r.vision['tipo_documento']} de «{r.vision['remitente'][:40]}»")
            if not case.channel_hint:
                r.canal = CHANNEL_NAMES.get(r.vision["tipo_documento"], "imagen")
            header = f"Remitente: {r.vision['remitente']}\n" if r.vision["remitente"] else ""
            texts.append(header + r.vision["texto_completo"])
        t0 = time.perf_counter()
        emb = _safe(r, "Embedding imagen", embeddings.embed_images, [case.image])
        if emb is not None:
            image_emb = emb[0]
            r.add_step("Embedding visual", {"model": config.HF_MODELS["siglip"]["id"], "ms": (time.perf_counter() - t0) * 1000})
        yield r

    if case.text:
        texts.append(case.text)
    r.evidence_text = "\n\n".join(t for t in texts if t and t.strip())

    # 3) Extractores, TacticNet y campañas
    r.stage = "Buscando señales de fraude (reglas, TacticNet y campañas)"
    yield r
    t0 = time.perf_counter()
    links = (r.vision or {}).get("enlaces", [])
    phones = (r.vision or {}).get("telefonos", [])
    r.extract = extractors.extract(r.evidence_text, links, phones)
    r.add_step("Reglas deterministas", {"model": "regex + rapidfuzz", "ms": (time.perf_counter() - t0) * 1000},
               f"{len(r.extract['flags_humanos'])} banderas rojas")
    text_emb = None
    if r.evidence_text:
        t0 = time.perf_counter()
        text_emb = _safe(r, "Embedding texto", embeddings.embed_text, r.evidence_text[:3000])
        if text_emb is not None:
            text_emb = text_emb[0]
            r.add_step("Embedding texto", {"model": config.HF_MODELS["text_emb"]["id"], "ms": (time.perf_counter() - t0) * 1000})
            t0 = time.perf_counter()
            r.tactic_model = keras_heads.predict_tactics(text_emb)
            if r.tactic_model:
                r.add_step("TacticNet", {"model": r.tactic_model["model"], "ms": (time.perf_counter() - t0) * 1000},
                           f"p(estafa) = {r.tactic_model['scam_prob']:.2f}")
    t0 = time.perf_counter()
    r.campaigns = _safe(r, "Campañas", campaigns.search, text_emb, image_emb) or []
    if r.campaigns:
        r.add_step("Campañas conocidas", {"model": "e5 + SigLIP2", "ms": (time.perf_counter() - t0) * 1000},
                   f"{r.campaigns[0]['nombre']} ({r.campaigns[0]['similitud']:.2f})")
    yield r

    # 4) Razonamiento con el LLM
    if r.evidence_text:
        from diputado.ai import llm

        r.stage = "Razonando como un analista antifraude (Qwen3)"
        yield r
        extra = {
            "Remitente": (r.vision or {}).get("remitente"),
            "Enlaces detectados": ", ".join(d["domain"] for d in r.extract["dominios"]),
            "Detalles visuales": "; ".join((r.vision or {}).get("senales_visuales", [])),
        }
        lr = _safe(r, "Razonamiento", llm.analyze, r.canal, r.evidence_text, extra)
        if lr:
            r.llm, m = lr
            r.add_step("Razonamiento", m, f"{r.llm['veredicto']} (p = {r.llm['probabilidad_estafa']:.2f})")

    # 5) Fusión y decisión
    _decide(r)
    r.stage = "Decisión tomada"
    r.done = True
    _store(r)
    yield r


def _decide(r: AnalysisResult) -> None:
    t0 = time.perf_counter()
    synth = r.voice["synthetic_prob"] if r.voice else None
    robotic = None
    if r.acoustic:
        robotic = r.acoustic.get("Voz robótica o sintética", 0) + r.acoustic.get("Menú automático (IVR)", 0)
    signals = {
        "tacticnet": r.tactic_model["scam_prob"] if r.tactic_model else None,
        "llm": r.llm["probabilidad_estafa"] if r.llm else None,
        "campana": fusion.campaign_to_prob(r.campaigns[0]["similitud"]) if r.campaigns else None,
        "reglas": fusion.rules_to_prob(r.extract["red_flag_score"]) if r.extract else None,
        "voz": synth,
        "acustica": robotic,
    }
    if not r.evidence_text:
        signals.update(tacticnet=None, llm=None, campana=None, reglas=None)
    fr = fusion.fuse(signals, hard_rule=bool(r.extract and r.extract["hard_rule"]))
    r.risk, r.level, r.contributions, r.signal_inputs, r.hard_rule = fr.risk, fr.level, fr.contributions, fr.inputs, fr.hard_rule
    r.add_step("Fusión de riesgo", {"model": "log-odds pooling", "ms": (time.perf_counter() - t0) * 1000},
               f"riesgo {fr.risk:.2f} → {fr.level}")

    tactics: dict[str, float] = {}
    if r.tactic_model:
        tactics.update(r.tactic_model["tactics"])
    for t in (r.llm or {}).get("tacticas", []):
        tactics[t] = max(tactics.get(t, 0.0), 0.8)
    r.tactics = dict(sorted(tactics.items(), key=lambda kv: -kv[1]))

    r.headline = HEADLINES[r.level]
    llm_level = VERDICT_TO_LEVEL.get((r.llm or {}).get("veredicto", ""), None)
    if r.llm and llm_level == r.level and r.llm.get("explicacion"):
        r.explanation = r.llm["explicacion"]
        r.advice = r.llm.get("consejos") or ADVICE[r.level]
    else:
        top = [config.TACTIC_LABELS[t].lower() for t, p in r.tactics.items() if p >= 0.5][:3]
        flags = (r.extract or {}).get("flags_humanos", [])[:2]
        if r.level == "verde":
            r.explanation = "No hemos encontrado peticiones de dinero, claves ni enlaces sospechosos."
        else:
            detail = ", ".join(top) if top else ", ".join(f.lower() for f in flags) or "varias señales de riesgo"
            r.explanation = f"Hemos detectado: {detail}. Así funcionan las estafas más habituales."
        r.advice = ADVICE[r.level]
    r.entity = (r.llm or {}).get("entidad_suplantada", "") or (r.campaigns[0]["nombre"] if r.campaigns and r.level != "verde" else "")
    r.highlights = _highlights(r.evidence_text, (r.llm or {}).get("frases_clave", []))


def _store(r: AnalysisResult) -> None:
    ex = r.extract or {}
    dom = next((d["domain"] for d in ex.get("dominios", []) if not d["official"]), None)
    amount = None
    if ex.get("importes"):
        m = re.search(r"\d+(?:[.,]\d+)*", ex["importes"][0])
        if m:
            try:
                amount = float(m.group(0).replace(".", "").replace(",", "."))
            except ValueError:
                amount = None
    phone = extractors.mask_pii(ex["telefonos"][0]) if ex.get("telefonos") else None
    try:
        r.case_id = cases_db.insert_case({
            "fecha": datetime.now().replace(microsecond=0).isoformat(sep=" "),
            "canal": r.canal,
            "nivel": r.level,
            "riesgo": round(float(r.risk), 3),
            "campana": r.campaigns[0]["id"] if r.campaigns and r.campaigns[0]["similitud"] >= 0.5 and r.level != "verde" else None,
            "entidad_suplantada": r.entity or None,
            "tacticas": ",".join(t for t, p in r.tactics.items() if p >= 0.5),
            "dominio": dom,
            "telefono": phone,
            "importe_eur": amount,
            "provincia": None,
            "edad_cliente": None,
            "resumen": extractors.mask_pii(r.evidence_text[:240]),
            "latencia_ms": round(r.total_ms(), 1),
            "origen": "app",
        })
    except Exception as exc:
        r.errors.append(f"Guardar caso: {exc}")


def narration(r: AnalysisResult) -> str:
    tips = " ".join(a.rstrip(".") + "." for a in r.advice[:2])
    return f"{r.headline} {r.explanation} {tips}"


def infographic_title(r: AnalysisResult) -> str:
    if r.level == "verde":
        return "Este mensaje parece legítimo"
    if r.campaigns and r.campaigns[0]["similitud"] >= 0.45:
        return r.campaigns[0]["nombre"]
    return f"Posible estafa: {r.entity}" if r.entity else "Posible estafa"


def outputs(r: AnalysisResult, video: bool = True) -> Iterator[tuple[str, AnalysisResult]]:
    """Genera las salidas multimedia en orden de utilidad: voz, infografía y vídeo."""
    from diputado.ai import tts
    from diputado.media import infographic, video as video_mod

    yield "Preparando el aviso de voz", r
    text = narration(r)
    res = _safe(r, "Aviso de voz", tts.speak, text)
    if res:
        r.audio_out, m = res
        r.add_step("Aviso de voz", m, f"{m['audio_s']:.1f} s de audio")
    yield "Dibujando la infografía (SDXL-Turbo)", r
    signals = [config.TACTIC_LABELS[t] for t, p in r.tactics.items() if p >= 0.5][:3]
    signals = signals or (r.extract or {}).get("flags_humanos", [])[:3]
    if r.level == "verde":
        signals = ["No pide dinero, claves ni códigos", "No contiene enlaces sospechosos", "No mete prisa ni amenaza"]
    res = _safe(r, "Infografía", infographic.make, r.level, infographic_title(r), signals, r.advice, r.tactics)
    if res:
        r.infographic, r.infographic_meta = res
        r.add_step("Infografía", r.infographic_meta, f"SigLIP2 = {r.infographic_meta.get('siglip_score', '-')}")
    if video and r.infographic and r.audio_out:
        yield "Montando el vídeo-alerta", r
        res = _safe(r, "Vídeo", video_mod.make, r.infographic, r.audio_out, text)
        if res:
            r.video, m = res
            r.add_step("Vídeo-alerta", m, f"{m['duracion_s']} s")
    yield "", r


def run(case: CaseInput) -> AnalysisResult:
    """Versión síncrona (para notebooks y tests): devuelve el resultado final."""
    last = None
    for last in analyze(case):
        pass
    return last
