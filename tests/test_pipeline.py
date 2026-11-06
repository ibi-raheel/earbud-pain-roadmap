import json
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline import measure, prioritise, validate
from pipeline.text import sentences
from pipeline.themes import KEYS, NAIVE_RE, SEED_RE, match

ROOT = Path(__file__).resolve().parents[1]


# ---------- experiment sizing: checked by hand ----------
def test_n_per_arm_matches_hand_calculation():
    # p1 = 0.65, p2 = 0.85, alpha = 0.05 two-sided, power = 0.80
    # z = 1.959964 + 0.841621 = 2.801585 ; z^2 = 7.848879
    # var = 0.65*0.35 + 0.85*0.15 = 0.2275 + 0.1275 = 0.355 ; diff^2 = 0.04
    # n = 7.848879 * 0.355 / 0.04 = 69.66 -> 70
    assert prioritise.n_per_arm(0.65, 0.85) == 70
    assert ceil(7.848879 * 0.355 / 0.04) == 70


def test_n_per_arm_agrees_with_statsmodels_for_small_effects():
    for p1, p2 in [(0.20, 0.18), (0.15, 0.14), (0.30, 0.27)]:
        a = prioritise.n_per_arm(p1, p2)
        b = prioritise.n_per_arm_statsmodels(p1, p2)
        assert abs(a - b) / a < 0.03


def test_rice_formula():
    assert prioritise.rice(10, 0.5, 0.8, 2) == pytest.approx(2.0)
    assert set(prioritise.EFFORT_PM) == set(KEYS)


def test_effort_sensitivity_probabilities():
    th = [{"key": k, "rice": 1.0 + i, "effort_pm": 2.0} for i, k in enumerate(KEYS)]
    s = prioritise.effort_sensitivity(th, draws=2000)
    assert sum(v["p_first"] for v in s.values()) == pytest.approx(1.0)
    assert sum(v["p_top3"] for v in s.values()) == pytest.approx(3.0)
    assert s[KEYS[-1]]["p_first"] > s[KEYS[0]]["p_first"]


# ---------- text and lexicons ----------
def test_sentence_split_and_html():
    s = sentences("Great fit, very light.<br />Battery died after 2 months! ok")
    assert s == ["Great fit, very light.", "Battery died after 2 months!"]


def test_lexicons_cover_every_theme_and_fire():
    assert set(NAIVE_RE) == set(SEED_RE) == set(KEYS)
    assert "battery" in match(SEED_RE, "Battery only lasts 2 hours")
    assert "charging_case" in match(SEED_RE, "The case lid hinge snapped")
    assert "connectivity" in match(SEED_RE, "Left bud keeps disconnecting")
    assert match(NAIVE_RE, "they hurt my ears") == []  # the naive baseline misses this


@pytest.mark.parametrize("s,m", [
    ("stopped working after 3 months", 3.0),
    ("died after a year", 12.0),
    ("within two weeks the case broke", 14 / 30.44),
    ("love them", None),
])
def test_stated_months(s, m):
    v = measure.stated_months(s)
    assert (v is None and m is None) or v == pytest.approx(m)


# ---------- validation metrics: tiny example by hand ----------
def test_prf_by_hand():
    K = len(KEYS)
    Y = np.zeros((4, K), dtype=np.int8)
    P = np.zeros((4, K), dtype=np.int8)
    Y[0, 0] = Y[1, 0] = 1      # two true fit sentences
    P[0, 0] = P[2, 0] = 1      # one hit, one false alarm
    r = validate.prf(Y, P)["per_theme"]["fit_comfort"]
    assert r["precision"] == 0.5 and r["recall"] == 0.5 and r["f1"] == 0.5


def test_label_matrix_rejects_unknown_theme():
    assert validate.label_matrix(pd.Series(["battery;fit_comfort", "none"])).sum() == 2
    with pytest.raises(ValueError):
        validate.label_matrix(pd.Series(["batery"]))


# ---------- estimators recover planted effects on synthetic data ----------
def _synthetic(n_items=300, per=40, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_items):
        base = rng.normal(4.2, 0.4)  # item quality differs: fixed effect
        for _ in range(per):
            x = rng.random(len(KEYS)) < 0.1
            y = base - 1.0 * x[KEYS.index("battery")] - 0.3 * x[KEYS.index("fit_comfort")] + rng.normal(0, 0.5)
            rows.append([f"i{i}", y, int(rng.integers(50, 800))] + x.astype(int).tolist())
    return pd.DataFrame(rows, columns=["item", "stars", "n_chars"] + KEYS)


def test_star_impact_recovers_planted_coefficients():
    out = measure.star_impact(_synthetic())
    assert out.loc["battery", "coef"] == pytest.approx(-1.0, abs=0.05)
    assert out.loc["fit_comfort", "coef"] == pytest.approx(-0.3, abs=0.05)
    assert abs(out.loc["sound_quality", "coef"]) < 0.05
    assert out.loc["battery", "lo"] < -1.0 < out.loc["battery", "hi"]


def test_prevalence_ci_brackets_point():
    p = measure.prevalence(_synthetic(n_items=100, per=20))
    assert ((p["lo"] <= p["share"]) & (p["share"] <= p["hi"])).all()
    assert p.loc["battery", "share"] == pytest.approx(0.1, abs=0.02)


# ---------- shipped results are internally consistent ----------
RES = ROOT / "public" / "results.json"


@pytest.mark.skipif(not RES.exists(), reason="run the pipeline first")
def test_results_json_consistent():
    r = json.loads(RES.read_text())
    th = r["themes"]
    assert [t["rank"] for t in th] == list(range(1, len(KEYS) + 1))
    assert all(0 <= t["share_lo"] <= t["share"] <= t["share_hi"] <= 1 for t in th)
    assert [t["rice"] for t in th] == sorted([t["rice"] for t in th], reverse=True)
    e = r["experiment"]
    assert e["n_per_arm_formula"] == prioritise.n_per_arm(e["baseline_p1"], e["target_p2"])
    assert abs(e["n_per_arm_formula"] - e["n_per_arm_statsmodels"]) / e["n_per_arm_formula"] < 0.03
    m = r["validation"]["methods"]
    assert m[r["validation"]["chosen"]]["micro"]["f1"] > m["keyword_baseline"]["micro"]["f1"]
