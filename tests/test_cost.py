from helios.analysis.cost import estimate_cost
from helios.config import Settings
from helios.types import StageLog


def test_local_cost_follows_watts_and_time():
    stage = StageLog("Infografía", "PIL", 3600, "ok", "ok")
    cost = estimate_cost([stage], Settings(hardware_watts=1000, electricity_eur_kwh=1.0), briefing_chars=0)
    assert cost["local_eur"] == 1
    assert cost["kwh"] == 1
