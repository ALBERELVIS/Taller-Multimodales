from pathlib import Path

from helios.orchestration.router import route_file


def test_router_separates_each_modality():
    assert route_file(Path("resultados.PDF")) == "pdf"
    assert route_file(Path("velas.png")) == "chart"
    assert route_file(Path("foto.JPEG")) == "chart"
    assert route_file(Path("llamada.mp3")) == "audio"
    assert route_file(Path("nota.wav")) == "audio"
    assert route_file(Path("precios.csv")) == "prices"
    assert route_file(Path("serie_price.csv")) == "prices"
    assert route_file(Path("noticias.json")) == "news"
    assert route_file(Path("recorte.txt")) == "news"
    assert route_file(Path("archivo.bin")) == "unknown"
