import sqlite3

import pytest

from diputado.core import cases_db


@pytest.mark.parametrize("sql", [
    "DELETE FROM casos",
    "DROP TABLE casos",
    "UPDATE casos SET nivel='verde'",
    "SELECT 1; DROP TABLE casos",
    "WITH x AS (SELECT 1) INSERT INTO casos(fecha) SELECT 1",
    "PRAGMA table_info(casos)",
    "ATTACH DATABASE 'otra.db' AS o",
])
def test_writes_are_rejected(temp_db, sql):
    cases_db.init(seed_rows=20)
    with pytest.raises(ValueError):
        cases_db.safe_query(sql)
    assert cases_db.safe_query("SELECT COUNT(*) AS n FROM casos")["n"][0] == 20


def test_select_works_and_is_limited(temp_db):
    cases_db.init(seed_rows=50)
    df = cases_db.safe_query("SELECT nivel, COUNT(*) AS n FROM casos GROUP BY nivel")
    assert set(df["nivel"]) <= {"verde", "ambar", "rojo"} and df["n"].sum() == 50
    assert len(cases_db.safe_query("SELECT * FROM casos", limit=7)) == 7


def test_readonly_connection_blocks_writes_even_without_blacklist(temp_db):
    cases_db.init(seed_rows=5)
    con = cases_db.connect(readonly=True)
    with pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM casos")
    con.close()


def test_insert_case_roundtrip(temp_db):
    cases_db.init(seed_rows=0)
    cid = cases_db.insert_case({"fecha": "2026-10-06 10:00:00", "canal": "sms", "nivel": "rojo", "riesgo": 0.97,
                                "origen": "app"})
    df = cases_db.safe_query(f"SELECT canal, nivel FROM casos WHERE id = {cid}")
    assert df.iloc[0].tolist() == ["sms", "rojo"]
