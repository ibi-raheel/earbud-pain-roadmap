"""Measures: prevalence (cluster bootstrap), star impact (OLS, item fixed effects),
lifecycle curves and stated time-to-complaint."""
import re
from collections import Counter

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .themes import KEYS

LIFE_BINS = [0, 3, 6, 12, 24, 1e9]
LIFE_LABELS = ["0-3 mo", "3-6 mo", "6-12 mo", "12-24 mo", "24+ mo"]


def prevalence(R: pd.DataFrame, B: int = 300, seed: int = 11) -> pd.DataFrame:
    """Share of reviews with each pain; 95% CI from a bootstrap that resamples items
    (reviews of the same item are not independent)."""
    point = R[KEYS].mean()
    g = R.groupby("item")[KEYS].agg(["sum", "count"])
    sums = np.column_stack([g[(k, "sum")].to_numpy() for k in KEYS])
    cnt = g[(KEYS[0], "count")].to_numpy()
    rng = np.random.default_rng(seed)
    n_items = len(cnt)
    boots = np.empty((B, len(KEYS)))
    for b in range(B):
        w = np.bincount(rng.integers(0, n_items, n_items), minlength=n_items)
        boots[b] = (w @ sums) / (w @ cnt)
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    return pd.DataFrame({"share": point.to_numpy(), "lo": lo, "hi": hi}, index=KEYS)


def within_item(df: pd.DataFrame, cols: list, group: str) -> pd.DataFrame:
    return df[cols] - df.groupby(group)[cols].transform("mean")


def star_impact(R: pd.DataFrame) -> pd.DataFrame:
    """OLS of stars on pain indicators with item fixed effects (within transform),
    controlling for log review length. SEs clustered by item."""
    R = R[R.groupby("item")["item"].transform("size") >= 2].copy()
    R["log_len"] = np.log(R["n_chars"].clip(lower=1))
    cols = ["stars"] + KEYS + ["log_len"]
    D = within_item(R, cols, "item")
    X = D[KEYS + ["log_len"]]
    fit = sm.OLS(D["stars"], X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(R["item"])[0]})
    ci = fit.conf_int()
    out = pd.DataFrame({"coef": fit.params[KEYS], "se": fit.bse[KEYS],
                        "lo": ci.loc[KEYS, 0], "hi": ci.loc[KEYS, 1]})
    out.attrs["n"] = int(fit.nobs)
    out.attrs["items"] = int(R["item"].nunique())
    out.attrs["log_len"] = float(fit.params["log_len"])
    return out


def low_star_rates(R: pd.DataFrame) -> pd.DataFrame:
    low = R["stars"] <= 2
    rows = {}
    for k in KEYS:
        m = R[k] == 1
        rows[k] = {"p_low_given_pain": float(low[m].mean()), "p_low_given_none": float(low[~m].mean()),
                   "share_of_low_reviews": float(m[low].mean())}
    return pd.DataFrame(rows).T


def lifecycle(R: pd.DataFrame) -> pd.DataFrame:
    b = pd.cut(R["months_since_first"], LIFE_BINS, labels=LIFE_LABELS, right=False)
    t = R.groupby(b, observed=False)[KEYS].mean()
    t["n"] = R.groupby(b, observed=False).size()
    return t


def by_year(R: pd.DataFrame) -> pd.DataFrame:
    y = R["date"].dt.year
    t = R.groupby(y)[KEYS].mean()
    t["n"] = R.groupby(y).size()
    return t[t["n"] >= 500]


_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "few": 3, "couple": 2}
_AFTER = re.compile(r"\b(?:after|within|in less than|in under|only)\s+(?:about\s+|just\s+|only\s+|a\s+few\s+|a\s+couple(?:\s+of)?\s+)?"
                    r"(\d{1,3}|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|few|couple)"
                    r"\s+(day|week|month|year)s?\b", re.I)
_UNIT = {"day": 1 / 30.44, "week": 7 / 30.44, "month": 1.0, "year": 12.0}


def stated_months(sentence: str):
    """'stopped working after 3 months' -> 3.0. Returns None when no duration is stated."""
    m = _AFTER.search(sentence)
    if not m:
        return None
    n = m.group(1).lower()
    n = float(_NUM.get(n, n)) if not n.isdigit() else float(n)
    return n * _UNIT[m.group(2).lower()]


def time_to_complaint(S: pd.DataFrame, pain: np.ndarray) -> dict:
    out = {}
    months = S["text"].map(stated_months)
    for j, k in enumerate(KEYS):
        v = months[(pain[:, j] == 1) & months.notna()].to_numpy(dtype=float)
        v = v[v <= 48]
        if len(v) < 20:
            out[k] = {"n": int(len(v))}
            continue
        hist = np.histogram(v, bins=[0, 1, 3, 6, 12, 24, 48])[0]
        out[k] = {"n": int(len(v)), "median_months": float(np.median(v)),
                  "p25": float(np.percentile(v, 25)), "p75": float(np.percentile(v, 75)),
                  "hist_bins": ["<1", "1-3", "3-6", "6-12", "12-24", "24-48"], "hist": hist.tolist()}
    return out


_STOP = set("""the a an and or but to of in on for with it its it's this that is was are be been i my me
my they them their you your so very just not no at as have has had if than then too can will would
these those there from out up all one get got when what which also only do does did after even""".split())


def top_ngrams(S: pd.DataFrame, pain: np.ndarray, n: int = 8) -> dict:
    out = {}
    for j, k in enumerate(KEYS):
        c = Counter()
        for t in S["text"][pain[:, j] == 1].str.lower().head(40_000):
            w = [x for x in re.findall(r"[a-z']+", t)]
            for a, b in zip(w, w[1:]):
                if a not in _STOP and b not in _STOP:
                    c[f"{a} {b}"] += 1
        out[k] = [[g, int(v)] for g, v in c.most_common(n)]
    return out
