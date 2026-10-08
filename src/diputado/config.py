"""Configuración central de DiputadoDetector.

Este módulo se importa antes que cualquier librería de IA: fija las variables de
entorno que obligan a Hugging Face, Keras y Ollama a trabajar dentro de la carpeta
del repositorio, de modo que nada se escriba fuera de ella.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

BRAND_NAME = "DiputadoDetector"
BRAND_TAGLINE = "Detector de estafas multimodal"
BRAND_CLAIM = "Antes de pagar, de dar un código o de devolver una llamada: pregúntanos."

ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = Path(os.environ.get("DD_MODELS_DIR", ROOT / "models"))
HF_HOME = MODELS_DIR / "hf"
OLLAMA_MODELS_DIR = MODELS_DIR / "ollama"
ARTIFACTS_DIR = ROOT / "artifacts"
DATA_DIR = ROOT / "data"
DEMO_DIR = DATA_DIR / "demo"
CAMPAIGNS_DIR = DATA_DIR / "campaigns"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
OUTPUTS_DIR = ROOT / "outputs"
TOOLS_DIR = ROOT / ".tools"
CASES_DB = DATA_DIR / "cases.sqlite"

os.environ.setdefault("HF_HOME", str(HF_HOME))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("KERAS_BACKEND", "torch")
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
if os.name != "nt":
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
if os.environ.get("DD_OFFLINE", "0") == "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

OLLAMA_PORT = int(os.environ.get("DD_OLLAMA_PORT", "11435"))
OLLAMA_HOST = os.environ.get("DD_OLLAMA_HOST", f"http://127.0.0.1:{OLLAMA_PORT}")
APP_PORT = int(os.environ.get("DD_APP_PORT", "7860"))

# Modelos de Hugging Face (id -> patrones de ficheros que descargamos)
HF_MODELS: dict[str, dict] = {
    "asr": {"id": "openai/whisper-large-v3-turbo", "allow": ["*.json", "*.txt", "model.safetensors"]},
    "asr_cpu": {"id": "openai/whisper-base", "allow": ["*.json", "*.txt", "model.safetensors"]},
    "text_emb": {"id": "intfloat/multilingual-e5-small", "allow": ["*.json", "model.safetensors", "sentencepiece.bpe.model", "1_Pooling/*"]},
    "siglip": {"id": "google/siglip2-base-patch16-224", "allow": ["*.json", "*.model", "model.safetensors"]},
    "clip": {"id": "openai/clip-vit-base-patch32", "allow": ["*.json", "*.txt", "pytorch_model.bin"]},
    "clap": {"id": "laion/clap-htsat-unfused", "allow": ["*.json", "*.txt", "pytorch_model.bin"]},
    "tts": {"id": "facebook/mms-tts-spa", "allow": ["*.json", "model.safetensors"]},
    # Locutor de la aplicación: hombre, español de España. MMS se queda para el dataset.
    "piper": {
        "id": "rhasspy/piper-voices",
        "file": "es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
        "allow": [
            "es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
            "es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json",
        ],
    },
    "bark": {
        "id": "suno/bark-small",
        "allow": ["*.json", "*.txt", "pytorch_model.bin", "speaker_embeddings/v2/es_*", "speaker_embeddings/v2/en_speaker_6*"],
    },
    "sdxl": {
        "id": "stabilityai/sdxl-turbo",
        "allow": ["model_index.json", "*/config.json", "tokenizer*/*", "scheduler/*", "*/*fp16.safetensors"],
    },
}

# Modelos de Ollama
OLLAMA_VLM = os.environ.get("DD_VLM", "qwen2.5vl:7b")
OLLAMA_LLM = os.environ.get("DD_LLM", "qwen3:8b")
OLLAMA_AGENT_LLM = os.environ.get("DD_AGENT_LLM", "qwen2.5:7b")
# Modelo de 46 MB que cargamos justo antes del de visión (ver ollama_client.prime_vram).
OLLAMA_PRIMER = "all-minilm"
OLLAMA_MODELS = [OLLAMA_VLM, OLLAMA_LLM, OLLAMA_AGENT_LLM, OLLAMA_PRIMER]

# Umbrales del semáforo (probabilidad fusionada de estafa)
THRESHOLD_AMBER = 0.35
THRESHOLD_RED = 0.65

# Taxonomía de tácticas que reconoce TacticNet
TACTICS: dict[str, str] = {
    "suplantacion_entidad": "Se hace pasar por un banco, Correos, la DGT, Hacienda u otra entidad",
    "urgencia_amenaza": "Mete prisa o amenaza con bloqueos, multas o pérdidas",
    "credenciales_otp": "Pide claves, PIN, códigos SMS o datos de la tarjeta",
    "enlace_sospechoso": "Empuja a pulsar un enlace o descargar una app",
    "pago_transferencia": "Pide un pago, una transferencia o un Bizum",
    "falso_familiar": "Finge ser un familiar con un número nuevo o en apuros",
    "premio_inversion": "Promete premios, herencias o inversiones con rentabilidad milagrosa",
}
TACTIC_LABELS = {
    "suplantacion_entidad": "Suplantación de entidad",
    "urgencia_amenaza": "Urgencia o amenaza",
    "credenciales_otp": "Pide claves o códigos",
    "enlace_sospechoso": "Enlace sospechoso",
    "pago_transferencia": "Pide dinero",
    "falso_familiar": "Falso familiar",
    "premio_inversion": "Premio o inversión milagro",
}

AI_WATERMARK = "Contenido generado por IA · " + BRAND_NAME


def ensure_dirs() -> None:
    for d in (MODELS_DIR, HF_HOME, OLLAMA_MODELS_DIR, OUTPUTS_DIR, ARTIFACTS_DIR, TOOLS_DIR / "bin"):
        d.mkdir(parents=True, exist_ok=True)


def ensure_ffmpeg_on_path() -> str | None:
    """Expone el ffmpeg que trae imageio-ffmpeg como `ffmpeg.exe` en .tools/bin.

    librosa, pydub (Gradio) y moviepy buscan un ejecutable llamado exactamente
    `ffmpeg`; el binario empaquetado tiene otro nombre, así que lo enlazamos.
    """
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    src = Path(imageio_ffmpeg.get_ffmpeg_exe())
    bin_dir = TOOLS_DIR / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    dst = bin_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if not dst.exists():
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    return str(dst)
