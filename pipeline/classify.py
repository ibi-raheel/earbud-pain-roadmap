"""Sentence-level pain detection.

pain(sentence, theme) = P(theme | sentence) >= t_theme  AND  P(negative | sentence) >= t_neg

- Theme model: one-vs-rest logistic regression on TF-IDF (1-2 grams), trained on weak
  labels from the SEED lexicon. Regularisation lets it score sentences that use words
  outside the lexicon but share its context.
- Negativity model: logistic regression on TF-IDF trained by distant supervision:
  sentences from 1-star reviews = negative, from 5-star reviews = positive.
Thresholds are tuned on the dev half of the hand-labelled set (see validate.py).
"""
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .themes import KEYS, SEED_RE

SEED = 7


def fit_vectorizer(texts) -> TfidfVectorizer:
    vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=5, max_features=60_000,
                          sublinear_tf=True, token_pattern=r"(?u)\b[\w']+\b")
    vec.fit(texts)
    return vec


def seed_labels(texts) -> np.ndarray:
    return np.array([[bool(SEED_RE[k].search(t)) for k in KEYS] for t in texts], dtype=np.int8)


def train_theme_models(X: sparse.csr_matrix, Y: np.ndarray, n_train: int = 150_000) -> list:
    rng = np.random.default_rng(SEED)
    idx = rng.choice(X.shape[0], min(n_train, X.shape[0]), replace=False)
    models = []
    for j in range(Y.shape[1]):
        m = LogisticRegression(C=0.5, max_iter=400, solver="liblinear")
        m.fit(X[idx], Y[idx, j])
        models.append(m)
    return models


def train_negativity(X: sparse.csr_matrix, stars: np.ndarray, n_train: int = 150_000) -> LogisticRegression:
    mask = np.where((stars == 1) | (stars == 5))[0]
    rng = np.random.default_rng(SEED + 1)
    # balance the classes: 5-star sentences dominate otherwise
    neg = mask[stars[mask] == 1]
    pos = mask[stars[mask] == 5]
    k = min(len(neg), len(pos), n_train // 2)
    idx = np.concatenate([rng.choice(neg, k, replace=False), rng.choice(pos, k, replace=False)])
    m = LogisticRegression(C=1.0, max_iter=400, solver="liblinear")
    m.fit(X[idx], (stars[idx] == 1).astype(int))
    return m


def score(sent: pd.DataFrame, review_stars: pd.Series) -> tuple:
    """Returns (P_theme [n x K], P_neg [n], vectorizer, models) for every sentence."""
    texts = sent["text"].tolist()
    vec = fit_vectorizer(texts)
    X = vec.transform(texts)
    Y = seed_labels(texts)
    theme_models = train_theme_models(X, Y)
    P = np.column_stack([m.predict_proba(X)[:, 1] for m in theme_models])
    stars = review_stars.reindex(sent["rid"]).to_numpy()
    neg_model = train_negativity(X, stars)
    pneg = neg_model.predict_proba(X)[:, 1]
    return P, pneg, Y, vec, theme_models, neg_model


def pain_matrix(P: np.ndarray, pneg: np.ndarray, t_theme: float, t_neg: float) -> np.ndarray:
    return ((P >= t_theme) & (pneg[:, None] >= t_neg)).astype(np.int8)
