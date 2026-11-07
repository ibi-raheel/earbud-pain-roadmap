# Method

## Research question

Which pains cost wireless earbuds the most stars, which ones grow as a model ages, and what
should the next model fix first?

Three measures answer it: stars lost within the same model (section 4, impact), pain share by
model age (section 4, lifecycle) and a RICE ranking whose stability is tested against the
Effort assumption, with a sized experiment for each pain (section 5). The decision rules that
turn these into a fix queue, and the tool that applies them to new data, are in
[SOLUTION.md](SOLUTION.md).

Goal: measure which pains in true-wireless earbuds cost the most rating points, rank them
with RICE, and size an experiment for the top item. Every number in `public/results.json`
comes from the pipeline in `pipeline/`. Nothing is typed in by hand except the Effort
assumptions and the experiment's efficacy assumption, both labelled as such.

## 1. Data

**Source:** Amazon Reviews 2023, Electronics category (McAuley Lab, UC San Diego).
<https://amazon-reviews-2023.github.io/>, files from the Hugging Face mirror
`McAuley-Lab/Amazon-Reviews-2023`.
Citation: Hou, Li, He, Yan, Chen, McAuley. *Bridging Language and Items for Retrieval and
Recommendation.* arXiv:2403.03952, 2024.
**Licence:** no licence is stated on the dataset card; it is released for research use.
This repo ships **only aggregates** (shares, coefficients, counts, frequent bigrams). No
review text and no reviewer IDs are committed. The hand-label file stores a review key and
a sentence index; the text is rebuilt locally from the download.

**Filtering** (`pipeline/fetch_filter.py`). The 5.2 GB item-metadata file and the 22.6 GB
review file are streamed through a filter, so the full files never touch disk:

| Step | Count |
|---|---|
| Electronics items scanned | 1,610,012 |
| True-wireless earbud items (title must say wireless/Bluetooth/TWS **and** earbud/in-ear/earphone; accessories, neckbands, wired, over-ear rejected) | 10,529 |
| Electronics reviews scanned | 43,886,944 |
| Reviews of those items | 1,091,757 |
| After removing exact duplicates (item, user, time) | 1,078,671 |
| After removing duplicate text (same review across colour variants) | 994,392 |
| From 2015 on, text at least 20 characters | 972,896 (9,929 items) |
| Random analysis sample (seed 20261106) | **120,000 reviews, 5,663 items, 612,234 sentences** |

A 120k random sample keeps the run inside a laptop budget; bootstrap CIs on prevalence
are about +/-0.5 to 1.5 points, so a larger sample would not change any ranking.

## 2. Pain taxonomy

Ten themes (`pipeline/themes.py`): fit and comfort, battery, charging case, connectivity,
sound quality, noise cancelling, calls and mic, touch controls, earbud stops working, app
and firmware. The list was checked against an unsupervised pass: TF-IDF + NMF (k = 20) on
sentences from 1-2 star reviews (`pipeline/topics.py`). One large NMF topic (37% of
sentences) is generic wording ("earbuds, headphones, phone, just"). Most other topics map
to one of the ten themes: sound, fit ("don't stay in ears"), charging ("won't hold charge"),
failure ("stopped working after months"), battery life and the case. The topics that do not are purchase regret ("don't buy",
"waste money", "disappointed") and value for money ("worth the price"). These are outcomes
rather than product pains, so they stay out of the taxonomy.

## 3. Pain detection

A sentence is a **pain** for theme *k* when it is about *k* **and** it is negative:

    pain_k(s) = 1[ P_k(s) >= t_theme ] * 1[ P_neg(s) >= t_neg ]

- **Theme model** P_k: one logistic regression per theme on TF-IDF features (word 1-2
  grams, 60k vocabulary, sublinear tf). It is trained on weak labels from a seed lexicon,
  using 150k sentences, C = 0.5. Regularisation gives soft scores for sentences whose
  wording is outside the lexicon.
- **Negativity model** P_neg: logistic regression on the same features, trained by distant
  supervision. Sentences from 1-star reviews count as negative, sentences from 5-star
  reviews as positive, and the classes are balanced. This separates "battery life is
  great" from "battery dies in an hour".
- A review has pain *k* if any of its sentences does.

Thresholds and the choice between the classifier and the plain seed lexicon (both gated by
negativity) are set on the **dev** split of the hand labels only (section 6).

## 4. Measures

**Reach (prevalence).** p_k = share of reviews with pain *k*. The 95% CI comes from a
cluster bootstrap that resamples **items** (B = 300), because reviews of one model are not
independent:

    p_k* = sum_i w_i * s_ik / sum_i w_i * n_i,   w ~ Multinomial(I, 1/I)

**Impact (stars lost).** OLS with item fixed effects, estimated by the within transform,
with standard errors clustered by item:

    stars_ri = a_i + sum_k b_k * pain_k,ri + g * log(len_ri) + e_ri

b_k is the change in stars when a review mentions pain *k*, compared with other reviews
of the **same model**. This removes the "cheap earbuds get worse reviews and more
complaints" confound. Review length is a control, because long reviews mention more
themes and tend to be more negative. Fit on 118,136 reviews of 3,799 items that have at
least two reviews.

**Lifecycle.** Pain share by months since the item's first review in the data, used as a
proxy for time since launch: 0-3, 3-6, 6-12, 12-24 and 24+ months.

**Stated time to complaint.** A regex pulls durations such as "stopped working after 3
months" or "within two weeks" out of pain sentences and converts them to months. Values
above 48 months are dropped.

## 5. Prioritisation and experiment

**RICE:** score_k = Reach_k (% of reviews) x Impact_k (stars lost, floored at 0) x
Confidence_k (test-set F1 of the detector for *k*) / Effort_k (person-months).
**Effort is an assumption**, written with a one-line rationale in
`pipeline/prioritise.py`. To show how much the ranking leans on it, each theme's effort is
scaled independently by a log-uniform factor in [0.5, 2] over 5,000 draws, and the share
of draws in which each theme ranks first or in the top 3 is reported.

**Experiment sizing.** Two-sided two-proportion z-test, unpooled variance:

    n per arm = (z_{1-a/2} + z_{1-b})^2 * [p1(1-p1) + p2(1-p2)] / (p1 - p2)^2

- Metric: share of 1-2 star reviews (p1 = measured baseline).
- Target: p2 = p1 - e * Reach_k * (P(low | pain_k) - P(low | no pain_k)), where e = 0.5
  is an **assumed** fix efficacy (half of the pain removed where it occurs).

Worked by hand for the top-ranked theme (sound quality):

    p1 = 0.24152
    p2 = 0.24152 - 0.5 * 0.25021 * (0.35730 - 0.20288) = 0.24152 - 0.01932 = 0.22220
    (z_0.975 + z_0.80)^2 = (1.959964 + 0.841621)^2 = 7.848879
    p1(1-p1) + p2(1-p2) = 0.18319 + 0.17283 = 0.35601
    n = 7.848879 * 0.35601 / 0.019319^2 = 7,486.9  ->  7,487 per arm

statsmodels (`NormalIndPower` with Cohen's h) gives 7,488. The 1-unit gap comes from the
arcsine effect size. A test asserts the two agree within 3%, and a second test checks the
formula against the textbook case p1 = 0.65, p2 = 0.85 (70 per arm).

## 6. Validation

**Hand-labelled set.** 320 sentences drawn by `run.py sample <download dir>` and labelled manually
against the rubric below, in one pass by one annotator, with stars and model scores hidden:

- 180 random sentences from 1-3 star reviews. This stratum is independent of every model.
- 140 sentences, 14 per theme, from sentences any lexicon or model flagged. This gives
  every theme some support.
- Split: 107 dev (thresholds and method choice) and 213 test (all reported scores).

Rubric: label theme *k* only if the sentence **complains** about *k*. Positive mentions
are `none`. "Stopped charging" counts as charging case. "Stopped working / died / broke" counts
as failure. One-bud dropouts and left-right sync count as connectivity.

**Results on the 213 test sentences** (micro-averaged over themes):

| Method | Precision | Recall | F1 |
|---|---|---|---|
| Keyword baseline (one or two grep words per theme) | 0.30 | 0.38 | 0.33 |
| Seed lexicon alone | 0.37 | 0.73 | 0.49 |
| Seed lexicon x negativity | 0.58 | 0.64 | 0.61 |
| **Theme classifier x negativity (chosen on dev)** | 0.53 | 0.58 | 0.55 |

The negativity gate is the step that matters: it lifts precision from 0.37 to 0.58 at a
small recall cost. On dev the classifier scored higher (0.554 against 0.531), so it was
chosen. On test the plain lexicon with the gate scored higher. With about 200 test
sentences the gap is inside noise, and the choice was not revisited after seeing test
scores. Per-theme F1 runs from 0.89 (calls and mic) down to 0.17 (noise cancelling, 4
test positives). Per-theme F1 is the Confidence term in RICE, so weakly validated themes
are discounted automatically.

**Estimator checks** (`tests/test_pipeline.py`, 15 tests; `tests/test_triage.py`, 3 more for the triage tool):
- The fixed-effects OLS recovers planted coefficients (-1.0 and -0.3 stars) on synthetic
  data with item-level quality differences, within 0.05, and the CI covers the truth.
- Bootstrap CIs bracket the point estimate and recover a planted 10% prevalence.
- P/R/F1 is checked against a 4-row example worked by hand.
- The sample-size formula is checked by hand and against statsmodels.
- The shipped `results.json` is checked for consistency: ranks, CI order, RICE order,
  the experiment n, and the chosen detector beating the keyword baseline.

## 7. Key measured results

- Earbud stops working: 10.1% of reviews, but **-1.52 stars** (95% CI -1.60 to -1.45)
  within the same model. That is 2.4x the next-worst pain, and 64% of these reviews are
  1-2 stars, against 20% without it. Its share rises from 5.9% of reviews in a model's
  first 3 months to 13.6% after 24 months. Where reviewers state when it happened, the
  median is 2 months (n = 2,676).
- Connectivity: 14.8% reach, -0.63 stars. Sound quality: 25.0% reach, -0.58 stars.
- RICE top 3: sound quality, connectivity, failure. They stay in the top 3 in 99%, 98%
  and 84% of effort perturbations.
- Touch controls, noise cancelling and app/firmware complaints cost no measurable stars
  once the item is held fixed (CIs include 0, or are positive for app reviews, which
  are often updates such as "after the firmware update it works").

## 8. Limitations

- One annotator and 320 labels: per-theme scores rest on 4-21 positives each and are
  noisy. A second annotator and an agreement score (Cohen's kappa) would be the next step.
- Sound-quality precision is the lowest of the big themes (0.39), so its Reach is likely
  overstated. Its RICE lead over connectivity is not robust to that.
- Public reviews are not support tickets: reviewers self-select, and failures that lead to
  a return may never be reviewed. Rates describe reviews, not owners.
- "Months since first review" stands in for product age and mixes product age with
  owner tenure.
- The OLS coefficients are conditional associations within a model, not causal effects of
  fixing a pain.
- Effort and fix efficacy are assumptions. The sensitivity analysis bounds the first; the
  experiment n scales roughly with 1/efficacy^2.
