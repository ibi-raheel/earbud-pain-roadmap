"""Pipeline entry point.

  python -I -m pipeline.run_all score   RAW_DIR   # prepare + models, cache to data/interim
  python -I -m pipeline.run_all sample            # write the hand-label sample (text stays local)
  python -I -m pipeline.run_all export            # validate, measure, prioritise -> public/results.json
"""
import json
import pickle
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import measure, prioritise, topics, validate
from .classify import pain_matrix, score
from .prepare import prepare
from .themes import KEYS, LABELS

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "public" / "results.json"


def stage_score(raw_dir: Path) -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    d = prepare(raw_dir)
    R, S = d["reviews"], d["sentences"]
    print(json.dumps(d["counts"]))
    stars = R.set_index("rid")["stars"]
    P, pneg, Yseed, *_ = score(S, stars)
    low = S["rid"].map(stars) <= 2
    disc = topics.discover(S["text"][low])
    with open(INTERIM / "scored.pkl", "wb") as f:
        pickle.dump({"R": R, "S": S, "P": P.astype(np.float32), "pneg": pneg.astype(np.float32),
                     "Yseed": Yseed, "counts": d["counts"], "topics": disc}, f)


def stage_sample() -> None:
    d = pickle.load(open(INTERIM / "scored.pkl", "rb"))
    R, S, P = d["R"], d["S"], d["P"]
    stars = S["rid"].map(R.set_index("rid")["stars"])
    rng = np.random.default_rng(42)
    # stratum A: random sentences from 1-3 star reviews (unbiased w.r.t. any model)
    a = S.index[stars <= 3].to_numpy()
    A = rng.choice(a, 180, replace=False)
    # stratum B: 14 per theme among sentences any lexicon or model flags (gives every theme support)
    B = []
    for j, k in enumerate(KEYS):
        cand = np.setdiff1d(np.flatnonzero((P[:, j] >= 0.3) | (d["Yseed"][:, j] == 1)), np.r_[A, B])
        B.extend(rng.choice(cand, 14, replace=False).tolist())
    idx = np.r_[A, np.array(B)]
    out = S.loc[idx, ["rid", "sidx", "text"]].copy()
    out["key"] = out["rid"].map(R.set_index("rid")["key"])
    out["stars"] = stars.loc[idx].to_numpy()
    out["stratum"] = ["random_low"] * len(A) + ["flagged"] * len(B)
    out = out.sample(frac=1, random_state=3)
    out["split"] = np.where(np.arange(len(out)) % 3 == 0, "dev", "test")
    out[["key", "sidx", "stratum", "split", "stars", "text"]].to_csv(INTERIM / "label_sample.csv", index=False)
    print(len(out))


def stage_export() -> None:
    d = pickle.load(open(INTERIM / "scored.pkl", "rb"))
    R, S, P, pneg = d["R"].copy(), d["S"], d["P"], d["pneg"]
    key_of = R.set_index("rid")["key"]
    S = S.assign(key=S["rid"].map(key_of))
    H = pd.read_csv(ROOT / "data" / "hand_labels.csv")
    pos = pd.Series(np.arange(len(S)), index=pd.MultiIndex.from_arrays([S["key"], S["sidx"]]))
    hi = pos.loc[list(zip(H["key"], H["sidx"]))].to_numpy()
    H["text"] = S["text"].to_numpy()[hi]
    val = validate.evaluate(H, P[hi], pneg[hi])
    if val["chosen"] == "classifier_plus_negativity":
        pain = pain_matrix(P, pneg, val["t_theme"], val["t_neg"])
    else:
        pain = pain_matrix(d["Yseed"].astype(np.float32), pneg, 0.5, val["t_neg"])
    rv = pd.DataFrame(pain, columns=KEYS).groupby(S["rid"].to_numpy()).max()
    R = R.set_index("rid").join(rv).fillna({k: 0 for k in KEYS}).reset_index()
    R[KEYS] = R[KEYS].astype(int)
    prev = measure.prevalence(R)
    imp = measure.star_impact(R)
    low = measure.low_star_rates(R)
    life = measure.lifecycle(R)
    yr = measure.by_year(R)
    ttc = measure.time_to_complaint(S, pain)
    grams = measure.top_ngrams(S, pain)
    f1 = {k: val["methods"][val["chosen"]]["per_theme"][k]["f1"] for k in KEYS}
    prec = {k: val["methods"][val["chosen"]]["per_theme"][k]["precision"] for k in KEYS}
    themes = []
    for k in KEYS:
        reach = 100 * prev.loc[k, "share"]
        impact = max(0.0, -imp.loc[k, "coef"])
        conf = f1[k]
        eff = prioritise.EFFORT_PM[k]
        themes.append({
            "key": k, "label": LABELS[k],
            "share": prev.loc[k, "share"], "share_lo": prev.loc[k, "lo"], "share_hi": prev.loc[k, "hi"],
            "star_delta": imp.loc[k, "coef"], "star_delta_lo": imp.loc[k, "lo"], "star_delta_hi": imp.loc[k, "hi"],
            "p_low_given_pain": low.loc[k, "p_low_given_pain"], "p_low_given_none": low.loc[k, "p_low_given_none"],
            "share_of_low_reviews": low.loc[k, "share_of_low_reviews"],
            "confidence_f1": conf, "precision": prec[k], "effort_pm": eff,
            "rice": prioritise.rice(reach, impact, conf, eff),
            "lifecycle": [float(life.loc[b, k]) for b in measure.LIFE_LABELS],
            "by_year": {int(y): float(yr.loc[y, k]) for y in yr.index},
            "time_to_complaint": ttc[k], "top_bigrams": grams[k],
        })
    themes.sort(key=lambda t: -t["rice"])
    for i, t in enumerate(themes, 1):
        t["rank"] = i
    sens = prioritise.effort_sensitivity(themes)
    for t in themes:
        t["effort_sensitivity"] = sens[t["key"]]
    # experiment for the top-ranked theme
    top = themes[0]
    p1 = float((R["stars"] <= 2).mean())
    efficacy = 0.5  # ASSUMPTION: the fix removes half of this pain where it occurs
    reach = top["share"]
    p2 = p1 - efficacy * reach * (top["p_low_given_pain"] - top["p_low_given_none"])
    exp = {"theme": top["key"], "label": top["label"], "metric": "share of 1-2 star reviews",
           "baseline_p1": p1, "efficacy_assumption": efficacy, "target_p2": p2,
           "mde_abs": p1 - p2, "mde_rel": (p1 - p2) / p1, "alpha": 0.05, "power": 0.8,
           "n_per_arm_formula": prioritise.n_per_arm(p1, p2),
           "n_per_arm_statsmodels": prioritise.n_per_arm_statsmodels(p1, p2)}
    # same sizing for every theme, so the spec can pick a different first experiment
    for t in themes:
        q2 = p1 - efficacy * t["share"] * (t["p_low_given_pain"] - t["p_low_given_none"])
        t["experiment_p2"] = q2
        t["experiment_n_per_arm"] = prioritise.n_per_arm(p1, q2) if p1 - q2 > 1e-4 else None
    out = {
        "generated": date.today().isoformat(),
        "dataset": {"name": "Amazon Reviews 2023 (Electronics), true-wireless earbud subset",
                    "url": "https://amazon-reviews-2023.github.io/",
                    "citation": "Hou, Li, He, Yan, Chen, McAuley. Bridging Language and Items for Retrieval and Recommendation. arXiv:2403.03952, 2024.",
                    **d["counts"]},
        "overall": {"mean_stars": float(R["stars"].mean()), "low_star_share": p1,
                    "any_pain_share": float((R[KEYS].sum(1) > 0).mean()),
                    "ols_n": imp.attrs["n"], "ols_items": imp.attrs["items"]},
        "lifecycle_bins": measure.LIFE_LABELS,
        "lifecycle_n": [int(life.loc[b, "n"]) for b in measure.LIFE_LABELS],
        "themes": themes, "experiment": exp, "validation": val, "topics": d["topics"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"top": [(t["key"], round(t["rice"], 2)) for t in themes], "exp": exp,
                      "chosen": val["chosen"], "t": [val["t_theme"], val["t_neg"]],
                      "dev": val["dev_micro"],
                      "micro": {m: v["micro"] for m, v in val["methods"].items()}}, indent=1, default=float))


if __name__ == "__main__":
    stage = sys.argv[1]
    if stage == "score":
        stage_score(Path(sys.argv[2]))
    elif stage == "sample":
        stage_sample()
    else:
        stage_export()
