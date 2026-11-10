# The solution: a field-pain triage recipe

**Question.** Which pains cost wireless earbuds the most stars, which ones grow as a model
ages, and what should the next model fix first?

**Answer, measured on 120,000 public reviews of 5,663 earbud models.** Battery costs 0.31
stars. An earbud that stops working costs 1.52, which is 2.4x any other pain, and its share of
reviews more than doubles as a model ages (5.9% at 0-3 months, 13.6% at 24+ months). A
connectivity firmware fix is the cheapest top-3 bet, and proving it takes 12,487 owners per
arm.

The method behind that answer is packaged below as a one-page recipe plus a small tool that
runs it on any team's own reviews or support tickets. Every number on this page is in
`public/results.json`. Equations and validation are in [METHOD.md](METHOD.md).

## The recipe (one page)

1. **Pull.** One product's reviews or support tickets, each with a date, a rating or outcome
   score, and text. Dedupe by (item, user, time) and by normalised text.
2. **Tag.** Ten pain themes. Each is a theme classifier gated by a negativity model. Hand-label
   about 300 sentences split into dev and test, with two annotators. Accept the tagger only if
   its test F1 beats keyword search. In the public run it scores 0.55 against 0.33 on 213
   held-out sentences.
3. **Measure** each pain three ways:
   - reach, with a CI that resamples whole models;
   - stars lost compared with other reviews of the same model (item fixed effects);
   - share by product age (0-3, 3-6, 6-12, 12-24, 24+ months).
4. **Decide** with four labels (rules below).
5. **Prove it.** Size the holdout with a two-proportion test. Firmware fixes go out as a
   staged OTA holdout. Hardware fixes are compared across build cohorts.
6. **Re-run** after every launch and every OTA.

## Decision rules

| Label | Rule | Why this threshold |
|---|---|---|
| **FIX FIRST** | RICE rank 1-3 **and** in the top 3 in at least 80% of the 5,000 effort draws | Effort is assumed, so a top-3 place has to survive Effort being off by up to 2x either way |
| **GATE BEFORE LAUNCH** | share at 24+ months is at least 1.5x the share at 0-3 months, **and** the star CI lies entirely below 0 | A pain that grows with age and costs stars is a reliability problem; it becomes a pre-launch reliability test |
| **NON-GOAL** | the 95% CI on stars lost includes 0 or is positive | No measurable star cost within the same model |
| **WATCH** | everything else | Costs stars but is not stable in the top 3 and does not grow with age |
| *verify* (flag) | detector precision under 0.45 | Reach is probably overstated; check a sample by hand before acting |

A theme can carry two labels (FIX FIRST and GATE BEFORE LAUNCH). NON-GOAL excludes the others.
The thresholds are constants at the top of `pipeline/triage.py`.

## What the recipe returns on the public data

| Rank | Pain | Decision | Evidence | Test |
|---|---|---|---|---|
| 1 | Sound quality | FIX FIRST, *verify* | -0.58 stars, 25.0% reach, top 3 in 99.5% of draws; precision 0.39 | 7,487 per arm |
| 2 | Pairing and connection drops | FIX FIRST | -0.63 stars, 14.8% reach, top 3 in 98.2% of draws | OTA holdout, 12,487 per arm |
| 3 | Earbud stops working | FIX FIRST + GATE BEFORE LAUNCH | -1.52 stars (CI -1.60 to -1.45); 5.9% to 13.6% with age (2.3x); top 3 in 83.6% of draws | Build-cohort comparison, 5,628 per arm |
| 4-7 | Fit, calls and mic, charging case, battery | WATCH | All cost stars (fit -0.42, battery -0.31) but none is stable in the top 3 or grows 1.5x with age (battery 9.7% to 10.8%) | |
| 8-10 | Touch controls, noise cancelling, app and firmware | NON-GOAL | Star CIs -0.09 to +0.04, -0.02 to +0.08, +0.11 to +0.24 | |

Noise cancelling also carries the *verify* flag (precision 0.13 on 4 test positives). This
matches the one-page [PRODUCT_SPEC.md](PRODUCT_SPEC.md): a reliability gate, link firmware,
and the same non-goals.

## Run the tool

```bash
# a team's own export, mapped to the six fields below
.venv/bin/python -I run.py triage reviews.jsonl --out triage/

# optional: engineering Effort estimates, a different fix efficacy, your own hand labels
.venv/bin/python -I run.py triage reviews.jsonl --effort effort.json --efficacy 0.3 \
    --labels my_labels.csv --out triage/

# re-run the public numbers from the cached scoring (seconds, reproduces results.json)
.venv/bin/python -I run.py triage ../_downloads/earbud-pain-roadmap/interim/scored.pkl --out triage/
```

**Input:** JSONL, one object per line, in the dataset's own review format:
`{parent_asin, user_id, rating, timestamp (ms), title, text}`. A support or return export only
needs mapping to these six fields; `rating` can be any 1-5 outcome score.

| Option | Meaning |
|---|---|
| `--effort effort.json` | `{theme: person-months}`; overrides the assumed Effort in `pipeline/prioritise.py` |
| `--efficacy 0.5` | assumed share of the pain a fix removes (sizes the test) |
| `--labels labels.csv` | hand labels (`text`, `labels`, `split`): thresholds are re-tuned on dev, confidence is test F1 |
| `--models models.pkl` | reuse a saved vectorizer and models, or save them there; useful for small exports |
| `--sample N` | random sample of N reviews (default: all) |

Without `--labels`, thresholds (0.40 theme, 0.25 negativity) and per-theme confidence come
from the public run's validation in `public/results.json`.

**Output:**
- `triage/triage.json`: the same per-theme schema as `results.json` `themes`, plus
  `decision`, `verify`, `age_ratio`, `fix_path` and `test`.
- `triage/triage.md`: a one-page ranked queue, one row per theme: rank, decision, reach with
  CI, stars lost with CI, age trend, RICE, top-3 stability, test type and owners per arm.

**How it is built.** `pipeline/triage.py` is a thin wrapper over the existing modules:
`prepare.prepare_frame` (dedupe, filters, sentence split), `classify.score` and
`classify.pain_matrix`, then `assemble.theme_table`, the same function that builds the
public `results.json`, so the two cannot drift. `tests/test_triage.py` checks that the tool
reproduces the shipped ranks and sample sizes, that the decision labels above come out of the
shipped results, and runs the command end to end on a 20,000-review slice of the real data.

## Week 1 on a real product line

- **Day 1.** Get one product's export (support tickets, return or warranty notes, or store
  reviews) with id, date, outcome and text, plus its ship date. Map it to the six input fields
  and run `triage` as-is for a first ranked queue.
- **Day 2.** Two people hand-label about 300 of the product's sentences. Re-tune the thresholds
  on dev with `--labels`, then report test F1 against keyword search. This closes the
  one-annotator limitation.
- **Day 3.** Replace the "months since first review" proxy with real age since activation or
  ship date. Re-run the ageing curves and the GATE BEFORE LAUNCH check.
- **Day 4.** With the hardware and firmware leads, replace the assumed Effort with their
  estimates (`--effort`) and re-run the effort sensitivity. Check whether review pains line up
  with return or warranty rates.
- **Day 5.** Hand over the ranked queue, this recipe, and a sized holdout for the top
  OTA-testable fix, plus a build-cohort plan for any hardware item. Items that rise with age go
  in as proposed reliability tests for the next launch gate.

## Caveats

- Effort and the 50% fix efficacy are assumptions. The effort draws bound the first; owners per
  arm scale roughly with 1/efficacy².
- The test type per theme (firmware or hardware) is also an engineering assumption
  (`FIX_PATH` in `pipeline/triage.py`).
- Sound-quality precision is 0.39, so its reach is probably overstated; that is why it carries
  the *verify* flag.
- These are public reviews, not support or return data. Rates describe reviews, not owners.

---
Built by Ibi Raheel, mechanical engineer building AI tools. More at [ibiraheel.com](https://ibiraheel.com).
