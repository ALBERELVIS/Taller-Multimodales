from helios.analysis.index import rank_texts
from helios.analysis.textutil import keyword_hit_rate, wer
from helios.types import TextChunk


def test_lexical_search_finds_cabo_prior():
    chunks = [
        TextChunk("a", "news", "Cabo", "Retraso del permiso de Cabo Prior y del capex.", "Noticia: Cabo"),
        TextChunk("b", "pdf", "Balance", "La deuda neta del grupo se mantiene estable.", "PDF p.1"),
    ]
    hits = rank_texts(chunks, "¿Qué pasa con el permiso de Cabo Prior?", k=1)
    assert hits[0].title == "Cabo"
    assert hits[0].mode == "lexico"


def test_wer_is_zero_on_the_same_script_and_one_on_an_empty_guess():
    script = "ingresos de 842 millones"
    assert wer(script, script) == 0
    assert wer(script, "") == 1
    assert keyword_hit_rate("El permiso de Cabo Prior y el capex", ["cabo prior", "capex", "margen"]) == 2 / 3
