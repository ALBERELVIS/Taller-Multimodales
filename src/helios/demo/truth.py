"""Verdad terreno del caso sintético NorteGrid.

El PDF, las noticias, el guion y la evaluación importan estas constantes
para que las cifras no puedan desviarse entre módulos.
"""

COMPANY = "NorteGrid"
TICKER = "NRGX"
CURRENCY = "EUR"

FIELDS: dict[str, float] = {
    "ingresos_2025_m": 842.0,
    "ebitda_2025_m": 239.0,
    "margen_ebitda_pct": 28.4,
    "capex_2025_m": 310.0,
    "deuda_neta_m": 540.0,
    "guidance_baja_m": 910.0,
    "guidance_alta_m": 940.0,
    "retraso_permiso_meses": 6.0,
}

RISK_TEXT = "Retraso de 6 meses en el permiso del parque eólico de Cabo Prior."

TRANSCRIPT_KEYWORDS = ["842", "margen", "capex", "cabo prior", "540"]

EARNINGS_SCRIPT = (
    "Buenos días. Habla la dirección financiera de NorteGrid. "
    "En dos mil veinticinco los ingresos alcanzaron 842 millones de euros. "
    "El EBITDA fue de 239 millones de euros, con un margen del 28,4 por ciento. "
    "El capex del ejercicio ascendió a 310 millones de euros y la deuda neta cerró en 540 millones. "
    "La guía de ingresos para dos mil veintiséis se sitúa entre 910 y 940 millones de euros. "
    "El riesgo principal es un retraso de seis meses en el permiso del parque eólico de Cabo Prior. "
    "Ese retraso puede desplazar parte del capex ya comunicado. "
    "Mantendremos la disciplina de balance y avisaremos al mercado si el permiso cambia de calendario. "
    "Gracias por su atención."
)

CHART_PATTERN = (
    "Caída plantada de aproximadamente el 18% entre las sesiones 180 y 200, "
    "seguida de una recuperación parcial. Los precios son sintéticos."
)
