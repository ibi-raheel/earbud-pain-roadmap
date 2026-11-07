"""Load the filtered earbud reviews, dedupe, sample, split into sentences."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .text import clean, sentences

SEED = 20261106


def earbud_items(raw_dir: Path) -> set:
    """Re-apply the (possibly tightened) title filter to the stored item metadata."""
    from .fetch_filter import is_earbud
    with open(raw_dir / "meta_earbuds.jsonl") as f:
        return {m["parent_asin"] for m in map(json.loads, f) if is_earbud(m)}


def load_reviews(raw_dir: Path) -> pd.DataFrame:
    items = earbud_items(raw_dir)
    rows = []
    with open(raw_dir / "reviews_earbuds.jsonl") as f:
        for line in f:
            r = json.loads(line)
            if r["parent_asin"] not in items:
                continue
            rows.append((r["parent_asin"], r["user_id"], float(r["rating"]), int(r["timestamp"]),
                         r.get("title") or "", r.get("text") or "", bool(r.get("verified_purchase")),
                         int(r.get("helpful_vote") or 0)))
    df = pd.DataFrame(rows, columns=["item", "user", "stars", "ts", "title", "text", "verified", "helpful"])
    return df


def dedupe(df: pd.DataFrame) -> tuple:
    n0 = len(df)
    df = df.drop_duplicates(["item", "user", "ts"])
    n1 = len(df)
    h = df["text"].str.lower().str.replace(r"\W+", "", regex=True).map(
        lambda s: hashlib.md5(s.encode()).hexdigest())
    df = df.assign(h=h).drop_duplicates("h").drop(columns="h")
    n2 = len(df)
    return df, {"raw": n0, "after_exact_dupes": n1, "after_text_dupes": n2}


def prepare(raw_dir: Path, n_sample: int = 120_000) -> dict:
    return prepare_frame(load_reviews(raw_dir), n_sample)


def load_jsonl(path: Path) -> pd.DataFrame:
    """Any review or ticket export in the dataset's own format, one JSON object per line:
    {parent_asin, user_id, rating, timestamp (ms), title, text}. No product filter."""
    rows = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            rows.append((str(r["parent_asin"]), str(r["user_id"]), float(r["rating"]), int(r["timestamp"]),
                         r.get("title") or "", r.get("text") or "", bool(r.get("verified_purchase")),
                         int(r.get("helpful_vote") or 0)))
    return pd.DataFrame(rows, columns=["item", "user", "stars", "ts", "title", "text", "verified", "helpful"])


def prepare_frame(df: pd.DataFrame, n_sample: int = 120_000) -> dict:
    """Post-load half: dedupe, date and length filter, months since first review, sampling,
    sentence split. n_sample=None keeps every review."""
    df, counts = dedupe(df)
    df["date"] = pd.to_datetime(df["ts"], unit="ms")
    df = df[(df["date"] >= "2015-01-01")]
    df["body"] = (df["title"].fillna("") + ". " + df["text"].fillna("")).map(clean)
    df = df[df["text"].str.len() >= 20]
    counts["after_date_and_length"] = len(df)
    # months since the item's first review in the data (a launch proxy)
    first = df.groupby("item")["date"].transform("min")
    df["months_since_first"] = ((df["date"] - first).dt.days / 30.44).astype(float)
    counts["items"] = int(df["item"].nunique())
    rng = np.random.default_rng(SEED)
    if n_sample is not None and len(df) > n_sample:
        df = df.iloc[rng.choice(len(df), n_sample, replace=False)]
    df = df.reset_index(drop=True)
    df["rid"] = np.arange(len(df))
    df["key"] = df["item"] + "|" + df["user"] + "|" + df["ts"].astype(str)
    counts["sample_reviews"] = len(df)
    counts["sample_items"] = int(df["item"].nunique())
    srows = []
    for rid, body in zip(df["rid"], df["body"]):
        for i, s in enumerate(sentences(body)):
            srows.append((rid, i, s))
    sent = pd.DataFrame(srows, columns=["rid", "sidx", "text"])
    counts["sample_sentences"] = len(sent)
    df["n_chars"] = df["body"].str.len()
    return {"reviews": df[["rid", "key", "item", "stars", "date", "months_since_first", "verified",
                           "helpful", "n_chars"]], "sentences": sent, "counts": counts}
