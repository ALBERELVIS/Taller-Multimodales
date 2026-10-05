"""Interfaz de Helios. No llama a modelos: solo al orquestador."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

from theme import CSS

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from helios.analysis.cost import estimate_cost
from helios.analysis.qa import answer_question
from helios.compliance.disclaimer import DISCLAIMER, SHORT_DISCLAIMER
from helios.config import Settings
from helios.demo.case import load_demo_case
from helios.doctor import readiness
from helios.orchestration.pipeline import run_analysis
from helios.types import AnalysisResult, CaseInput
from helios.viz.architecture import render_architecture

SUGGESTED = [
    "¿Cuál es el margen EBITDA?",
    "¿Qué pasa con Cabo Prior?",
    "¿Cuál es el drawdown de la serie?",
    "¿Cuál es la guía de ingresos?",
]


def main() -> None:
    st.set_page_config(page_title="Helios", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    page = _sidebar()
    if page == "Mesa":
        _mesa()
    elif page == "Preguntar":
        _preguntar()
    elif page == "Briefing":
        _briefing()
    else:
        _arquitectura()


def _sidebar() -> str:
    st.sidebar.markdown("### HELIOS")
    st.sidebar.caption("Mesa de análisis local")
    page = st.sidebar.radio("Sección", ["Mesa", "Preguntar", "Briefing", "Arquitectura"], label_visibility="collapsed")
    st.sidebar.divider()
    for check in readiness():
        mark = "ok" if check.ok else "pendiente"
        st.sidebar.caption(f"{mark} · {check.name}: {check.detail}")
    st.sidebar.divider()
    st.sidebar.caption(SHORT_DISCLAIMER)
    return page


def _mesa() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="kicker">FINTECH · MULTIMODAL · LOCAL</div>
            <h1>Helios</h1>
            <p>El expediente de una compañía, partido en PDF, gráfico, audio y prensa, vuelve a una sola mesa.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.1, 1])
    with left:
        if st.button("Cargar caso demo NorteGrid", type="primary"):
            st.session_state["use_demo"] = True
        live = st.checkbox("Sustituir la serie por precios en vivo (yfinance)", value=False)
        company = st.text_input("Compañía", value="NorteGrid")
        ticker = st.text_input("Ticker", value="NRGX")
    with right:
        pdf = st.file_uploader("PDF de resultados", type=["pdf"])
        chart = st.file_uploader("Gráfico de velas", type=["png", "jpg", "jpeg", "webp"])
        audio = st.file_uploader("Audio de la conferencia", type=["mp3", "wav", "m4a"])
        news = st.file_uploader("Noticias", type=["json", "txt", "md"])
        prices = st.file_uploader("Serie de precios CSV", type=["csv"])
    use_models = st.toggle("Usar modelos locales (Ollama, Whisper, embeddings y CLIP)", value=True)
    if st.session_state.get("use_demo"):
        st.caption("Caso sintético NorteGrid cargado. Un archivo subido sustituye solo esa pieza.")
    if st.button("Ejecutar análisis", type="primary"):
        case = _build_case(company, ticker, live, pdf, chart, audio, news, prices)
        _execute(case, use_models)
    result = st.session_state.get("result")
    if isinstance(result, AnalysisResult):
        _show_result(result)


def _build_case(company, ticker, live, pdf, chart, audio, news, prices) -> CaseInput:
    if st.session_state.get("use_demo"):
        case = load_demo_case()
        case.company = company or case.company
        case.ticker = ticker or case.ticker
    else:
        case = CaseInput(company=company or "Compañía", ticker=ticker or "TICKER")
    if pdf is not None:
        case.pdf_path = _store(pdf, pdf.name)
    if chart is not None:
        case.chart_path = _store(chart, chart.name)
    if audio is not None:
        case.audio_path = _store(audio, audio.name)
    if news is not None:
        case.news_path = _store(news, news.name)
    if prices is not None:
        case.prices_path = _store(prices, prices.name)
        case.live_prices = False
    elif live:
        case.live_prices = True
        case.prices_path = None
    return case


def _store(uploaded, name: str) -> Path:
    folder = ROOT / "data" / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / Path(name).name
    dest.write_bytes(uploaded.getbuffer())
    return dest


def _execute(case: CaseInput, use_models: bool) -> None:
    lines: list[str] = []
    with st.status("Cruzando el expediente...", expanded=True) as status:
        board = st.empty()

        def on_stage(log) -> None:
            lines.append(f"{_mark(log.status)} {log.name} · {log.model} · {log.seconds:.1f}s · {log.detail}")
            items = "".join(f"<li>{_escape(line)}</li>" for line in lines)
            board.markdown(f"<ul>{items}</ul>", unsafe_allow_html=True)

        try:
            result = run_analysis(case, on_stage=on_stage, use_models=use_models)
        except Exception as exc:
            status.update(label="El análisis no pudo cerrarse", state="error")
            st.exception(exc)
            return
        status.update(label="Expediente listo", state="complete")
    st.session_state["result"] = result
    st.session_state["messages"] = []


def _show_result(result: AnalysisResult) -> None:
    facts = result.fact_sheet
    st.markdown(f'<div class="stance">{facts.stance}</div>', unsafe_allow_html=True)
    st.caption(f"{facts.company} · {facts.ticker}" + (" · caso sintético" if facts.synthetic else ""))
    drawdown = facts.price_stats.get("max_drawdown")
    cards = [
        ("Ingresos 2025", _metric(facts, "ingresos_2025_m")),
        ("Margen EBITDA", _metric(facts, "margen_ebitda_pct", "%")),
        ("Capex 2025", _metric(facts, "capex_2025_m")),
        ("Drawdown", _pct(drawdown) if drawdown is not None else "—"),
    ]
    cards_html = "".join(
        f"<div class='kpi'><span>{label}</span><strong>{value}</strong></div>" for label, value in cards
    )
    st.markdown(f"<div class='kpi-row'>{cards_html}</div>", unsafe_allow_html=True)
    st.subheader("Tesis")
    st.write(result.thesis)
    support = f"{result.published_support_ratio:.0%}"
    st.markdown(
        f'<div class="panel">Control de cifras: {support} de las cifras publicadas están en las fuentes. '
        f"Frases retiradas del borrador: {len(result.rejected)}. Modo: {result.thesis_mode}. "
        f"Respaldo del borrador antes del filtro: {result.raw_support_ratio:.0%}.</div>",
        unsafe_allow_html=True,
    )
    if result.rejected:
        with st.expander("Frases retiradas"):
            for item in result.rejected:
                st.write(f"{', '.join(item.numbers)} — {item.text}")
    with st.expander("Etapas del orquestador"):
        st.dataframe(
            [
                {
                    "etapa": stage.name,
                    "modelo": stage.model,
                    "segundos": stage.seconds,
                    "estado": stage.status,
                    "detalle": stage.detail,
                    "caché": stage.cached,
                }
                for stage in result.stages
            ],
            width="stretch",
            hide_index=True,
        )
    with st.expander("Evidencias por modalidad"):
        for evidence in result.evidences:
            st.markdown(f"**{evidence.title}** · `{evidence.locator}`")
            st.write(evidence.text[:900])
    st.caption(result.disclaimer)


def _preguntar() -> None:
    st.header("Preguntar al expediente")
    result = st.session_state.get("result")
    if not isinstance(result, AnalysisResult):
        st.info("Primero ejecuta un análisis en la Mesa.")
        return
    st.session_state.setdefault("messages", [])
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            for hit in message.get("hits", []):
                st.caption(f"{hit.locator} · {hit.mode} · {hit.score:.2f}")
    chips = st.columns(2)
    pending = None
    for index, question in enumerate(SUGGESTED):
        if chips[index % 2].button(question, width="stretch", key=f"suggest-{index}"):
            pending = question
    typed = st.chat_input("Pregunta por una cifra, un riesgo o el gráfico")
    question = pending or typed
    if not question:
        return
    answer = answer_question(question, result, Settings.from_env(), use_models=True)
    st.session_state["messages"].append({"role": "user", "content": question})
    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": answer.text,
            "hits": answer.hits,
        }
    )
    st.rerun()


def _briefing() -> None:
    st.header("Briefing")
    result = st.session_state.get("result")
    if not isinstance(result, AnalysisResult):
        st.info("Primero ejecuta un análisis en la Mesa.")
        return
    st.caption(f"Voz: {result.audio_engine or 'no generada'}. El audio lee la ficha calculada, no la prosa libre del modelo.")
    if result.audio_path and Path(result.audio_path).exists():
        audio = Path(result.audio_path).read_bytes()
        st.audio(audio)
        st.download_button("Descargar audio", data=audio, file_name=Path(result.audio_path).name)
    else:
        st.warning("No hay archivo de audio en esta ejecución. El guion sigue disponible.")
    if result.infographic_path and Path(result.infographic_path).exists():
        image = Path(result.infographic_path).read_bytes()
        st.image(image, width="stretch")
        st.download_button("Descargar infografía", data=image, file_name="infografia.png", mime="image/png")
    st.subheader("Guion")
    st.write(result.briefing_script)
    st.caption(SHORT_DISCLAIMER)


def _arquitectura() -> None:
    st.header("Arquitectura")
    st.write(
        "Helios separa la conexión con los modelos, la lógica de negocio y la pantalla. "
        "Un orquestador encadena visión, transcripción, precios, índice, redacción, control de cifras, infografía y voz."
    )
    path = ROOT / "docs" / "arquitectura.png"
    render_architecture(path)
    st.image(str(path), width="stretch")
    st.markdown(
        """
        | Etapa | Modelo | Presupuesto de latencia en CPU |
        | --- | --- | --- |
        | PDF | PyMuPDF | menos de 2 s |
        | Visión | qwen2.5vl:7b, si falta llava o moondream | 15–90 s por imagen |
        | Audio | faster-whisper small | 20–60 s por minuto y medio |
        | Índice | MiniLM y CLIP ViT-B-32 | menos de 10 s |
        | Tesis | qwen2.5:7b | 20–60 s |
        | Infografía | código | menos de 1 s |
        | Voz | edge-tts, o la voz del sistema | 2–15 s |
        """
    )
    result = st.session_state.get("result")
    if isinstance(result, AnalysisResult):
        cost = estimate_cost(result.stages, Settings.from_env(), briefing_chars=len(result.briefing_script))
        st.subheader("Coste de la última ejecución")
        c1, c2, c3 = st.columns(3)
        c1.metric("Segundos medidos", f"{cost['seconds']:.1f}")
        c2.metric("Coste local estimado", f"{cost['local_eur']:.4f} EUR")
        c3.metric("Escenario API", f"{cost['api_eur']:.4f} EUR")
        st.caption(
            f"Local: {cost['watts']} W y {cost['eur_kwh']} EUR/kWh. "
            "El escenario de API es una hipótesis de trabajo, no una tarifa contratada. "
            f"{cost['note']}."
        )
    st.subheader("Cumplimiento")
    st.write(DISCLAIMER)
    st.write(
        "El PDF, la transcripción y el razonamiento se ejecutan en esta máquina. "
        "La locución con edge-tts usa el servicio gratuito de voz de Microsoft, sin clave; "
        "con HELIOS_TTS=system la voz también queda en local. "
        "No se piden credenciales bancarias ni se envía el expediente a una API de pago."
    )
    st.subheader("Monetización")
    st.write(
        "Suscripción por puesto para gestores independientes y family offices pequeños. "
        "El coste variable de un análisis local es electricidad y el equipo ya comprado, "
        "no una llamada por modalidad."
    )


def _metric(facts, key: str, suffix: str = " M") -> str:
    if key not in facts.metrics:
        return "—"
    value = facts.metrics[key]
    if suffix == "%":
        return _pct(value / 100.0)
    return f"{value:.0f}{suffix}"


def _pct(ratio: float) -> str:
    return f"{abs(ratio) * 100:.1f}".replace(".", ",") + "%"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _mark(status: str) -> str:
    return {"ok": "OK", "omitido": "OMITIDO", "error": "ERROR"}.get(status, status.upper())


main()
