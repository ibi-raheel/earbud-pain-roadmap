"""The triage tool: decision rules on the shipped results, and end-to-end runs on real data."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pipeline import triage
from pipeline.themes import KEYS

ROOT = Path(__file__).resolve().parents[1]
RES = json.loads((ROOT / "public" / "results.json").read_text())
RAW = Path(os.environ.get("EARBUD_RAW", ROOT.parent / "_downloads" / "earbud-pain-roadmap"))
SCORED = RAW / "interim" / "scored.pkl"


def _by_key(themes):
    return {t["key"]: t for t in themes}


def test_decisions_on_shipped_results():
    th = _by_key(triage.decide(copy.deepcopy(RES["themes"])))
    assert th["sound_quality"]["decision"] == [triage.FIX_FIRST] and th["sound_quality"]["verify"]
    assert th["connectivity"]["decision"] == [triage.FIX_FIRST] and th["connectivity"]["test"] == "OTA holdout"
    assert th["failure"]["decision"] == [triage.FIX_FIRST, triage.GATE]
    assert th["failure"]["test"] == "build cohort"
    assert th["failure"]["age_ratio"] == pytest.approx(0.1358 / 0.0587, rel=0.01)
    for k in ("controls", "anc_noise", "app_software"):
        assert th[k]["decision"] == [triage.NON_GOAL]
    for k in ("fit_comfort", "battery", "charging_case", "call_mic"):
        assert th[k]["decision"] == [triage.WATCH]
    md = triage.render_md({"overall": {"reviews": RES["dataset"]["sample_reviews"],
                                       "items": RES["dataset"]["sample_items"],
                                       "low_star_share": RES["overall"]["low_star_share"],
                                       "efficacy_assumption": 0.5},
                           "rules": {"fix_first_rank": 3, "fix_first_stability": 0.8,
                                     "gate_age_ratio": 1.5, "verify_precision": 0.45},
                           "themes": list(th.values())})
    assert "FIX FIRST + GATE BEFORE LAUNCH" in md and "12,487" in md


@pytest.mark.skipif(not SCORED.exists(), reason="needs the cached public scoring (run.py score)")
def test_triage_reproduces_public_run(tmp_path):
    out = triage.triage(SCORED)
    got, want = out["themes"], RES["themes"]
    assert [t["key"] for t in got] == [t["key"] for t in want]
    assert [t["experiment_n_per_arm"] for t in got] == [t["experiment_n_per_arm"] for t in want]
    assert [t["rice"] for t in got] == pytest.approx([t["rice"] for t in want])
    th = _by_key(got)
    assert triage.GATE in th["failure"]["decision"]
    assert all(th[k]["decision"] == [triage.NON_GOAL] for k in ("controls", "anc_noise", "app_software"))
    triage.write(out, tmp_path)
    assert json.loads((tmp_path / "triage.json").read_text())["themes"][0]["key"] == "sound_quality"


@pytest.mark.skipif(not (RAW / "reviews_earbuds.jsonl").exists(), reason="needs the public review download")
def test_cli_on_real_review_slice(tmp_path):
    src = tmp_path / "slice.jsonl"
    with open(RAW / "reviews_earbuds.jsonl") as f, open(src, "w") as g:
        for i, line in enumerate(f):
            if i >= 20_000:
                break
            g.write(line)
    effort = tmp_path / "effort.json"
    effort.write_text(json.dumps({"connectivity": 1.5}))
    r = subprocess.run([sys.executable, "-I", str(ROOT / "run.py"), "triage", str(src), "--effort", str(effort),
                        "--out", str(tmp_path / "out")], capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    out = json.loads((tmp_path / "out" / "triage.json").read_text())
    assert sorted(t["key"] for t in out["themes"]) == sorted(KEYS)
    assert [t["rank"] for t in out["themes"]] == list(range(1, len(KEYS) + 1))
    allowed = {triage.FIX_FIRST, triage.GATE, triage.NON_GOAL, triage.WATCH}
    assert all(set(t["decision"]) <= allowed and t["decision"] for t in out["themes"])
    assert _by_key(out["themes"])["connectivity"]["effort_pm"] == 1.5
    assert out["overall"]["reviews"] > 1000
    assert "| Rank | Pain | Decision |" in (tmp_path / "out" / "triage.md").read_text()
