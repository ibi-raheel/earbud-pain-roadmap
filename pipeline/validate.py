"""Validation against hand labels.

Hand labels (data/hand_labels.csv) mark, for each sampled sentence, the pain theme(s) it
complains about ('none' if it complains about nothing in the taxonomy). A positive mention
('battery lasts all day') is NOT a pain and is labelled none.
"""
import numpy as np
import pandas as pd

from .themes import KEYS, NAIVE_RE, SEED_RE


def label_matrix(labels: pd.Series) -> np.ndarray:
    Y = np.zeros((len(labels), len(KEYS)), dtype=np.int8)
    for i, s in enumerate(labels):
        for k in str(s).split(";"):
            k = k.strip()
            if k and k != "none":
                if k not in KEYS:
                    raise ValueError(f"unknown theme {k!r}")
                Y[i, KEYS.index(k)] = 1
    return Y


def lexicon_matrix(lex: dict, texts) -> np.ndarray:
    return np.array([[bool(lex[k].search(t)) for k in KEYS] for t in texts], dtype=np.int8)


def prf(Y: np.ndarray, P: np.ndarray) -> dict:
    tp = ((Y == 1) & (P == 1)).sum(0)
    fp = ((Y == 0) & (P == 1)).sum(0)
    fn = ((Y == 1) & (P == 0)).sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        prec = np.where(tp + fp > 0, tp / (tp + fp), np.nan)
        rec = np.where(tp + fn > 0, tp / (tp + fn), np.nan)
        f1 = np.where(prec + rec > 0, 2 * prec * rec / (prec + rec), 0.0)
    TP, FP, FN = tp.sum(), fp.sum(), fn.sum()
    mp, mr = TP / max(TP + FP, 1), TP / max(TP + FN, 1)
    return {"per_theme": {k: {"precision": float(prec[j]), "recall": float(rec[j]), "f1": float(f1[j]),
                              "support": int(Y[:, j].sum())} for j, k in enumerate(KEYS)},
            "micro": {"precision": float(mp), "recall": float(mr),
                      "f1": float(2 * mp * mr / (mp + mr)) if mp + mr else 0.0}}


def tune(Y: np.ndarray, P: np.ndarray, pneg: np.ndarray, tol: float = 0.01,
         theme_grid=None) -> tuple:
    """Grid-search both thresholds on the dev set. Among settings within `tol` of the best
    micro-F1, take the most precise one: the dev set is small, and over-counting a pain
    inflates Reach more than under-counting deflates it."""
    grid = []
    for tt in (np.arange(0.15, 0.80, 0.05) if theme_grid is None else theme_grid):
        for tn in np.arange(0.20, 0.85, 0.05):
            m = prf(Y, ((P >= tt) & (pneg[:, None] >= tn)).astype(np.int8))["micro"]
            grid.append((m["f1"], m["precision"], float(round(tt, 2)), float(round(tn, 2))))
    best = max(g[0] for g in grid)
    near = [g for g in grid if g[0] >= best - tol]
    f, p, tt, tn = max(near, key=lambda g: (g[1], g[0]))
    return tt, tn, f


def evaluate(H: pd.DataFrame, P: np.ndarray, pneg: np.ndarray) -> dict:
    """H: hand-label rows aligned with P and pneg, columns text, labels, split."""
    Y = label_matrix(H["labels"])
    dev = (H["split"] == "dev").to_numpy()
    test = ~dev
    texts = H["text"].tolist()
    L = lexicon_matrix(SEED_RE, texts).astype(float)
    # candidate 1: theme classifier x negativity; candidate 2: seed lexicon x negativity
    tt, tn_c, f_c = tune(Y[dev], P[dev], pneg[dev])
    _, tn_l, f_l = tune(Y[dev], L[dev], pneg[dev], theme_grid=[0.5])
    chosen = "classifier_plus_negativity" if f_c >= f_l else "seed_lexicon_plus_negativity"
    methods = {
        "keyword_baseline": lexicon_matrix(NAIVE_RE, texts),
        "seed_lexicon": L.astype(np.int8),
        "seed_lexicon_plus_negativity": ((L >= 0.5) & (pneg[:, None] >= tn_l)).astype(np.int8),
        "classifier_plus_negativity": ((P >= tt) & (pneg[:, None] >= tn_c)).astype(np.int8),
    }
    res = {name: prf(Y[test], M[test]) for name, M in methods.items()}
    dev_res = {name: prf(Y[dev], M[dev])["micro"] for name, M in methods.items()}
    return {"chosen": chosen, "t_theme": tt if chosen.startswith("classifier") else None,
            "t_neg": tn_c if chosen.startswith("classifier") else tn_l,
            "n_dev": int(dev.sum()), "n_test": int(test.sum()),
            "methods": res, "dev_micro": dev_res,
            "confusion": confusion(Y[test], methods[chosen][test])}


def confusion(Y: np.ndarray, P: np.ndarray) -> dict:
    """Theme-by-theme co-occurrence of hand label (rows) vs model label (cols), plus a
    'none' row/column, counted over sentences."""
    K = len(KEYS)
    M = np.zeros((K + 1, K + 1), dtype=int)
    for y, p in zip(Y, P):
        ys = np.flatnonzero(y).tolist() or [K]
        ps = np.flatnonzero(p).tolist() or [K]
        for a in ys:
            for b in ps:
                M[a, b] += 1
    return {"labels": KEYS + ["none"], "matrix": M.tolist()}
