"""Vista Cliente: pocos botones, letra grande y respuesta por voz."""

from __future__ import annotations

import gradio as gr

from app import components as C
from diputado.data import demo_cases


def build() -> dict:
    ui: dict = {}
    cases = demo_cases.load()
    ui["demo_cases"] = cases
    with gr.Row(equal_height=False):
        with gr.Column(scale=5):
            with gr.Tabs(selected="msg") as ui["input_tabs"]:
                with gr.Tab("¿Me están llamando?", id="call"):
                    gr.Markdown("Graba la llamada con el altavoz puesto, o sube la grabación.")
                    ui["audio"] = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Llamada o nota de voz")
                with gr.Tab("¿Es fiable este mensaje?", id="msg"):
                    ui["image"] = gr.Image(type="filepath", sources=["upload", "clipboard", "webcam"], label="Captura del SMS, WhatsApp, correo o foto de una carta", height=360)
                    ui["text"] = gr.Textbox(label="…o pega aquí el texto", lines=3, placeholder="Ej.: Correos: su paquete está retenido, abone 1,99 € en…")
                with gr.Tab("Pregúntame", id="ask"):
                    gr.Markdown("Hazme cualquier pregunta sobre estafas o seguridad bancaria. Puedes hablar o escribir.")
                    ui["q_audio"] = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Tu pregunta en voz alta")
                    ui["q_text"] = gr.Textbox(label="…o escríbela", placeholder="¿Es normal que mi banco me pida el PIN por teléfono?")
                    ui["q_btn"] = gr.Button("Responder", variant="primary", elem_classes="dd-big-btn")
                    ui["q_heard"] = gr.Markdown()
                    ui["q_answer"] = gr.Markdown()
                    ui["q_voice"] = gr.Audio(label="Respuesta hablada", autoplay=True, interactive=False)
            ui["analyze"] = gr.Button("Analizar ahora", elem_id="dd-analyze")
            with gr.Accordion("Casos de demostración", open=True):
                ui["demo"] = gr.Radio(choices=[c["titulo"] for c in cases], label="Elige un caso y pulsa Analizar", value=None)
            ui["progress"] = gr.HTML(C.progress(None))
        with gr.Column(scale=6):
            ui["semaforo"] = gr.HTML(C.semaforo(None))
            ui["summary"] = gr.HTML()
            ui["voice"] = gr.Audio(label="Aviso en voz alta", autoplay=True, interactive=False)
            with gr.Row():
                ui["infographic"] = gr.Image(label="Infografía para recordar", interactive=False, height=420)
                ui["video"] = gr.Video(label="Vídeo-alerta para tu familia", interactive=False, height=420)
            with gr.Row():
                ui["share"] = gr.DownloadButton("Compartir con mi familia", visible=False, variant="secondary")
                ui["call_bank"] = gr.Button("Llamar a mi banco", variant="secondary")
    return ui


def load_demo(title: str, cases: list[dict]):
    case = next((c for c in cases if c["titulo"] == title), None)
    if case is None:
        return gr.skip(), gr.skip(), gr.skip(), gr.skip()
    if case.get("audio_path"):
        return case["audio_path"], None, "", gr.Tabs(selected="call")
    return None, case.get("imagen_path"), "", gr.Tabs(selected="msg")
