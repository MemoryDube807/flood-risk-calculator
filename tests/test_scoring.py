import json
import os

import pytest

from floodsense import scoring

CLIM = {"rl2": 56.0, "api90": 92.5, "q2": 7.4}


def test_dry_day_is_low():
    r = scoring.hazard_score(0, 0, 0, CLIM)
    assert r["score"] == 0 and r["level"] == "LOW"


def test_every_factor_at_its_cap_gives_100():
    r = scoring.hazard_score(CLIM["rl2"] * 1.5, CLIM["api90"] * 1.5, CLIM["q2"] * 2, CLIM)
    assert r["score"] == 100


def test_factors_are_capped():
    a = scoring.hazard_score(CLIM["rl2"] * 1.5, 0, 0, CLIM)["score"]
    b = scoring.hazard_score(CLIM["rl2"] * 5, 0, 0, CLIM)["score"]
    assert a == b == 50


def test_more_rain_never_lowers_the_score():
    scores = [scoring.hazard_score(r, 40, 2, CLIM)["score"] for r in range(0, 120, 5)]
    assert scores == sorted(scores)


def test_no_river_share_follows_wetness():
    clim = {**CLIM, "q2": 0.2}                     # tiny channel: not a river
    r = scoring.hazard_score(0, CLIM["api90"] * 1.5, 50, clim)
    assert not r["has_river"]
    assert r["points"]["river"] == r["points"]["wetness"] * 0.2 / 0.3


def test_thresholds():
    assert scoring.level(34.9) == "LOW"
    assert scoring.level(35) == "MODERATE"
    assert scoring.level(50) == "HIGH"


def test_exposure_raises_risk_for_low_poorly_drained_ground():
    low = scoring.assess(40, 80, None, CLIM, rel_height_m=2, drainage="poor")
    high = scoring.assess(40, 80, None, CLIM, rel_height_m=40, drainage="good")
    assert low["score"] == high["score"]           # hazard is the same
    assert low["risk"] > high["risk"]


def test_antecedent_index_weights_recent_days_most():
    assert scoring.antecedent_index([10, 0, 0]) < scoring.antecedent_index([0, 0, 10])
    assert scoring.antecedent_index([0, 0, 10]) == 10


def test_climatology_on_a_synthetic_series():
    dates, rain = [], []
    from datetime import date, timedelta
    d = date(1991, 1, 1)
    while d.year < 2020:
        dates.append(d.isoformat())
        rain.append(30.0 if (d.month, d.day) == (1, 15) else 0.0)
        d += timedelta(days=1)
    c = scoring.rain_climatology(dates, rain)
    assert c["rl2"] == 30.0


@pytest.mark.skipif(not os.path.exists("data/backtest_results.json"), reason="run scripts/backtest.py first")
def test_backtest_headline_numbers():
    with open("data/backtest_results.json") as f:
        s = json.load(f)["summary"]
    assert s["caught_moderate"] >= s["caught_high"]
    assert s["caught_moderate_outside_lusaka"] == s["n_outside_lusaka"]
