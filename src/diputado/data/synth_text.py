"""Generación de mensajes sintéticos en español con Qwen3 (supervisión débil por receta).

Cada receta fija un canal, un escenario y sus etiquetas (estafa sí/no + tácticas).
Pedimos al LLM varias variantes por llamada, con temperatura alta y semillas
distintas, y heredamos las etiquetas de la receta. Incluimos muchos negativos
difíciles: mensajes legítimos que también hablan de bancos, códigos o paquetes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from diputado import config
from diputado.ai import ollama_client

T = list(config.TACTICS)

SCAM_RECIPES = [
    ("sms", "Correos o una empresa de paquetería retiene un paquete por tasas pequeñas y da un enlace para pagar", ["suplantacion_entidad", "urgencia_amenaza", "enlace_sospechoso", "pago_transferencia"]),
    ("sms", "Una empresa de mensajería dice que no pudo entregar y pide reprogramar en un enlace acortado", ["suplantacion_entidad", "enlace_sospechoso"]),
    ("sms", "La DGT avisa de una multa pendiente con recargo si no se paga en un enlace", ["suplantacion_entidad", "urgencia_amenaza", "enlace_sospechoso", "pago_transferencia"]),
    ("sms", "El banco avisa de un acceso no autorizado y pide verificar la identidad en un enlace en 24 horas", ["suplantacion_entidad", "urgencia_amenaza", "enlace_sospechoso", "credenciales_otp"]),
    ("sms", "El banco dice que se ha bloqueado la tarjeta y hay que llamar a un número o entrar en una web", ["suplantacion_entidad", "urgencia_amenaza", "enlace_sospechoso"]),
    ("llamada", "Transcripción de una llamada de un falso empleado de seguridad del banco que pide el código SMS para anular un cargo", ["suplantacion_entidad", "urgencia_amenaza", "credenciales_otp"]),
    ("llamada", "Transcripción de una llamada que pide transferir los ahorros a una cuenta segura porque la cuenta está hackeada", ["suplantacion_entidad", "urgencia_amenaza", "pago_transferencia"]),
    ("llamada", "Transcripción de un falso técnico informático que pide instalar AnyDesk y las claves del banco", ["suplantacion_entidad", "urgencia_amenaza", "credenciales_otp"]),
    ("llamada", "Transcripción de una llamada de la compañía de la luz que amenaza con cortar el suministro si no se paga ya con tarjeta", ["suplantacion_entidad", "urgencia_amenaza", "pago_transferencia", "credenciales_otp"]),
    ("whatsapp", "Un supuesto hijo o hija escribe desde un número nuevo porque se le rompió el móvil y pide un Bizum o transferencia urgente", ["falso_familiar", "urgencia_amenaza", "pago_transferencia"]),
    ("whatsapp", "Un supuesto familiar con número nuevo pide que le pases el código que te ha llegado por SMS", ["falso_familiar", "credenciales_otp"]),
    ("whatsapp", "Falso sorteo de un supermercado o marca que pide pagar gastos de envío en un enlace", ["premio_inversion", "enlace_sospechoso", "pago_transferencia"]),
    ("whatsapp", "Falsa oferta de empleo desde casa muy bien pagada que acaba pidiendo un depósito", ["premio_inversion", "pago_transferencia"]),
    ("whatsapp", "Falso comprador de segunda mano que envía una solicitud de Bizum para que la aceptes", ["pago_transferencia", "urgencia_amenaza"]),
    ("email", "Falsa Agencia Tributaria anuncia una devolución y pide los datos de la tarjeta antes de un plazo", ["suplantacion_entidad", "urgencia_amenaza", "enlace_sospechoso", "credenciales_otp"]),
    ("email", "Falsa plataforma de streaming dice que el pago falló y hay que actualizar la tarjeta en 24 horas", ["suplantacion_entidad", "urgencia_amenaza", "enlace_sospechoso", "credenciales_otp"]),
    ("email", "Falso bufete promete recuperar dinero perdido en inversiones a cambio de una tasa", ["premio_inversion", "pago_transferencia", "suplantacion_entidad"]),
    ("web", "Anuncio con un famoso que promete rentabilidades garantizadas con bitcoin o inteligencia artificial", ["premio_inversion", "enlace_sospechoso", "pago_transferencia"]),
    ("sms", "La Seguridad Social amenaza con suspender la pensión si no se actualizan los datos en un enlace", ["suplantacion_entidad", "urgencia_amenaza", "enlace_sospechoso"]),
    ("carta", "Carta que anuncia una herencia de un pariente lejano en el extranjero y pide pagar gastos notariales", ["premio_inversion", "pago_transferencia"]),
]

LEGIT_RECIPES = [
    ("sms", "El banco informa de una compra con tarjeta realizada, sin enlaces ni peticiones"),
    ("sms", "Código de un solo uso para confirmar una compra que el usuario está haciendo, advirtiendo que no lo comparta con nadie"),
    ("sms", "Correos o una empresa de mensajería avisa de que el paquete llegará mañana, sin pagos, remitiendo a la app oficial"),
    ("sms", "Recordatorio de una cita médica en el centro de salud"),
    ("sms", "La compañía eléctrica informa de que la factura está disponible en su área de clientes oficial"),
    ("whatsapp", "Un hijo o hija escribe desde su número de siempre para quedar a cenar o contar algo cotidiano"),
    ("whatsapp", "Una amiga comenta que le han intentado estafar y avisa de que tengan cuidado"),
    ("whatsapp", "Grupo de la familia organizando un cumpleaños y quién paga qué, sin urgencias"),
    ("llamada", "Transcripción de una llamada del gestor del banco recordando una cita en la oficina, sin pedir datos"),
    ("llamada", "Transcripción de un repartidor que llama porque está en la puerta con un paquete"),
    ("llamada", "Transcripción de una llamada al médico para cambiar una cita"),
    ("email", "El banco envía el extracto mensual y recuerda que nunca pide claves por correo"),
    ("email", "Confirmación de un pedido online con número de pedido y fecha de entrega"),
    ("email", "La Agencia Tributaria informa de que la declaración se ha presentado correctamente"),
    ("sms", "Promoción comercial legítima de un supermercado con descuentos en su app oficial"),
]

SCHEMA = {
    "type": "object",
    "properties": {"mensajes": {"type": "array", "items": {"type": "string"}, "minItems": 6, "maxItems": 10}},
    "required": ["mensajes"],
}

PROMPT = """Genera {n} ejemplos realistas y MUY distintos entre sí de {tipo} en español de España.
Canal: {canal}. Escenario: {escenario}.
Varía la longitud (de 1 a 5 frases), el tono, los importes, los nombres de empresas (usa nombres genéricos o inventados como "BancoSur", "Caja Levante", "EnvíaYa"), los dominios web y los números.
{extra}
Escribe solo el texto del mensaje o la transcripción, sin comillas ni explicaciones."""


def _gen(canal: str, escenario: str, n: int, seed: int, scam: bool) -> list[str]:
    tipo = "mensajes fraudulentos usados por estafadores" if scam else "mensajes LEGÍTIMOS y normales (no son estafas)"
    extra = ("Algunos con faltas de ortografía o mayúsculas, como los reales." if scam
             else "No incluyas enlaces raros, ni urgencias, ni peticiones de claves o dinero.")
    if canal == "llamada":
        extra += " Escribe la transcripción de lo que dice la persona que llama, en primera persona."
    prompt = PROMPT.format(n=n, tipo=tipo, canal=canal, escenario=escenario, extra=extra)
    data, _ = ollama_client.chat(config.OLLAMA_LLM, [{"role": "user", "content": prompt}], schema=SCHEMA,
                                 temperature=0.95, seed=seed, num_predict=1800)
    return [m.strip() for m in data.get("mensajes", []) if isinstance(m, str) and len(m.strip()) > 15]


def generate(out_csv: Path, calls_per_scam: int = 4, calls_per_legit: int = 5, n: int = 8, log=print) -> pd.DataFrame:
    """Genera el dataset y lo va guardando (se puede reanudar si se interrumpe)."""
    rows = pd.read_csv(out_csv).to_dict("records") if out_csv.exists() else []
    done = {(r["receta"], r["semilla"]) for r in rows}
    jobs = [(f"S{i}", c, e, tac, True) for i, (c, e, tac) in enumerate(SCAM_RECIPES) for _ in range(calls_per_scam)]
    jobs += [(f"L{i}", c, e, [], False) for i, (c, e) in enumerate(LEGIT_RECIPES) for _ in range(calls_per_legit)]
    seen_seeds: dict[str, int] = {}
    for k, (rid, canal, esc, tac, scam) in enumerate(jobs):
        seed = seen_seeds.get(rid, 0)
        seen_seeds[rid] = seed + 1
        if (rid, seed) in done:
            continue
        try:
            msgs = _gen(canal, esc, n, 1000 + seed, scam)
        except Exception as exc:
            log(f"  receta {rid} semilla {seed}: error {exc}")
            continue
        for m in msgs:
            row = {"texto": m, "canal": canal, "estafa": int(scam), "receta": rid, "semilla": seed, "origen": "sintetico_qwen3"}
            row.update({t: int(t in tac) for t in T})
            rows.append(row)
        pd.DataFrame(rows).to_csv(out_csv, index=False)
        log(f"[{k + 1}/{len(jobs)}] {rid} ({canal}) -> {len(msgs)} mensajes; total {len(rows)}")
    df = pd.DataFrame(rows)
    df["hash"] = df["texto"].str.lower().str.replace(r"\W+", "", regex=True).map(lambda s: hashlib.md5(s.encode()).hexdigest())
    df = df.drop_duplicates("hash").drop(columns="hash").reset_index(drop=True)
    df.to_csv(out_csv, index=False)
    return df


def load_sms_spam() -> pd.DataFrame:
    """UCI SMS Spam Collection (inglés): solo aporta la etiqueta binaria spam/no spam."""
    from huggingface_hub import hf_hub_download

    path = hf_hub_download("ucirvine/sms_spam", "plain_text/train-00000-of-00001.parquet", repo_type="dataset")
    df = pd.read_parquet(path)
    df = df.rename(columns={"sms": "texto", "label": "estafa"})
    df["texto"] = df["texto"].str.strip()
    df["canal"], df["receta"], df["semilla"], df["origen"] = "sms", "uci", 0, "uci_sms_spam"
    for t in T:
        df[t] = -1  # -1 = etiqueta desconocida (se enmascara en el entrenamiento)
    return df


def save_json(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
