"""Base de datos SQLite de casos analizados (consola del analista)."""

from __future__ import annotations

import random
import re
import sqlite3
import threading
from datetime import datetime, timedelta

import pandas as pd

from diputado import config
from diputado.core import campaigns

SCHEMA = """
CREATE TABLE IF NOT EXISTS casos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,              -- fecha y hora ISO 8601 (YYYY-MM-DD HH:MM:SS)
    canal TEXT NOT NULL,              -- llamada, sms, whatsapp, email, carta, web, texto
    nivel TEXT NOT NULL,              -- verde, ambar, rojo
    riesgo REAL NOT NULL,             -- probabilidad fusionada de estafa (0-1)
    campana TEXT,                     -- id de la campaña conocida más parecida (o NULL)
    entidad_suplantada TEXT,          -- banco, Correos, DGT, familiar...
    tacticas TEXT,                    -- tácticas separadas por comas
    dominio TEXT,                     -- dominio web sospechoso detectado
    telefono TEXT,                    -- teléfono enmascarado
    importe_eur REAL,                 -- importe que se pedía, en euros
    provincia TEXT,
    edad_cliente INTEGER,
    resumen TEXT,
    latencia_ms REAL,
    origen TEXT                       -- historico_sintetico o app
);
"""
SCHEMA_DOC = """Tabla casos (un registro por mensaje o llamada analizada):
- id INTEGER
- fecha TEXT 'YYYY-MM-DD HH:MM:SS' (usa date(fecha), strftime o date('now','-7 day'))
- canal TEXT: 'llamada','sms','whatsapp','email','carta','web','texto'
- nivel TEXT: 'verde','ambar','rojo'
- riesgo REAL entre 0 y 1
- campana TEXT: id de campaña (ej. 'correos_tasas','hola_mama','banco_llamada_spoofing','dgt_multa','cripto_famoso','bizum_inverso','soporte_tecnico','hacienda_devolucion') o NULL
- entidad_suplantada TEXT (ej. 'Correos','Banco','DGT','Familiar','Agencia Tributaria','Microsoft')
- tacticas TEXT separadas por comas (usa LIKE '%falso_familiar%')
- dominio TEXT, telefono TEXT, importe_eur REAL, provincia TEXT, edad_cliente INTEGER
- resumen TEXT, latencia_ms REAL, origen TEXT ('historico_sintetico','app')"""

PROVINCIAS = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Málaga", "Zaragoza", "Murcia", "Alicante", "Vizcaya", "A Coruña", "Asturias", "Granada"]
_lock = threading.Lock()


def connect(readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        con = sqlite3.connect(f"file:{config.CASES_DB.as_posix()}?mode=ro", uri=True, check_same_thread=False)
        con.execute("PRAGMA query_only = ON")
        return con
    config.CASES_DB.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(config.CASES_DB, check_same_thread=False)


def init(seed_rows: int = 450, rng_seed: int = 11) -> None:
    with _lock, connect() as con:
        con.executescript(SCHEMA)
        if con.execute("SELECT COUNT(*) FROM casos").fetchone()[0] == 0:
            con.executemany(_insert_sql(), _synthetic_history(seed_rows, rng_seed))


def _insert_sql() -> str:
    return ("INSERT INTO casos (fecha, canal, nivel, riesgo, campana, entidad_suplantada, tacticas, dominio, telefono, "
            "importe_eur, provincia, edad_cliente, resumen, latencia_ms, origen) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")


def _synthetic_history(n: int, seed: int) -> list[tuple]:
    """Histórico sintético verosímil para que la consola tenga datos que explorar."""
    rng = random.Random(seed)
    camps = campaigns.load()
    popularity = {"correos_tasas": 9, "banco_bloqueo": 8, "hola_mama": 7, "banco_llamada_spoofing": 7, "dgt_multa": 5,
                  "mensajeria_entrega": 5, "bizum_inverso": 4, "hacienda_devolucion": 3, "cripto_famoso": 3}
    weights = [popularity.get(c["id"], 2) for c in camps]
    now = datetime.now().replace(microsecond=0)
    rows = []
    for _ in range(n):
        ts = now - timedelta(days=rng.betavariate(1.2, 2.5) * 60, minutes=rng.randint(0, 1440))
        if rng.random() < 0.28:
            canal = rng.choice(["sms", "whatsapp", "email", "llamada"])
            risk = rng.uniform(0.02, 0.3)
            rows.append((ts.isoformat(sep=" "), canal, "verde", round(risk, 3), None, None, "", None, None, None,
                         rng.choice(PROVINCIAS), rng.randint(25, 88), "Mensaje legítimo verificado", rng.uniform(4000, 16000), "historico_sintetico"))
            continue
        c = rng.choices(camps, weights)[0]
        # Campañas "de moda": hola_mama y spoofing crecen en las dos últimas semanas.
        if c["id"] in ("hola_mama", "banco_llamada_spoofing") and (now - ts).days > 14 and rng.random() < 0.5:
            ts = now - timedelta(days=rng.uniform(0, 14))
        risk = rng.uniform(0.66, 0.99) if rng.random() < 0.85 else rng.uniform(0.38, 0.64)
        nivel = "rojo" if risk >= config.THRESHOLD_RED else "ambar"
        amount = None
        m = re.search(r"(\d+(?:\.\d{3})*(?:,\d{1,2})?)\s?(?:€|euros)", c["texto"])
        if m:
            amount = float(m.group(1).replace(".", "").replace(",", ".")) * rng.choice([1, 1, 1, 0.5, 2])
        dom = re.search(r"([a-z0-9-]+\.(?:top|info|com|online|vip|shop|xyz|live))", c["texto"])
        rows.append((ts.isoformat(sep=" "), c["canal"], nivel, round(risk, 3), c["id"], c["entidad"], ",".join(c["tacticas"]),
                     dom.group(1) if dom else None, f"+34 6** *** {rng.randint(100, 999)}", amount, rng.choice(PROVINCIAS),
                     int(min(92, max(18, rng.gauss(64, 14)))), c["nombre"], rng.uniform(6000, 24000), "historico_sintetico"))
    rows.sort(key=lambda r: r[0])
    return rows


def insert_case(row: dict) -> int:
    init()
    cols = ["fecha", "canal", "nivel", "riesgo", "campana", "entidad_suplantada", "tacticas", "dominio", "telefono",
            "importe_eur", "provincia", "edad_cliente", "resumen", "latencia_ms", "origen"]
    with _lock, connect() as con:
        cur = con.execute(_insert_sql(), tuple(row.get(c) for c in cols))
        return int(cur.lastrowid)


FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex)\b", re.I)


def safe_query(sql: str, limit: int = 200) -> pd.DataFrame:
    """Ejecuta SOLO consultas de lectura. Triple defensa: lista negra, conexión `mode=ro` y `query_only`."""
    sql = sql.strip().rstrip(";")
    if ";" in sql:
        raise ValueError("Solo se permite una única consulta")
    if not re.match(r"^\s*(select|with)\b", sql, re.I) or FORBIDDEN.search(sql):
        raise ValueError("Solo se permiten consultas SELECT de lectura")
    init()
    with connect(readonly=True) as con:
        df = pd.read_sql_query(sql, con)
    return df.head(limit)


def recent(limit: int = 15) -> pd.DataFrame:
    return safe_query(f"SELECT id, fecha, canal, nivel, riesgo, campana, entidad_suplantada, origen FROM casos ORDER BY fecha DESC LIMIT {int(limit)}")
