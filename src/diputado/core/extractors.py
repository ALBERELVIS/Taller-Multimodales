"""Extractores deterministas de señales de fraude y enmascarado de datos personales.

Son reglas transparentes y auditables: complementan a los modelos y nos permiten
aplicar "reglas duras" (por ejemplo, cualquier petición de PIN es roja).
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

from rapidfuzz import fuzz

OFFICIAL_DOMAINS = [
    "correos.es", "dgt.es", "agenciatributaria.gob.es", "seg-social.es", "sede.gob.es",
    "bancosantander.es", "bbva.es", "caixabank.es", "bancosabadell.com", "ing.es", "unicajabanco.es",
    "openbank.es", "kutxabank.es", "ibercaja.es", "abanca.com", "bankinter.com",
    "endesa.com", "iberdrola.es", "naturgy.es", "netflix.com", "amazon.es", "dhl.com", "seur.com",
    "gls-spain.es", "mrw.es", "bizum.es", "cnmv.es", "bde.es", "wallapop.com", "microsoft.com",
]
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "rb.gy", "shorturl.at", "goo.su", "t.ly", "ow.ly"}
RISKY_TLDS = {"top", "xyz", "info", "click", "shop", "live", "icu", "vip", "cc", "online", "site", "buzz", "store", "app", "link", "life"}
REMOTE_APPS = ["anydesk", "teamviewer", "rustdesk", "quicksupport", "ultraviewer", "supremo"]

URL_RE = re.compile(r"(?:https?://)?(?:www\.)?((?:[a-z0-9-]+\.)+[a-z]{2,10})(/[^\s]*)?", re.I)
PHONE_RE = re.compile(r"(?:\+34[\s.-]?)?(?:[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}|[6789]\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2})")
IBAN_RE = re.compile(r"\bES\d{2}(?:[\s-]?\d{4}){5}\b", re.I)
AMOUNT_RE = re.compile(r"(\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)\s?(?:€|euros?\b|eur\b)", re.I)
DNI_RE = re.compile(r"\b\d{8}[A-HJ-NP-TV-Z]\b")
CARD_RE = re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b")

PATTERNS = {
    "pide_codigo": r"(c[oó]digo|clave|pin|contraseña|cvv|otp|coordenadas)\b.{0,60}\b(d[ií]ga|dime|facilit|indiqu|envi|dict|confirm|comparta|necesit)"
                   r"|(d[ií]ga|dime|facilit|indiqu|envi|dict|confirm|necesit).{0,60}\b(c[oó]digo|clave|pin|contraseña|cvv)\b",
    "urgencia": r"\b(urgente|inmediat|hoy mismo|en las pr[oó]ximas \d+ ?h|24 ?h|48 ?h|antes de que|bloquead|suspendid|cancelad|[uú]ltimo aviso|caduca)",
    "pago": r"\b(transferencia|bizum|pague|abone|ingrese|tasa|importe pendiente|pago pendiente|env[ií]a(me)? dinero|hazme un|cuenta segura)",
    "familiar": r"\b(hola (mam[aá]|pap[aá])|este es mi (nuevo )?n[uú]mero|se me ha (roto|ca[ií]do) el m[oó]vil|mi m[oó]vil nuevo|soy tu hij[oa])",
    "premio": r"\b(premio|ganador|has ganado|herencia|sorteo|rentabilidad|garantizad|invierte|criptomoneda|bitcoin|duplica)",
    "remoto": r"\b(" + "|".join(REMOTE_APPS) + r")\b",
}
# Avisos típicos de mensajes legítimos ("no lo compartas con nadie"): desactivan la
# regla de petición de código para no marcar como estafa un OTP que pidió el usuario.
DISCLAIMER = r"(no (lo |la |se lo |te lo )?(compartas|comparta|facilites|facilite|digas|diga)|nunca te (pediremos|llamaremos|solicitaremos)|nunca (le )?(pediremos|solicitaremos|pedimos))"

HUMAN_FLAGS = {
    "pide_codigo": "Pide un código, PIN o contraseña",
    "urgencia": "Mete prisa o amenaza con bloqueos",
    "pago": "Pide un pago o una transferencia",
    "familiar": "Alguien dice ser un familiar con número nuevo",
    "premio": "Promete premios o rentabilidades",
    "remoto": "Pide instalar una app de control remoto",
    "acortador": "Usa un enlace acortado que oculta el destino",
    "dominio_imitado": "El enlace imita la web oficial",
    "tld_riesgo": "El enlace usa una terminación de web poco fiable",
    "iban": "Incluye un número de cuenta para enviar dinero",
}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def find_domains(text: str) -> list[str]:
    out = []
    for m in URL_RE.finditer(text):
        dom = m.group(1).lower().strip(".")
        if re.fullmatch(r"[\d.]+", dom) or "." not in dom:
            continue
        if dom.split(".")[-1] in {"jpg", "png", "pdf", "mp3", "wav"}:
            continue
        out.append(dom)
    return list(dict.fromkeys(out))


def domain_risk(domain: str) -> dict:
    d = domain.lower().removeprefix("www.")
    official = next((o for o in OFFICIAL_DOMAINS if d == o or d.endswith("." + o)), None)
    if official:
        return {"domain": d, "official": True, "lookalike_of": None, "shortener": False, "risky_tld": False}
    base = d.split(".")[-2] if d.count(".") >= 1 else d
    best, best_score = None, 0.0
    for o in OFFICIAL_DOMAINS:
        brand = o.split(".")[0]
        score = max(fuzz.ratio(base, brand), fuzz.partial_ratio(brand, d) if len(brand) >= 4 else 0)
        if score > best_score:
            best, best_score = o, score
    return {
        "domain": d,
        "official": False,
        "lookalike_of": best if best_score >= 80 else None,
        "shortener": d in SHORTENERS,
        "risky_tld": d.split(".")[-1] in RISKY_TLDS,
    }


def extract(text: str, extra_links: list[str] | None = None, extra_phones: list[str] | None = None) -> dict:
    text = text or ""
    low = _strip_accents(text.lower())
    domains = find_domains(text + " " + " ".join(extra_links or []))
    dom_info = [domain_risk(d) for d in domains]
    flags = {name: bool(re.search(_strip_accents(pat), low)) for name, pat in PATTERNS.items()}
    disclaimer = bool(re.search(DISCLAIMER, low))
    if disclaimer:
        flags["pide_codigo"] = False
    flags["acortador"] = any(d["shortener"] for d in dom_info)
    flags["dominio_imitado"] = any(d["lookalike_of"] for d in dom_info)
    flags["tld_riesgo"] = any(d["risky_tld"] for d in dom_info)
    ibans = IBAN_RE.findall(text)
    flags["iban"] = bool(ibans)
    phones = list(dict.fromkeys(PHONE_RE.findall(text) + list(extra_phones or [])))
    amounts = [m.group(0) for m in AMOUNT_RE.finditer(text)]
    weights = {"pide_codigo": 0.35, "remoto": 0.35, "dominio_imitado": 0.3, "familiar": 0.25, "acortador": 0.2,
               "pago": 0.15, "urgencia": 0.15, "tld_riesgo": 0.15, "premio": 0.15, "iban": 0.15}
    score = min(1.0, sum(w for k, w in weights.items() if flags.get(k)))
    return {
        "flags": flags,
        "flags_humanos": [HUMAN_FLAGS[k] for k, v in flags.items() if v],
        "dominios": dom_info,
        "telefonos": phones,
        "ibans": ibans,
        "importes": amounts,
        "red_flag_score": score,
        "aviso_legitimo": disclaimer,
        "hard_rule": flags["pide_codigo"] or flags["remoto"],
    }


def mask_pii(text: str) -> str:
    """Enmascara IBAN, tarjetas, DNI y teléfonos antes de guardar o registrar nada."""
    text = IBAN_RE.sub(lambda m: m.group(0)[:4] + " **** **** " + m.group(0)[-4:], text)
    text = CARD_RE.sub(lambda m: "**** **** **** " + m.group(0)[-4:], text)
    text = DNI_RE.sub("********X", text)
    text = PHONE_RE.sub(lambda m: re.sub(r"\d(?=(?:\D*\d){2})", "*", m.group(0)), text)
    return text
