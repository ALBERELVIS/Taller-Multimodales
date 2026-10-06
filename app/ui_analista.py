"""Vista Analista del banco: trazabilidad del último análisis y exploración de casos."""

from __future__ import annotations

import gradio as gr
import pandas as pd
import plotly.express as px

from app import components as C
from diputado.core import cases_db

EXAMPLES = [
    "¿Cuántos casos rojos hemos tenido en los últimos 7 días?",
    "¿Cuáles son las 5 campañas más frecuentes este mes?",
    "¿Cuánto dinero se intentó sacar con el falso familiar?",
    "¿Qué provincias tienen más casos de llamadas falsas del banco?",
    "¿Cuál es la edad media de los clientes afectados por cada canal?",
]


def kpis_html() -> str:
    try:
        df = cases_db.safe_query(
            "SELECT COUNT(*) AS n, SUM(nivel='rojo') AS rojos, SUM(nivel='ambar') AS ambar, "
            "ROUND(SUM(CASE WHEN nivel='rojo' THEN COALESCE(importe_eur,0) ELSE 0 END)) AS importe, "
            "SUM(origen='app') AS app FROM casos WHERE fecha >= datetime('now','-30 day')"
        ).iloc[0]
        top = cases_db.safe_query(
            "SELECT campana, COUNT(*) n FROM casos WHERE campana IS NOT NULL AND fecha >= datetime('now','-7 day') GROUP BY campana ORDER BY n DESC LIMIT 1"
        )
    except Exception:
        return ""
    top_name = top.iloc[0]["campana"] if len(top) else "-"
    cards = [
        (f"{int(df['n'] or 0)}", "casos analizados (30 días)"),
        (f"{(df['rojos'] or 0) / max(df['n'] or 1, 1) * 100:.0f} %", "marcados en rojo"),
        (f"{(df['importe'] or 0):,.0f} €".replace(",", "."), "importe que se intentó robar"),
        (top_name, "campaña más activa esta semana"),
    ]
    return '<div class="dd-kpis">' + "".join(f'<div class="dd-kpi"><div class="v">{v}</div><div class="l">{l}</div></div>' for v, l in cards) + "</div>"


def charts():
    try:
        daily = cases_db.safe_query(
            "SELECT date(fecha) AS dia, nivel, COUNT(*) AS casos FROM casos WHERE fecha >= datetime('now','-60 day') GROUP BY dia, nivel ORDER BY dia"
        )
        camp = cases_db.safe_query(
            "SELECT campana, COUNT(*) AS casos FROM casos WHERE campana IS NOT NULL AND fecha >= datetime('now','-30 day') GROUP BY campana ORDER BY casos DESC LIMIT 8"
        )
    except Exception:
        daily, camp = pd.DataFrame(columns=["dia", "nivel", "casos"]), pd.DataFrame(columns=["campana", "casos"])
    colors = {"rojo": "#d7263d", "ambar": "#e89128", "verde": "#2a9d8f"}
    f1 = px.bar(daily, x="dia", y="casos", color="nivel", color_discrete_map=colors, title="Casos por día y nivel")
    f1.update_layout(height=320, template="plotly_white", margin=dict(l=10, r=10, t=50, b=10), legend_title=None)
    f2 = px.bar(camp.sort_values("casos"), x="casos", y="campana", orientation="h", title="Campañas más activas (30 días)",
                color_discrete_sequence=["#1f2a44"])
    f2.update_layout(height=320, template="plotly_white", margin=dict(l=10, r=10, t=50, b=10))
    return f1, f2


def recent():
    try:
        return cases_db.recent(12)
    except Exception:
        return pd.DataFrame()


def build() -> dict:
    ui: dict = {}
    gr.Markdown("### Último análisis: traza completa de modelos y decisión")
    with gr.Row():
        with gr.Column(scale=6):
            ui["timeline"] = gr.Dataframe(C.timeline_df(None), label="Cronología del pipeline", interactive=False, wrap=True)
            ui["contrib"] = gr.Plot(C.contributions_fig(None), label="Explicabilidad de la fusión")
        with gr.Column(scale=5):
            ui["highlight"] = gr.HighlightedText(label="Evidencia unificada con frases sospechosas resaltadas", combine_adjacent=True, show_legend=True)
            ui["tactics"] = gr.Dataframe(C.tactics_df(None), label="Tácticas detectadas", interactive=False)
            ui["gallery"] = gr.Gallery(label="Campañas conocidas más parecidas (búsqueda multimodal)", columns=3, height=300, object_fit="contain")
    with gr.Accordion("Salida en bruto de cada modelo (JSON)", open=False):
        ui["raw"] = gr.JSON()
        ui["vram"] = gr.JSON(label="Estado de la GPU")
    gr.Markdown("### Panel de casos")
    ui["kpis"] = gr.HTML(kpis_html())
    with gr.Row():
        f1, f2 = charts()
        ui["chart_daily"] = gr.Plot(f1)
        ui["chart_camp"] = gr.Plot(f2)
    ui["recent"] = gr.Dataframe(recent(), label="Últimos casos (datos personales enmascarados)", interactive=False)
    ui["refresh"] = gr.Button("Actualizar panel")
    gr.Markdown("### Pregunta a los datos en lenguaje natural (agente SQL de solo lectura)")
    with gr.Row():
        ui["sql_q"] = gr.Textbox(label="Pregunta", placeholder=EXAMPLES[0], scale=5)
        ui["sql_btn"] = gr.Button("Consultar", variant="primary", scale=1)
    gr.Examples(EXAMPLES, inputs=ui["sql_q"], label="Ejemplos")
    ui["sql_answer"] = gr.Markdown()
    ui["sql_code"] = gr.Code(language="sql", label="SQL ejecutado", interactive=False)
    ui["sql_df"] = gr.Dataframe(label="Resultado", interactive=False)
    return ui


def ask(question: str):
    from diputado.core.sql_agent import agent

    if not question or not question.strip():
        raise gr.Error("Escribe una pregunta sobre los casos.")
    res = agent.ask(question)
    md = f"**Respuesta:** {res['answer']}\n\n<span class='dd-note'>Modo: {res['mode']} · {res['ms'] / 1000:.1f} s</span>"
    return md, res["sql"] or "", res["df"]


def refresh():
    f1, f2 = charts()
    return kpis_html(), f1, f2, recent()
