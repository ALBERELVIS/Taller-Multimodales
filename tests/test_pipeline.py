"""La mesa demo publica solo cifras que están en las fuentes."""

from dataclasses import replace
from pathlib import Path

import pytest

from helios.config import Settings
from helios.demo.case import load_demo_case
from helios.orchestration.pipeline import run_analysis

CASE = Path(__file__).resolve().parents[1] / "data" / "samples" / "nortegrid"


@pytest.mark.skipif(not (CASE / "resultados.pdf").exists(), reason="Caso demo aún no generado")
def test_offline_mesa_keeps_every_published_number():
    settings = replace(Settings.from_env(), tts_mode="off", cache_enabled=False)
    result = run_analysis(load_demo_case(), settings=settings, use_models=False, use_cache=False)
    assert result.fact_sheet.company == "NorteGrid"
    assert result.fact_sheet.stance == "Vigilar"
    assert result.fact_sheet.metrics["ingresos_2025_m"] == 842
    assert result.published_support_ratio == 1.0
    assert result.infographic_path
    assert Path(result.infographic_path).exists()
    assert "842" in result.thesis
    assert result.briefing_script
    names = [stage.name for stage in result.stages]
    assert "Lectura del PDF" in names
    assert "Control de cifras" in names
    assert "Infografía" in names
