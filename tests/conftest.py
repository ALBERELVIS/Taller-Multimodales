import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    from diputado import config

    monkeypatch.setattr(config, "CASES_DB", tmp_path / "casos.sqlite")
    return config.CASES_DB
