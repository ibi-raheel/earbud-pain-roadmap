# Product spec: next-generation true-wireless earbuds, reliability first

One page. All evidence comes from `public/results.json` (120,000 public reviews of 5,663
true-wireless earbud models, method in METHOD.md).

## Problem
Owners rate a model lower when an earbud **stops working**: the review loses 1.52 stars
compared with other reviews of the same model. That is 2.4 times the cost of any other pain.
It shows up in 10.1% of reviews overall, and its share more than doubles as a model ages
(5.9% in the first 3 months, 13.6% after 2 years). Reviewers who say when it happened put the
median at 2 months. Connectivity (14.8% of reviews, -0.63 stars) and sound quality (25.0%,
-0.58 stars) affect more people but cost less each time.

## Who has it
Everyday owners who wear earbuds for workouts, commutes and calls. The failures they name are
one bud dying, the case or bud no longer charging, and housings cracking after sweat or drops.

## Goals (12 months after launch)
1. Cut the share of reviews describing a dead or non-charging bud from 10.1% to 6% or less.
2. Cut connection-drop and pairing complaints from 14.8% to 11% or less.
3. Keep the 1-2 star review share below the current 24.2% baseline at every lifecycle stage,
   including 12+ months.

## Non-goals
Noise cancelling, touch-control and app changes. They are mentioned often, but once the model
is held fixed they cost no measurable stars.

## Requirements
| # | Requirement | Pain addressed | Evidence |
|---|---|---|---|
| R1 | 12-month reliability gate: drop, sweat-ingress and charge-cycle tests on bud and case, run before launch | Failure, case | Failure share doubles by 24 months; "stopped charging" is the second most common failure phrase |
| R2 | Per-bud charge telemetry and a fault code when one bud stops charging in the case | Case, battery | Charging-case pain 7.9%; battery 10.1%, rising from 9.7% to 10.8% with age |
| R3 | Bud-to-bud link and reconnection firmware, with field logging of drop events | Connectivity | 14.8% reach, -0.63 stars, lowest assumed effort (3 person-months) |
| R4 | Fit kit with more tip sizes and an in-app fit test at setup | Fit | 14.1% reach, -0.42 stars, worst in the first 3 months (15.7%) |

## Prioritisation
RICE ranking: sound quality (1.88), connectivity (1.70), failure (1.08). The same three stay
in the top 3 in 99%, 98% and 84% of runs that vary the assumed Effort between half and double.
Sound ranks first only because of reach, and that theme has the weakest detection precision
(0.39). The spec therefore leads with failure and connectivity, where the evidence per affected
owner is strongest.

## First experiment
Run a holdout on the connection firmware (R3) through a staged OTA rollout. It is the cheapest top-3 fix to
randomise after launch. The baseline 1-2 star rate is 24.2%; the target is 22.6%,
assuming half the connectivity pain is removed. At alpha 0.05 and power 0.8 that needs **12,487
owners per arm**. The same sizing gives 7,487 per arm for sound quality and 5,628 for failure.
Failure is a hardware change, so it is tested by comparing build cohorts, not by randomisation.
Use the same metric on support contacts, where base rates are higher and the n is smaller.

## Risks and open questions
- Reviews are not support data. Validate on warranty returns and support tickets first.
- Effort figures are assumptions. Engineering estimates replace them before committing.
- A second annotator should re-label the validation set (320 sentences, one labeller).
