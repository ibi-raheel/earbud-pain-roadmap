"""Shared assembly of the per-theme table.

Used by both `run_all.stage_export` (the public run) and `triage.py` (any team's export), so
the two cannot drift: same measures, same RICE, same sensitivity, same experiment sizing.
"""
import numpy as np
import pandas as pd

from . import measure, prioritise
from .themes import KEYS, LABELS


def review_pain(R: pd.DataFrame, S: pd.DataFrame, pain: np.ndarray) -> pd.DataFrame:
    """A review has pain k if any of its sentences does."""
    rv = pd.DataFrame(pain, columns=KEYS).groupby(S["rid"].to_numpy()).max()
    R = R.set_index("rid").join(rv).fillna({k: 0 for k in KEYS}).reset_index()
    R[KEYS] = R[KEYS].astype(int)
    return R


def theme_table(R: pd.DataFrame, S: pd.DataFrame, pain: np.ndarray, per_theme: dict,
                effort: dict = None, efficacy: float = 0.5) -> dict:
    """R must already carry the pain columns (see review_pain). per_theme is the validation
    block for the chosen detector: {key: {"f1":..., "precision":...}}.
    Returns {"themes", "p1", "imp", "life", "yr"}; themes are sorted by RICE and ranked."""
    effort = {**prioritise.EFFORT_PM, **(effort or {})}
    prev = measure.prevalence(R)
    imp = measure.star_impact(R)
    low = measure.low_star_rates(R)
    life = measure.lifecycle(R)
    yr = measure.by_year(R)
    ttc = measure.time_to_complaint(S, pain)
    grams = measure.top_ngrams(S, pain)
    themes = []
    for k in KEYS:
        reach = 100 * prev.loc[k, "share"]
        impact = max(0.0, -imp.loc[k, "coef"])
        conf = per_theme[k]["f1"]
        eff = effort[k]
        themes.append({
            "key": k, "label": LABELS[k],
            "share": prev.loc[k, "share"], "share_lo": prev.loc[k, "lo"], "share_hi": prev.loc[k, "hi"],
            "star_delta": imp.loc[k, "coef"], "star_delta_lo": imp.loc[k, "lo"], "star_delta_hi": imp.loc[k, "hi"],
            "p_low_given_pain": low.loc[k, "p_low_given_pain"], "p_low_given_none": low.loc[k, "p_low_given_none"],
            "share_of_low_reviews": low.loc[k, "share_of_low_reviews"],
            "confidence_f1": conf, "precision": per_theme[k]["precision"], "effort_pm": eff,
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
    # experiment sizing for every theme: share of 1-2 star reviews, assumed efficacy
    p1 = float((R["stars"] <= 2).mean())
    for t in themes:
        q2 = p1 - efficacy * t["share"] * (t["p_low_given_pain"] - t["p_low_given_none"])
        t["experiment_p2"] = q2
        t["experiment_n_per_arm"] = prioritise.n_per_arm(p1, q2) if p1 - q2 > 1e-4 else None
    return {"themes": themes, "p1": p1, "imp": imp, "life": life}
