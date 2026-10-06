"""Pestaña «Cómo funciona»: arquitectura y fichas de modelos para el evaluador."""

from __future__ import annotations

import gradio as gr

from diputado import config

FLOW = """
<div class="dd-card">
<div style="display:grid;grid-template-columns:1fr 1.6fr 1fr;gap:18px;align-items:start">
 <div><h3>Entradas</h3>
  <div class="dd-chip">📞 Llamada (audio)</div><br><div class="dd-chip">🎙️ Pregunta por voz</div><br>
  <div class="dd-chip">🖼️ Captura / foto de carta</div><br><div class="dd-chip">⌨️ Texto pegado</div></div>
 <div><h3>Orquestación (grafo determinista)</h3>
  <ol>
   <li><b>Whisper large-v3-turbo</b> transcribe · <b>CLAP</b> describe el sonido · <b>VozSinteticaNet</b> (Keras) estima si la voz es sintética</li>
   <li><b>Qwen2.5-VL 7B</b> lee la imagen (texto, remitente, enlaces, señales visuales) · <b>SigLIP2</b> la compara con campañas</li>
   <li><b>Reglas</b> (dominios imitados, PIN/OTP, IBAN) · <b>e5</b> + <b>TacticNet</b> (Keras) clasifican tácticas</li>
   <li><b>Qwen3 8B</b> razona como un analista con salida JSON validada</li>
   <li><b>Fusión log-odds</b> calibrada → semáforo explicable</li>
  </ol></div>
 <div><h3>Salidas</h3>
  <div class="dd-chip">🚦 Semáforo + explicación</div><br><div class="dd-chip">🔊 Aviso hablado (MMS-TTS)</div><br>
  <div class="dd-chip">🖼️ Infografía (SDXL-Turbo + control SigLIP2)</div><br><div class="dd-chip">🎬 Vídeo-alerta (moviepy)</div><br>
  <div class="dd-chip">📊 Consola + agente SQL (smolagents)</div></div>
</div></div>
"""

MODELS = """
| Modelo | Modalidad | Para qué lo usamos | Dónde corre |
|---|---|---|---|
| `openai/whisper-large-v3-turbo` | audio → texto | Transcribir llamadas y preguntas | GPU (por turnos) |
| `laion/clap-htsat-unfused` | audio ↔ texto | Contexto acústico y embeddings de voz | CPU |
| **VozSinteticaNet** (Keras, propio) | audio | ¿Voz humana o sintética? | CPU/GPU |
| `qwen2.5vl:7b` (Ollama) | imagen → texto | Leer capturas, cartas y correos | GPU (por turnos) |
| `google/siglip2-base-patch16-224` | imagen ↔ texto | Búsqueda de campañas y control de calidad | CPU |
| `intfloat/multilingual-e5-small` | texto | Embeddings para TacticNet y campañas | CPU |
| **TacticNet** (Keras, propio) | texto | Probabilidad de estafa y 7 tácticas | CPU/GPU |
| `qwen3:8b` (Ollama) | texto → texto | Razonamiento y explicación | GPU (por turnos) |
| `qwen2.5:7b` (Ollama) + smolagents | texto → SQL | Agente de datos del analista | GPU (por turnos) |
| `facebook/mms-tts-spa` | texto → voz | Aviso hablado | CPU |
| `stabilityai/sdxl-turbo` | texto → imagen | Ilustración de la infografía | GPU (por turnos) |
| `suno/bark-small` | texto → voz | Generar llamadas sintéticas (datos y demo) | GPU (offline) |
"""

PRIVACY = f"""
**Privacidad y cumplimiento.** Todo se ejecuta en este equipo: ningún audio, imagen ni dato bancario sale de él y no usamos APIs de pago.
Guardamos los casos con teléfonos, IBAN y DNI enmascarados. El agente SQL abre la base en modo de solo lectura.
Todo el contenido generado lleva la marca «{config.AI_WATERMARK}» (AI Act, art. 50). {config.BRAND_NAME} informa y aconseja,
pero la decisión final es siempre de la persona: no bloqueamos pagos ni accedemos a cuentas.
"""


def build() -> None:
    gr.HTML(FLOW)
    gr.Markdown(MODELS)
    gr.Markdown(PRIVACY)
