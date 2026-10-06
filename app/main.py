"""Punto de entrada de la aplicación web (`python -m app.main`)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from diputado import config  # noqa: I001  (fija variables de entorno antes que el resto)

config.ensure_dirs()
config.ensure_ffmpeg_on_path()

import gradio as gr  # noqa: E402
from gradio import processing_utils  # noqa: E402

# imageio-ffmpeg no incluye ffprobe, que Gradio usa para comprobar el códec; nuestros vídeos ya son H.264/MP4.
if shutil.which("ffprobe") is None:
    processing_utils.video_is_playable = lambda _path: True

from app import components as C  # noqa: E402
from app import services, ui_analista, ui_cliente, ui_info  # noqa: E402
from diputado.ai import ollama_server  # noqa: E402
from diputado.core import pipeline  # noqa: E402
from diputado.core.schemas import CaseInput  # noqa: E402

CSS = (Path(__file__).parent / "theme.css").read_text(encoding="utf-8")
THEME = gr.themes.Soft(primary_hue="rose", secondary_hue="slate", neutral_hue="slate",
                       font=["Segoe UI", "system-ui", "-apple-system", "sans-serif"])

# La interfaz está diseñada con alto contraste en modo claro; lo forzamos aunque el sistema use modo oscuro.
FORCE_LIGHT = """() => { const u = new URL(window.location.href);
  if (u.searchParams.get('__theme') !== 'light') { u.searchParams.set('__theme', 'light'); window.location.replace(u.href); } }"""

HERO = f"""
<div id="dd-hero"><div class="dd-logo">🛡️</div>
<div><h1>{config.BRAND_NAME}</h1><p>{config.BRAND_TAGLINE} · {config.BRAND_CLAIM}</p></div>
<div class="dd-status" id="dd-status">{{status}}</div></div>
"""


def analyst_updates(ua: dict, r) -> dict:
    from diputado.ai.gpu import gpu

    return {
        ua["timeline"]: C.timeline_df(r),
        ua["contrib"]: C.contributions_fig(r),
        ua["highlight"]: r.highlights,
        ua["tactics"]: C.tactics_df(r),
        ua["gallery"]: C.campaigns_gallery(r),
        ua["raw"]: C.raw(r),
        ua["vram"]: gpu.snapshot(),
    }


def make_analyze(uc: dict, ua: dict):
    def analyze(audio, image, text):
        if not (audio or image or (text and text.strip())):
            raise gr.Error("Sube una captura, graba una llamada o escribe el mensaje que quieres comprobar.")
        try:
            yield from _analyze(audio, image, text)
        except gr.Error:
            raise
        except Exception as exc:
            yield {uc["progress"]: f'<div class="dd-progress dd-idle">No hemos podido terminar el análisis '
                                   f'({type(exc).__name__}). Inténtalo de nuevo; si se repite, reinicia la aplicación.</div>'}
            raise gr.Error(f"Error inesperado: {exc}") from exc

    def _analyze(audio, image, text):
        case = CaseInput(text=(text or "").strip() or None, image=image, audio=audio)
        yield {uc["semaforo"]: C.semaforo(None), uc["summary"]: "", uc["voice"]: None, uc["infographic"]: None,
               uc["video"]: None, uc["share"]: gr.DownloadButton(visible=False)}
        r = None
        for r in pipeline.analyze(case):
            if not r.done:
                yield {uc["progress"]: C.progress(r)}
        out = {uc["progress"]: C.progress(r, current="Preparando el aviso de voz"), uc["semaforo"]: C.semaforo(r),
               uc["summary"]: C.summary_md(r)}
        out.update(analyst_updates(ua, r))
        yield out
        for stage, r in pipeline.outputs(r):
            yield {
                uc["progress"]: C.progress(r, current=stage or None),
                uc["voice"]: r.audio_out,
                uc["infographic"]: r.infographic,
                uc["video"]: r.video,
                uc["share"]: gr.DownloadButton(value=r.video, visible=bool(r.video)),
                ua["timeline"]: C.timeline_df(r),
                ua["raw"]: C.raw(r),
            }
        f1, f2 = ui_analista.charts()
        yield {ua["kpis"]: ui_analista.kpis_html(), ua["chart_daily"]: f1, ua["chart_camp"]: f2, ua["recent"]: ui_analista.recent()}

    return analyze


def answer_question(q_audio, q_text):
    from diputado.ai import asr, llm, tts

    question = (q_text or "").strip()
    heard = ""
    if q_audio:
        tr, _ = asr.transcribe(q_audio)
        question = tr["text"]
        heard = f"🎙️ He entendido: *«{question}»*"
    if not question:
        raise gr.Error("Haz una pregunta en voz alta o escríbela.")
    yield heard, "⏳ Pensando…", None
    text, _ = llm.answer(question)
    yield heard, f"### {text}", None
    path, _ = tts.speak(text)
    yield heard, f"### {text}", path


def build() -> gr.Blocks:
    with gr.Blocks(title=f"{config.BRAND_NAME} · {config.BRAND_TAGLINE}", theme=THEME, css=CSS, js=FORCE_LIGHT) as demo:
        hero = gr.HTML(HERO.format(status=services.status_html()), elem_id="dd-hero-box")
        with gr.Tabs():
            with gr.Tab("👵 Cliente"):
                uc = ui_cliente.build()
            with gr.Tab("🏦 Analista del banco"):
                ua = ui_analista.build()
            with gr.Tab("⚙️ Cómo funciona"):
                ui_info.build()

        timer = gr.Timer(2.0)
        timer.tick(lambda: (HERO.format(status=services.status_html()), gr.Timer(active=not services.ready())),
                   outputs=[hero, timer], show_progress="hidden", queue=False)

        uc["demo"].change(lambda t: ui_cliente.load_demo(t, uc["demo_cases"]), inputs=uc["demo"],
                          outputs=[uc["audio"], uc["image"], uc["text"], uc["input_tabs"]])
        outputs = [uc[k] for k in ("progress", "semaforo", "summary", "voice", "infographic", "video", "share")]
        outputs += [ua[k] for k in ("timeline", "contrib", "highlight", "tactics", "gallery", "raw", "vram",
                                    "kpis", "chart_daily", "chart_camp", "recent")]
        uc["analyze"].click(make_analyze(uc, ua), inputs=[uc["audio"], uc["image"], uc["text"]], outputs=outputs,
                            show_progress="hidden", concurrency_limit=1)
        uc["call_bank"].click(lambda: gr.Info("Simulación: te pondríamos en contacto con el número oficial de tu banco "
                                              "(el que aparece en el reverso de tu tarjeta)."))
        uc["q_btn"].click(answer_question, inputs=[uc["q_audio"], uc["q_text"]],
                          outputs=[uc["q_heard"], uc["q_answer"], uc["q_voice"]], concurrency_limit=1)
        ua["sql_btn"].click(ui_analista.ask, inputs=ua["sql_q"], outputs=[ua["sql_answer"], ua["sql_code"], ua["sql_df"]],
                            concurrency_limit=1)
        ua["sql_q"].submit(ui_analista.ask, inputs=ua["sql_q"], outputs=[ua["sql_answer"], ua["sql_code"], ua["sql_df"]],
                           concurrency_limit=1)
        ua["refresh"].click(ui_analista.refresh, outputs=[ua["kpis"], ua["chart_daily"], ua["chart_camp"], ua["recent"]])
    return demo


def main() -> None:
    if not ollama_server.ensure_server(install_if_missing=True):
        print("AVISO: no he podido arrancar Ollama; el razonamiento y la lectura de imágenes no estarán disponibles.")
    services.warmup()
    demo = build()
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=config.APP_PORT,
        inbrowser=os.environ.get("DD_NO_BROWSER") != "1",
        allowed_paths=[str(config.OUTPUTS_DIR), str(config.DATA_DIR)],
        favicon_path=None,
        show_api=False,
    )


if __name__ == "__main__":
    main()
