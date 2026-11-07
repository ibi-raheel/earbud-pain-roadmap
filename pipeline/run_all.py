"""Pipeline entry point.

  python -I -m pipeline.run_all score   RAW_DIR   # prepare + models, cache to data/interim
  python -I -m pipeline.run_all sample  RAW_DIR   # write the hand-label sample (text stays local)
  python -I -m pipeline.run_all export  RAW_DIR   # validate, measure, prioritise -> public/results.json
"""
import json
import pickle
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import assemble, measure, prioritise, topics, validate
from .classify import pain_matrix, score
from .prepare import prepare
from .themes import KEYS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "results.json"


def interim(raw_dir: Path) -> Path:
    """Intermediate files hold review text, so they live next to the download, not in the repo."""
    return Path(raw_dir) / "interim"


def stage_score(raw_dir: Path) -> None:
    INTERIM = interim(raw_dir)
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


def stage_sample(raw_dir: Path) -> None:
    INTERIM = interim(raw_dir)
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


def stage_export(raw_dir: Path) -> None:
    INTERIM = interim(raw_dir)
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
    R = assemble.review_pain(R, S, pain)
    efficacy = 0.5  # ASSUMPTION: the fix removes half of this pain where it occurs
    tab = assemble.theme_table(R, S, pain, val["methods"][val["chosen"]]["per_theme"], efficacy=efficacy)
    themes, p1, imp, life = tab["themes"], tab["p1"], tab["imp"], tab["life"]
    # experiment card for the top-ranked theme (every theme also carries its own sizing)
    top = themes[0]
    p2 = top["experiment_p2"]
    exp = {"theme": top["key"], "label": top["label"], "metric": "share of 1-2 star reviews",
           "baseline_p1": p1, "efficacy_assumption": efficacy, "target_p2": p2,
           "mde_abs": p1 - p2, "mde_rel": (p1 - p2) / p1, "alpha": 0.05, "power": 0.8,
           "n_per_arm_formula": prioritise.n_per_arm(p1, p2),
           "n_per_arm_statsmodels": prioritise.n_per_arm_statsmodels(p1, p2)}
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
        stage_sample(Path(sys.argv[2]))
    else:
        stage_export(Path(sys.argv[2]))
