# Earbud Pain-to-Roadmap

Measures which pains cost true-wireless earbuds the most stars, using 120,000 public reviews.
The pains are then ranked with RICE, and the top fix gets an experiment sized with a power
calculation.

**Live demo:** coming soon

## The problem
True-wireless earbuds trade size, battery and fit against each other, and owners describe
those trade-offs in millions of unstructured reviews. A product team needs to know which
pain is most common, which one costs the most rating points per affected owner, and how big
a test has to be to show a fix worked.

## What it does
1. **Pain map.** Each of 10 pain themes (fit, battery, charging case, connectivity, sound,
   noise cancelling, calls, controls, failure, app) gets its share of reviews with a
   bootstrap CI, and the stars it costs within the same model.
2. **Lifecycle.** Pain share by model age. Failure complaints rise from 5.9% of reviews in a
   model's first 3 months to 13.6% after 2 years.
3. **Detector check.** Precision, recall and F1 against 320 hand-labelled sentences,
   compared with a keyword baseline.
4. **RICE board.** Reach and Impact are measured, Confidence is the validated F1, and Effort
   is an explicit assumption. A sensitivity analysis varies Effort.
5. **Experiment card.** Metric, baseline, target and the required sample per arm. The
   sample size is checked by hand and against statsmodels.

Headline: when an earbud **stops working**, the review loses **1.52 stars** compared with
other reviews of the same model. That is 2.4 times any other pain. The median reported time
to failure is 2 months.

See [METHOD.md](METHOD.md) for the equations, assumptions, validation and limitations, and
[PRODUCT_SPEC.md](PRODUCT_SPEC.md) for the one-page spec the numbers support.

## How it works
- `pipeline/fetch_filter.py` streams the 22.6 GB review file and keeps 1.09M reviews of
  10,529 earbud models. Nothing large is stored.
- `pipeline/classify.py`: theme logistic regressions on TF-IDF, trained on weak labels,
  gated by a negativity model trained on 1-star against 5-star sentences.
- `pipeline/measure.py`: item-clustered bootstrap prevalence, OLS with item fixed effects,
  lifecycle curves and stated time to failure.
- `pipeline/prioritise.py`: RICE, Effort sensitivity, two-proportion sample size.
- Results go to `public/results.json`. The page is static and needs no API keys.

## Run locally
```bash
# pipeline (Python 3.10+)
python -m venv .venv && .venv/bin/pip install -r requirements.txt
B=https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw
mkdir -p ../downloads/earbuds
curl -sL $B/meta_categories/meta_Electronics.jsonl | .venv/bin/python -I pipeline/fetch_filter.py meta ../downloads/earbuds
curl -sL $B/review_categories/Electronics.jsonl   | .venv/bin/python -I pipeline/fetch_filter.py reviews ../downloads/earbuds
.venv/bin/python -I run.py score ../downloads/earbuds
.venv/bin/python -I run.py export ../downloads/earbuds
.venv/bin/python -I -m pytest -q tests

# web page
npm install
npm run dev
```

## Data
Real public data: [Amazon Reviews 2023](https://amazon-reviews-2023.github.io/) (McAuley
Lab, UC San Diego). Cite: Hou et al., *Bridging Language and Items for Retrieval and
Recommendation*, arXiv:2403.03952, 2024. No licence is stated (research release), so this
repo ships only aggregate statistics: no review text and no reviewer IDs. Effort
estimates and the fix-efficacy figure are assumptions and are labelled as such. Nothing is
simulated.

---
Built by Ibi Raheel, mechanical engineer building AI tools. More work at [ibiraheel.com](https://ibiraheel.com).
