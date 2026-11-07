"""Field-pain triage: one product's reviews or tickets in, a ranked fix queue out.

    python -I run.py triage <reviews.jsonl | scored.pkl> [--effort effort.json] [--efficacy 0.5]
                            [--out triage/] [--labels labels.csv] [--models models.pkl] [--sample N]

A thin wrapper over the existing pipeline (no new modelling):
  prepare.prepare_frame -> classify.score -> classify.pain_matrix -> assemble.theme_table -> decide

Input JSONL, one object per line, in the dataset's own review format:
  {"parent_asin", "user_id", "rating" (1-5 or any 1-5 outcome score), "timestamp" (ms), "title", "text"}
A support or return export only needs mapping to these six fields.

Thresholds (t_theme, t_neg) and per-theme confidence come from the public run's validation in
public/results.json unless --labels points at a hand-label CSV (columns text, labels, split),
in which case validate.evaluate re-tunes them on that file's dev split.

Writes <out>/triage.json (the results.json `themes` schema plus decision fields) and
<out>/triage.md (a one-page ranked queue).
"""
import argparse
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):  # run as a script: python -I pipeline/triage.py ...
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline import assemble, measure, validate  # noqa: E402
    from pipeline.classify import pain_matrix, score  # noqa: E402
    from pipeline.prepare import load_jsonl, prepare_frame  # noqa: E402
    from pipeline.themes import KEYS, LABELS  # noqa: E402
else:
    from . import assemble, measure, validate
    from .classify import pain_matrix, score
    from .prepare import load_jsonl, prepare_frame
    from .themes import KEYS, LABELS

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "public" / "results.json"

# ---- decision rules (thresholds are stated in SOLUTION.md) ----
FIX_FIRST_RANK = 3          # RICE top 3 ...
FIX_FIRST_STABILITY = 0.80  # ... and in the top 3 in at least 80% of effort draws
GATE_AGE_RATIO = 1.5        # share at 24+ months >= 1.5x share at 0-3 months, star CI below 0
VERIFY_PRECISION = 0.45     # detector precision under this -> check by hand before acting

FIX_FIRST, GATE, NON_GOAL, WATCH = "FIX FIRST", "GATE BEFORE LAUNCH", "NON-GOAL", "WATCH"

# How a fix would ship, and so how it is proved. An engineering ASSUMPTION per theme, like Effort.
FIX_PATH = {
    "fit_comfort": "hardware", "battery": "hardware", "charging_case": "hardware",
    "connectivity": "firmware", "sound_quality": "firmware", "anc_noise": "hardware",
    "call_mic": "hardware", "controls": "firmware", "failure": "hardware", "app_software": "firmware",
}
TEST_FOR = {"firmware": "OTA holdout", "hardware": "build cohort"}


def age_ratio(t: dict):
    first, last = t["lifecycle"][0], t["lifecycle"][-1]
    if first is None or last is None or not first > 0 or math.isnan(last):
        return None
    return last / first


def decide(themes: list) -> list:
    """Adds decision (list of labels), verify, age_ratio, fix_path and test to each theme.
    `themes` must be ranked and carry effort_sensitivity (as theme_table returns)."""
    for t in themes:
        r = age_ratio(t)
        labels = []
        if t["star_delta_hi"] >= 0:
            labels = [NON_GOAL]  # star CI includes 0 or is positive: no measurable cost
        else:
            if t["rank"] <= FIX_FIRST_RANK and t["effort_sensitivity"]["p_top3"] >= FIX_FIRST_STABILITY:
                labels.append(FIX_FIRST)
            if r is not None and r >= GATE_AGE_RATIO:
                labels.append(GATE)
            if not labels:
                labels = [WATCH]
        path = FIX_PATH[t["key"]]
        t.update({"decision": labels, "verify": bool(t["precision"] < VERIFY_PRECISION),
                  "age_ratio": r, "fix_path": path, "test": TEST_FOR[path]})
    return themes


def triage_scored(R: pd.DataFrame, S: pd.DataFrame, P: np.ndarray, pneg: np.ndarray,
                  t_theme: float, t_neg: float, per_theme: dict,
                  effort: dict = None, efficacy: float = 0.5) -> dict:
    """Core: scored sentences in, decided theme table out."""
    pain = pain_matrix(P, pneg, t_theme, t_neg)
    R = assemble.review_pain(R, S, pain)
    tab = assemble.theme_table(R, S, pain, per_theme, effort=effort, efficacy=efficacy)
    return {"overall": {"reviews": int(len(R)), "items": int(R["item"].nunique()),
                        "low_star_share": tab["p1"], "efficacy_assumption": efficacy,
                        "t_theme": t_theme, "t_neg": t_neg},
            "lifecycle_bins": measure.LIFE_LABELS,
            "rules": {"fix_first_rank": FIX_FIRST_RANK, "fix_first_stability": FIX_FIRST_STABILITY,
                      "gate_age_ratio": GATE_AGE_RATIO, "verify_precision": VERIFY_PRECISION},
            "themes": decide(tab["themes"])}


def public_validation(results: Path = RESULTS) -> tuple:
    v = json.loads(Path(results).read_text())["validation"]
    return v["t_theme"], v["t_neg"], v["methods"][v["chosen"]]["per_theme"]


def _score_with(models: dict, texts: list) -> tuple:
    X = models["vec"].transform(texts)
    P = np.column_stack([m.predict_proba(X)[:, 1] for m in models["theme"]])
    return P, models["neg"].predict_proba(X)[:, 1]


def triage(src: Path, effort: dict = None, efficacy: float = 0.5, labels: Path = None,
           models_path: Path = None, n_sample: int = None, results: Path = RESULTS) -> dict:
    src = Path(src)
    models = None
    if src.suffix == ".pkl":  # cached output of `run.py score`
        d = pickle.load(open(src, "rb"))
        R, S, P, pneg = d["R"], d["S"], d["P"], d["pneg"]
    else:
        d = prepare_frame(load_jsonl(src), n_sample)
        R, S = d["reviews"], d["sentences"]
        if models_path and Path(models_path).exists():  # reuse a vectorizer + models (small inputs)
            models = pickle.load(open(models_path, "rb"))
            P, pneg = _score_with(models, S["text"].tolist())
        else:
            P, pneg, _, vec, theme_models, neg_model = score(S, R.set_index("rid")["stars"])
            models = {"vec": vec, "theme": theme_models, "neg": neg_model}
            if models_path:
                pickle.dump(models, open(models_path, "wb"))
    if labels:
        if models is None:
            raise SystemExit("--labels needs models: pass a .jsonl input (and optionally --models)")
        H = pd.read_csv(labels)
        Hp, Hn = _score_with(models, H["text"].astype(str).tolist())
        Y = validate.label_matrix(H["labels"])
        dev = (H["split"] == "dev").to_numpy()
        t_theme, t_neg, _ = validate.tune(Y[dev], Hp[dev], Hn[dev])  # tuned on dev only
        per_theme = validate.prf(Y[~dev], pain_matrix(Hp[~dev], Hn[~dev], t_theme, t_neg))["per_theme"]
    else:
        t_theme, t_neg, per_theme = public_validation(results)
    return triage_scored(R, S, P, pneg, t_theme, t_neg, per_theme, effort, efficacy)


# ---------- output ----------
def _clean(o):
    if isinstance(o, float) and math.isnan(o):
        return None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        return _clean(float(o))
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def _pct(x):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f}%"


def render_md(out: dict) -> str:
    o = out["overall"]
    lines = [
        "# Field-pain triage: ranked fix queue", "",
        f"{o['reviews']:,} reviews of {o['items']:,} products. Baseline 1-2 star share "
        f"{_pct(o['low_star_share'])}. Fix efficacy assumed {o['efficacy_assumption']:.0%}.", "",
        "| Rank | Pain | Decision | Reach (95% CI) | Stars lost (95% CI) | Age trend 0-3 mo -> 24+ mo "
        "| RICE | Top-3 stability | Test | n per arm |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t in out["themes"]:
        dec = " + ".join(t["decision"]) + (" (verify)" if t["verify"] else "")
        n = t["experiment_n_per_arm"]
        test = "none" if NON_GOAL in t["decision"] else t["test"]
        n_txt = "n/a" if (n is None or NON_GOAL in t["decision"]) else f"{n:,}"
        lines.append(
            f"| {t['rank']} | {t['label']} | {dec} | {_pct(t['share'])} ({_pct(t['share_lo'])} to {_pct(t['share_hi'])}) "
            f"| {t['star_delta']:+.2f} ({t['star_delta_lo']:+.2f} to {t['star_delta_hi']:+.2f}) "
            f"| {_pct(t['lifecycle'][0])} -> {_pct(t['lifecycle'][-1])} | {t['rice']:.2f} "
            f"| {t['effort_sensitivity']['p_top3']:.1%} | {test} | {n_txt} |")
    r = out["rules"]
    lines += ["", "**Rules.** FIX FIRST: RICE rank <= %d and in the top 3 in >= %d%% of effort draws. "
              "GATE BEFORE LAUNCH: share at 24+ months >= %.1fx the share at 0-3 months, with the star CI "
              "below 0. NON-GOAL: star CI includes 0 or is positive. WATCH: everything else. "
              "(verify): detector precision under %.2f; check a sample by hand before acting."
              % (r["fix_first_rank"], round(100 * r["fix_first_stability"]), r["gate_age_ratio"], r["verify_precision"]),
              "", "Effort and fix efficacy are assumptions; test type follows from whether the fix ships as "
              "firmware (OTA holdout) or hardware (build cohort)."]
    return "\n".join(lines) + "\n"


def write(out: dict, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "triage.json").write_text(json.dumps(_clean(out), indent=1, default=float))
    (out_dir / "triage.md").write_text(render_md(out))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="run.py triage", description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path, help="reviews JSONL, or a scored.pkl from `run.py score`")
    ap.add_argument("--effort", type=Path, help="JSON {theme: person-months} overriding the assumed Effort")
    ap.add_argument("--efficacy", type=float, default=0.5, help="assumed fix efficacy (default 0.5)")
    ap.add_argument("--out", type=Path, default=Path("triage"))
    ap.add_argument("--labels", type=Path, help="hand-label CSV (text, labels, split) to re-tune thresholds")
    ap.add_argument("--models", type=Path, help="reuse (or save) vectorizer + models; useful for small inputs")
    ap.add_argument("--sample", type=int, default=None, help="random sample of N reviews (default: all)")
    a = ap.parse_args(argv)
    effort = json.loads(a.effort.read_text()) if a.effort else None
    if effort and set(effort) - set(KEYS):
        raise SystemExit(f"unknown themes in --effort: {sorted(set(effort) - set(KEYS))}")
    out = triage(a.src, effort, a.efficacy, a.labels, a.models, a.sample)
    write(out, a.out)
    for t in out["themes"]:
        print(f"{t['rank']:>2}  {LABELS[t['key']]:<36} {' + '.join(t['decision'])}{' (verify)' if t['verify'] else ''}")
    print(f"wrote {a.out / 'triage.json'} and {a.out / 'triage.md'}")


if __name__ == "__main__":
    main()
