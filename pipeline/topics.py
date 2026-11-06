"""Theme discovery: TF-IDF + NMF on sentences from 1-2 star reviews.

Used to check the theme taxonomy against what the data actually contains
(each NMF topic is mapped to a named theme by its top terms).
"""
import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from .themes import KEYS, SEED_RE


def discover(texts, k: int = 20, seed: int = 0, max_docs: int = 60_000) -> list:
    rng = np.random.default_rng(seed)
    texts = list(texts)
    if len(texts) > max_docs:
        texts = [texts[i] for i in rng.choice(len(texts), max_docs, replace=False)]
    vec = TfidfVectorizer(stop_words="english", min_df=10, max_df=0.3, ngram_range=(1, 2),
                          max_features=20_000, sublinear_tf=True)
    X = vec.fit_transform(texts)
    nmf = NMF(n_components=k, init="nndsvd", random_state=seed, max_iter=300)
    W = nmf.fit_transform(X)
    H = nmf.components_
    terms = np.array(vec.get_feature_names_out())
    share = np.bincount(W.argmax(1), minlength=k) / len(texts)
    out = []
    for t in range(k):
        top = terms[np.argsort(-H[t])[:10]].tolist()
        # map topic to the theme whose seed lexicon matches most of its top terms
        hits = {key: sum(bool(SEED_RE[key].search(w)) for w in top) for key in KEYS}
        best = max(hits, key=hits.get)
        out.append({"topic": t, "top_terms": top, "share": round(float(share[t]), 4),
                    "theme": best if hits[best] >= 1 else "other"})
    return sorted(out, key=lambda d: -d["share"])
