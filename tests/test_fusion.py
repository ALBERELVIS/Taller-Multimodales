import math

import pytest

from diputado import config
from diputado.core import fusion

PARAMS = {"bias": 0.0, "weights": {"tacticnet": 1.0, "llm": 1.0, "campana": 0.5, "reglas": 0.5, "voz": 0.5, "acustica": 0.5},
          "source": "test"}


def test_missing_signals_are_neutral():
    r = fusion.fuse({"tacticnet": None, "llm": None}, params=PARAMS)
    assert r.risk == pytest.approx(0.5)
    assert r.contributions == {}


def test_contributions_sum_to_logit_of_risk():
    sig = {"tacticnet": 0.9, "llm": 0.8, "campana": 0.3, "reglas": 0.6}
    r = fusion.fuse(sig, params=PARAMS)
    z = math.log(r.risk / (1 - r.risk))
    assert sum(r.contributions.values()) + PARAMS["bias"] == pytest.approx(z, abs=1e-6)


def test_levels_follow_thresholds():
    assert fusion.level_for(config.THRESHOLD_RED) == "rojo"
    assert fusion.level_for(config.THRESHOLD_AMBER) == "ambar"
    assert fusion.level_for(config.THRESHOLD_AMBER - 1e-3) == "verde"


def test_monotonic_in_each_signal():
    base = {"tacticnet": 0.5, "llm": 0.5, "reglas": 0.5}
    prev = 0.0
    for p in (0.05, 0.3, 0.5, 0.7, 0.95):
        r = fusion.fuse({**base, "llm": p}, params=PARAMS).risk
        assert r > prev
        prev = r


def test_amplifiers_can_only_raise_risk():
    base = {"tacticnet": 0.8, "llm": 0.8}
    r0 = fusion.fuse(base, params=PARAMS).risk
    natural_voice = fusion.fuse({**base, "voz": 0.01}, params=PARAMS)
    synthetic_voice = fusion.fuse({**base, "voz": 0.99}, params=PARAMS)
    assert natural_voice.risk == pytest.approx(r0)
    assert synthetic_voice.risk > r0


def test_hard_rule_needs_model_agreement():
    low = {"tacticnet": 0.1, "llm": 0.1, "reglas": 0.3}
    assert not fusion.fuse(low, hard_rule=True, params=PARAMS).hard_rule
    agree = {"tacticnet": 0.6, "llm": 0.2, "reglas": 0.3}
    r = fusion.fuse(agree, hard_rule=True, params=PARAMS)
    assert r.hard_rule and r.risk >= 0.9 and r.level == "rojo"


def test_logit_is_clipped():
    assert math.isfinite(fusion.logit(0.0)) and math.isfinite(fusion.logit(1.0))
