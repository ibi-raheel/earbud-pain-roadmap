"""Stream-filter the Amazon Reviews 2023 Electronics files (read from stdin).

Usage:
  curl -sL <meta_Electronics.jsonl> | python -I fetch_filter.py meta  OUT_DIR
  curl -sL <Electronics.jsonl>      | python -I fetch_filter.py reviews OUT_DIR

Only true-wireless earbud items (and their reviews) are written to OUT_DIR, so the
22 GB source never touches disk.
"""
import json
import re
import sys
from pathlib import Path

WANT = re.compile(r"(true\s*wireless|wireless|bluetooth|\btws\b)", re.I)
BUD = re.compile(r"(ear\s?buds?|in-ear|earphones?|ear\s?pods?)", re.I)
REJECT = re.compile(
    r"(neckband|neck\s?band|wired|3\.5\s?mm|over[- ]ear|on[- ]ear|headset for (pc|office)|"
    r"case (for|cover)|cover for|\bskin\b|ear ?tips?\b|replacement|adapter|charger only|"
    r"cable|strap|holder|hooks?|cleaning|cleaner|sticker|decal|stand\b|lanyard|"
    r"protective|keychain|shockproof|silicone (case|cover)|hard (case|shell)|airpods( pro)? case|case compatible|\bcover\b|"
    r"bone conduction|hearing aid|sleep(ing)? (mask|headphones)|kids headband|headband)",
    re.I,
)
CAT_OK = re.compile(r"(earbud|in-ear|headphones)", re.I)


def is_earbud(m: dict) -> bool:
    title = m.get("title") or ""
    cats = " > ".join(m.get("categories") or [])
    if not (WANT.search(title) and BUD.search(title)):
        return False
    if REJECT.search(title):
        return False
    if cats and not CAT_OK.search(cats):
        return False
    return True


def run_meta(out: Path) -> None:
    n = kept = 0
    with open(out / "meta_earbuds.jsonl", "w") as fo:
        for raw in sys.stdin.buffer:
            n += 1
            low = raw.lower()
            if b"earbud" not in low and b"in-ear" not in low and b"earphone" not in low and b"ear bud" not in low:
                continue
            m = json.loads(raw)
            if is_earbud(m):
                keep = {k: m.get(k) for k in ("parent_asin", "title", "store", "average_rating",
                                               "rating_number", "price", "categories", "details")}
                fo.write(json.dumps(keep) + "\n")
                kept += 1
    print(json.dumps({"meta_lines": n, "earbud_items": kept}))


def run_reviews(out: Path) -> None:
    asins = set()
    with open(out / "meta_earbuds.jsonl") as f:
        for line in f:
            asins.add(json.loads(line)["parent_asin"].encode())
    key = b'"parent_asin": "'
    n = kept = 0
    with open(out / "reviews_earbuds.jsonl", "wb") as fo:
        for raw in sys.stdin.buffer:
            n += 1
            i = raw.find(key)
            if i < 0:
                continue
            j = raw.find(b'"', i + len(key))
            if raw[i + len(key):j] in asins:
                fo.write(raw)
                kept += 1
    print(json.dumps({"review_lines": n, "earbud_reviews": kept}))


if __name__ == "__main__":
    mode, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    {"meta": run_meta, "reviews": run_reviews}[mode](out)
