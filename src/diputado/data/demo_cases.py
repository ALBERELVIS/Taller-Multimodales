"""Casos de demostración precargados (imágenes renderizadas y una llamada generada con Bark)."""

from __future__ import annotations

import json

import numpy as np
import soundfile as sf

from diputado import config
from diputado.media import render

DEMO_JSON = config.DEMO_DIR / "demo_cases.json"

CALL_SCRIPT = (
    "Buenos días, le llamo del departamento de seguridad de BancoSur. "
    "Hemos detectado un cargo de novecientos cuarenta euros en su tarjeta. "
    "Para anularlo necesito que me diga ahora mismo el código de seis cifras que le acaba de llegar por SMS. "
    "Es muy urgente, si no lo cancelamos en cinco minutos el dinero se perderá."
)

CASES = [
    {
        "id": "llamada_falso_banco",
        "titulo": "Llamada del «departamento de seguridad» del banco",
        "descripcion": "Voz generada con Bark y pasada por un canal telefónico simulado.",
        "audio": "llamada_falso_banco.wav",
        "esperado": "rojo",
    },
    {
        "id": "sms_correos",
        "titulo": "SMS de Correos: paquete retenido por 1,99 €",
        "descripcion": "Smishing clásico con dominio que imita a Correos.",
        "imagen": "sms_correos.png",
        "esperado": "rojo",
    },
    {
        "id": "whatsapp_hola_mama",
        "titulo": "WhatsApp: «Hola mamá, este es mi número nuevo»",
        "descripcion": "Falso familiar desde un número desconocido pidiendo un Bizum.",
        "imagen": "whatsapp_hola_mama.png",
        "esperado": "rojo",
    },
    {
        "id": "sms_banco_legitimo",
        "titulo": "SMS legítimo del banco (aviso de compra)",
        "descripcion": "Aviso informativo sin enlaces ni peticiones: debe salir verde.",
        "imagen": "sms_banco_legitimo.png",
        "esperado": "verde",
    },
    {
        "id": "carta_cripto",
        "titulo": "Carta de una «gestora» de inversión en cripto",
        "descripcion": "Foto de una carta en papel con rentabilidad garantizada y un IBAN.",
        "imagen": "carta_cripto.png",
        "esperado": "rojo",
    },
]


def build_images() -> None:
    d = config.DEMO_DIR
    render.save(render.render_sms(
        "Correos",
        "Correos: Su paquete ES2849301 está retenido en aduanas por tasas impagadas (1,99 €). "
        "Abone hoy para evitar su devolución: https://correos-aduanas.top/pago",
        hour="10:42",
    ), d / "sms_correos.png")
    render.save(render.render_whatsapp(
        "+34 612 908 441",
        "Hola mamá, se me ha roto el móvil y este es mi número nuevo, guárdalo. "
        "Necesito que me hagas un Bizum de 480 € urgente que no puedo entrar en mi banco. Mañana te lo devuelvo, porfa",
        hour="21:17",
    ), d / "whatsapp_hola_mama.png")
    render.save(render.render_sms(
        "BancoSur",
        "BancoSur: Compra con tarjeta ****4512 en MERCADO CENTRAL por 23,40 EUR el 06/10 a las 10:41. "
        "Si no la reconoces, llama al número que aparece en tu tarjeta.",
        hour="10:43",
        previous=["BancoSur: Ya tienes disponible tu extracto de septiembre en la app."],
    ), d / "sms_banco_legitimo.png")
    render.save(render.render_letter(
        "ATLAS CAPITAL INVERSIONES",
        "Estimado/a cliente: Ha sido seleccionado/a para participar en nuestro fondo privado de criptomonedas "
        "gestionado con inteligencia artificial. Le garantizamos una rentabilidad del 35 % mensual sin riesgo. "
        "Plazas limitadas hasta el viernes. Para reservar su plaza, realice una transferencia inicial de 1.500 € "
        "a la cuenta ES91 2100 0418 4502 0005 1332 indicando su nombre. Su asesor personal le llamará en 24 horas. "
        "Atentamente, Departamento de Clientes Preferentes.",
    ), d / "carta_cripto.png")


def build_call(seed: int = 4, voice: str = "v2/es_speaker_8") -> None:
    from diputado.ai import bark
    from diputado.ai.audio_io import resample
    from diputado.data.telephony import phone_channel

    audio, sr = bark.synthesize(CALL_SCRIPT, voice=voice, seed=seed)
    phone = phone_channel(resample(audio, sr, 16_000), 16_000, np.random.default_rng(seed))
    sf.write(config.DEMO_DIR / "llamada_falso_banco.wav", phone, 16_000)


def save_manifest() -> None:
    DEMO_JSON.write_text(json.dumps(CASES, ensure_ascii=False, indent=2), encoding="utf-8")


def load() -> list[dict]:
    cases = json.loads(DEMO_JSON.read_text(encoding="utf-8")) if DEMO_JSON.exists() else CASES
    for c in cases:
        for k in ("audio", "imagen"):
            if c.get(k):
                c[k + "_path"] = str(config.DEMO_DIR / c[k])
    return cases
