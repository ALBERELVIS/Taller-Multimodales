"""Piezas visuales reutilizables (HTML y gráficos) para las dos vistas."""

from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go

from diputado import config
from diputado.core import fusion
from diputado.core.schemas import AnalysisResult

LEVEL_TEXT = {"rojo": "ESTAFA PROBABLE", "ambar": "SOSPECHOSO", "verde": "PARECE SEGURO"}
LEVEL_COLOR = {"rojo": "#ff3b54", "ambar": "#ffb020", "verde": "#1dffb0"}


def semaforo(r: AnalysisResult | None) -> str:
    level = r.level if r and r.level else None
    lights = "".join(
        f'<div class="dd-light dd-{lv} {"dd-on" if lv == level else ""}"></div>' for lv in ("rojo", "ambar", "verde")
    )
    if level is None:
        label, pct = "Esperando un mensaje o una llamada", ""
    else:
        label, pct = LEVEL_TEXT[level], f'<div class="dd-pct">Riesgo {r.risk * 100:.0f} %</div>'
    color = LEVEL_COLOR.get(level, "#8a8f98")
    return (f'<div class="dd-semaforo"><div class="dd-lights">{lights}</div>'
            f'<div class="dd-verdict" style="color:{color}">{label}{pct}</div></div>')


def progress(r: AnalysisResult | None, extra_done: list[str] | None = None, current: str | None = None) -> str:
    del extra_done  # los tiempos viven en la cronología del analista, no en esta vista
    if r is None:
        return '<div class="dd-progress dd-idle">Sube una captura, graba la llamada o escribe el mensaje y pulsa <b>Analizar</b>.</div>'
    stage = current or (r.stage if not r.done else "")
    if stage:
        return f'<div class="dd-progress"><div class="dd-stage"><span class="dd-spin"></span>{html.escape(stage)}</div></div>'
    if r and r.done:
        return '<div class="dd-progress dd-idle">Listo. Escucha el aviso y, si hace falta, compártelo con tu familia.</div>'
    return '<div class="dd-progress dd-idle">Trabajando…</div>'


def summary_md(r: AnalysisResult) -> str:
    color = LEVEL_COLOR[r.level]
    advice = "".join(f"<li>{html.escape(a)}</li>" for a in r.advice[:3])
    tactics = "".join(
        f'<span class="dd-tag">{config.TACTIC_LABELS[t]}</span>' for t, p in r.tactics.items() if p >= 0.5
    )
    flags = "".join(f'<span class="dd-tag dd-tag-soft">{html.escape(f)}</span>' for f in (r.extract or {}).get("flags_humanos", [])[:4])
    camp = ""
    if r.campaigns and r.level != "verde" and r.campaigns[0]["similitud"] >= 0.45:
        camp = f'<div class="dd-camp">Se parece a una campaña conocida: <b>{html.escape(r.campaigns[0]["nombre"])}</b></div>'
    return (f'<div class="dd-summary" style="border-color:{color}">'
            f'<h2 style="color:{color}">{html.escape(r.headline)}</h2>'
            f'<p class="dd-expl">{html.escape(r.explanation)}</p>{camp}'
            f'<div class="dd-tags">{tactics}{flags}</div>'
            f'<h3>Qué hacer ahora</h3><ol class="dd-advice">{advice}</ol></div>')


def contributions_fig(r: AnalysisResult | None) -> go.Figure:
    fig = go.Figure()
    if r and r.contributions:
        items = sorted(r.contributions.items(), key=lambda kv: kv[1])
        names = [fusion.SIGNAL_LABELS.get(k, k) for k, _ in items]
        vals = [v for _, v in items]
        fig.add_bar(x=vals, y=names, orientation="h",
                    marker_color=["#ff3b54" if v > 0 else "#1dffb0" for v in vals],
                    text=[f"p={r.signal_inputs.get(k, 0):.2f}" for k, _ in items], textposition="outside")
    fig.update_layout(title="Contribución de cada señal al riesgo (log-odds)", height=320, margin=dict(l=10, r=30, t=50, b=30),
                      xaxis_title="← hacia legítimo · hacia estafa →", template="plotly_dark",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1520", font_color="#e7f4fb")
    return fig


def timeline_df(r: AnalysisResult | None) -> pd.DataFrame:
    if not r:
        return pd.DataFrame(columns=["Etapa", "Modelo", "Tiempo (s)", "Detalle"])
    return pd.DataFrame([{"Etapa": s.etapa, "Modelo": s.modelo, "Tiempo (s)": round(s.ms / 1000, 2), "Detalle": s.detalle}
                         for s in r.timeline])


def tactics_df(r: AnalysisResult | None) -> pd.DataFrame:
    if not r or not r.tactics:
        return pd.DataFrame(columns=["Táctica", "Probabilidad", "Fuente"])
    llm_t = set((r.llm or {}).get("tacticas", []))
    km = (r.tactic_model or {}).get("tactics", {})
    rows = []
    for t, p in r.tactics.items():
        src = " + ".join(s for s, ok in (("TacticNet", km.get(t, 0) >= 0.5), ("Qwen3", t in llm_t)) if ok) or "-"
        rows.append({"Táctica": config.TACTIC_LABELS[t], "Probabilidad": round(p, 3), "Fuente": src})
    return pd.DataFrame(rows)


def campaigns_gallery(r: AnalysisResult | None) -> list[tuple[str, str]]:
    if not r:
        return []
    return [(c["imagen"], f"{c['nombre']} · similitud {c['similitud']:.2f}") for c in r.campaigns]


def raw(r: AnalysisResult | None) -> dict:
    if not r:
        return {}
    return {
        "canal": r.canal,
        "modalidades": r.modalidades,
        "transcripcion": (r.transcript or {}).get("text"),
        "lectura_visual": r.vision,
        "contexto_acustico": r.acoustic,
        "voz_sintetica": r.voice,
        "reglas": {k: v for k, v in (r.extract or {}).items() if k != "dominios"},
        "dominios": (r.extract or {}).get("dominios"),
        "tacticnet": r.tactic_model,
        "llm": r.llm,
        "fusion": {"riesgo": r.risk, "nivel": r.level, "contribuciones": r.contributions, "regla_dura": r.hard_rule},
        "errores": r.errors,
        "salidas": {"audio": r.audio_out, "infografia": r.infographic_meta, "video": r.video},
    }
