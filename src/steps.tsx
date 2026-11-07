import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import {
  EFFORT_WHY,
  GROUPS,
  METHOD_NAMES,
  Results,
  SHORT,
  Theme,
  fmt,
  nPerArm,
  pct,
  riceScore,
  stars,
  targetP2,
  toneOf,
} from './data'
import { Details, Pin, Step, Tape, tilt } from './ui'

function useWidth<T extends HTMLElement>(fallback = 320) {
  const ref = useRef<T>(null)
  const [w, setW] = useState(fallback)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    setW(el.clientWidth)
    const ro = new ResizeObserver(([e]) => setW(Math.round(e.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return { ref, w }
}

/* ───────────────────────── 1. The pile ───────────────────────── */

export function StepPile({ d }: { d: Results }) {
  const ds = d.dataset
  const rows = [
    { n: ds.raw, label: 'reviews of true-wireless earbuds, out of the whole electronics file' },
    { n: ds.after_exact_dupes, label: 'after removing exact duplicates' },
    { n: ds.after_text_dupes, label: 'after removing the same text posted on colour variants' },
    { n: ds.after_date_and_length, label: `from 2015 on, with real text (${fmt(ds.items)} models)` },
    { n: ds.sample_reviews, label: `random sample, ${fmt(ds.sample_items)} models, ${fmt(ds.sample_sentences)} sentences`, keep: true },
  ]
  return (
    <Step
      id="pile"
      n={1}
      title={`Start with ${fmt(ds.sample_reviews)} real reviews`}
      lede="Public reviews of wireless earbuds, cleaned and sampled. Every sentence gets read by a model in the next step."
    >
      <div className="sheet pile">
        <Pin className="pin-tl" />
        <ol className="strips">
          {rows.map((r, i) => (
            <li key={i} className={r.keep ? 'strip keep' : 'strip'} style={{ ['--i' as string]: i }}>
              <span className="strip-bar" style={{ width: `${Math.max(14, (100 * r.n) / ds.raw)}%` }}>
                <b className="num">{fmt(r.n)}</b>
              </span>
              <span className="strip-label">{r.label}</span>
            </li>
          ))}
        </ol>
        <p className="foot-note">
          Bar length is the count, to scale. The sample keeps the run on a laptop; bootstrap intervals are already about ±1 point.
        </p>
      </div>
    </Step>
  )
}

/* ───────────────────────── 2. Affinity wall ───────────────────────── */

// Hide tokenisation fragments ("don t") and phrases that only name the product ("ear buds") or the review itself.
const NOISE = /(^|\s)\w(\s|$)|i'll|^ear buds?$|^bluetooth (headphones|earbuds)$|^updated review$/
const cleanBigrams = (t: Theme) => t.top_bigrams.filter(([p]) => !NOISE.test(p)).slice(0, 5)

export function StepWall({ d }: { d: Results }) {
  const byKey = useMemo(() => Object.fromEntries(d.themes.map((t) => [t.key, t])), [d])
  const [sel, setSel] = useState('failure')
  const quotesRef = useRef<HTMLDivElement>(null)
  const pick = (k: string) => {
    setSel(k)
    // On one-column layouts the quote cards sit below the wall; bring them into view.
    const el = quotesRef.current
    if (el && window.matchMedia('(max-width: 899px)').matches) {
      const r = el.getBoundingClientRect()
      if (r.top > window.innerHeight * 0.7) {
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
        el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
      }
    }
  }
  const t = byKey[sel]
  const topics = d.topics.filter((x) => x.theme === sel)
  return (
    <Step
      id="wall"
      n={2}
      title="What owners complain about"
      lede={
        <>
          Ten pain clusters. Each square note is 1% of reviews; {pct(d.overall.any_pain_share)} of reviews hold at least one
          pain. Tap a cluster to see the phrases owners use most.
        </>
      }
    >
      <div className="wall">
        <div className="clusters">
          {GROUPS.map((g) => (
            <div className="group" key={g.id}>
              <h3 className={`group-title tone-${g.tone}`} style={{ rotate: `${tilt(g.id, 1.5)}deg` }}>
                {g.title}
              </h3>
              {g.keys.map((k) => {
                const th = byKey[k]
                const count = Math.round(th.share * 100)
                return (
                  <button
                    key={k}
                    className="cluster"
                    aria-pressed={sel === k}
                    onClick={() => pick(k)}
                    aria-label={`${th.label}: ${pct(th.share)} of reviews`}
                  >
                    <span className="cluster-name">{SHORT[k]}</span>
                    <span className="notes" aria-hidden="true">
                      {Array.from({ length: count }, (_, i) => (
                        <span
                          key={i}
                          className={`sq tone-${g.tone}`}
                          style={{ rotate: `${tilt(k + i, 7)}deg`, ['--i' as string]: i }}
                        />
                      ))}
                    </span>
                    <span className="cluster-share num">{pct(th.share)}</span>
                  </button>
                )
              })}
            </div>
          ))}
        </div>

        <div ref={quotesRef} className="quotes-anchor">
        <aside className="quotes" aria-live="polite" key={sel}>
          <div className={`quote-head tone-${toneOf(sel)}`}>
            <Tape className="tape-top" />
            <p className="qh-name">{t.label}</p>
            <p className="qh-stat">
              <b className="num">{pct(t.share)}</b> of reviews <span className="muted num">(95% CI {pct(t.share_lo)}–{pct(t.share_hi)})</span>
            </p>
          </div>
          <p className="quotes-cap">Phrases owners used most in these complaints</p>
          <ul className="slips">
            {cleanBigrams(t).map(([p, n], i) => (
              <li key={p} className="slip" style={{ rotate: `${tilt(sel + p, 0.9)}deg`, ['--i' as string]: i }}>
                <span className="slip-text">“{p}”</span>
                <span className="slip-n num">{fmt(n)} sentences</span>
              </li>
            ))}
          </ul>
          {topics.length > 0 && (
            <p className="topic-line">
              <span className="muted">Unsupervised topic words that landed here: </span>
              {topics
                .slice(0, 2)
                .map((x) => x.top_terms.slice(0, 5).join(', '))
                .join(' · ')}
            </p>
          )}
        </aside>
        </div>
      </div>
      <Details>
        <p>
          The dataset is a research release with no stated licence, so the page ships only aggregates: phrase counts, not
          review text. Two-word phrases are counted over the sentences flagged for that pain; tokenisation fragments (single
          letters) and phrases that only name the product, such as “ear buds”, are hidden. Groupings on the wall are for reading, not a result.
        </p>
        <table className="tbl">
          <thead>
            <tr>
              <th>Pain</th>
              <th className="r">Share of reviews</th>
              <th className="r">95% CI</th>
              <th className="r">Share of 1–2★ reviews</th>
            </tr>
          </thead>
          <tbody>
            {d.themes.map((x) => (
              <tr key={x.key}>
                <td>{x.label}</td>
                <td className="r num">{pct(x.share)}</td>
                <td className="r num">
                  {pct(x.share_lo)}–{pct(x.share_hi)}
                </td>
                <td className="r num">{pct(x.share_of_low_reviews)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">
          The ten themes were checked against an unsupervised pass (TF-IDF + NMF, 20 topics on 1–2★ sentences). Topics that
          matched no theme were purchase regret and value for money: outcomes, not product pains.
        </p>
      </Details>
    </Step>
  )
}

/* ───────────────────────── 3. Model vs baseline ───────────────────────── */

export function StepModel({ d }: { d: Results }) {
  const v = d.validation
  const chosen = v.methods[v.chosen]
  const [against, setAgainst] = useState<'keyword_baseline' | 'seed_lexicon_plus_negativity'>('keyword_baseline')
  const base = v.methods[against]
  const rows = [...d.themes].sort((a, b) => chosen.per_theme[b.key].f1 - chosen.per_theme[a.key].f1)
  const { ref, w } = useWidth<HTMLDivElement>()
  const narrow = w < 520
  const L = narrow ? 126 : 170
  const R = 44
  const rowH = 30
  const H = rows.length * rowH + 34
  const x = (f: number) => L + f * (w - L - R)
  const wins = rows.filter((t) => chosen.per_theme[t.key].f1 > base.per_theme[t.key].f1).length
  return (
    <Step
      id="model"
      n={3}
      title="The trained model, checked by hand"
      lede={
        <>
          A classifier reads each sentence for topic and for complaint. Scored on {v.n_test} sentences labelled by hand, it
          lifts F1 from <b className="num">{chosen && v.methods.keyword_baseline.micro.f1.toFixed(2)}</b> for keyword search to{' '}
          <b className="num">{chosen.micro.f1.toFixed(2)}</b>.
        </>
      }
    >
      <div className="sheet graph">
        <Pin tone="blue" className="pin-tr" />
        <div className="seg" role="radiogroup" aria-label="Compare the trained model against">
          <span className="seg-label">Compare with</span>
          {(['keyword_baseline', 'seed_lexicon_plus_negativity'] as const).map((k) => (
            <button key={k} role="radio" aria-checked={against === k} onClick={() => setAgainst(k)}>
              {k === 'keyword_baseline' ? 'Keyword search' : 'Word list + complaint gate'}
            </button>
          ))}
        </div>
        <div className="legend">
          <span>
            <svg width="14" height="14" aria-hidden="true">
              <circle cx="7" cy="7" r="5" className="dot-base" />
            </svg>
            {METHOD_NAMES[against]}
          </span>
          <span>
            <svg width="14" height="14" aria-hidden="true">
              <circle cx="7" cy="7" r="5.5" className="dot-model" />
            </svg>
            Trained classifier
          </span>
        </div>
        <div ref={ref} className="chart">
          <svg width={w} height={H} role="img" aria-label={`F1 per pain theme, trained classifier versus ${METHOD_NAMES[against]}`}>
            {[0, 0.25, 0.5, 0.75, 1].map((g) => (
              <g key={g}>
                <line x1={x(g)} x2={x(g)} y1={4} y2={H - 26} className="grid" />
                <text x={x(g)} y={H - 8} className="tick" textAnchor="middle">
                  {g === 0 ? '0' : g.toFixed(2)}
                </text>
              </g>
            ))}
            {rows.map((t, i) => {
              const y = 18 + i * rowH
              const a = base.per_theme[t.key].f1
              const b = chosen.per_theme[t.key].f1
              const better = b >= a
              return (
                <g key={t.key} className="row">
                  <title>{`${t.label}: classifier F1 ${b.toFixed(2)}, ${METHOD_NAMES[against]} ${a.toFixed(2)}, ${chosen.per_theme[t.key].support} test positives`}</title>
                  <rect x={0} y={y - rowH / 2} width={w} height={rowH} className="hit" />
                  <text x={L - 12} y={y + 4} className="row-label" textAnchor="end">
                    {SHORT[t.key]}
                  </text>
                  <line x1={x(a)} x2={x(b)} y1={y} y2={y} className={better ? 'link up' : 'link down'} />
                  <circle cx={x(a)} cy={y} r={5} className="dot-base" />
                  <circle cx={x(b)} cy={y} r={5.5} className="dot-model" />
                  <text x={better ? x(b) + 10 : x(b) - 10} y={y + 4} className={better ? 'val' : 'val strong'} textAnchor={better ? 'start' : 'end'}>
                    {b.toFixed(2)}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>
        <p className="verdict">
          {against === 'keyword_baseline' ? (
            <>
              Better on {wins} of 10 pains. The big gain comes from the complaint gate: it tells “battery life is great” from
              “battery dies in an hour”.
            </>
          ) : (
            <>
              Honest result: the plain word list with the same gate scored{' '}
              <b className="num">{v.methods.seed_lexicon_plus_negativity.micro.f1.toFixed(2)}</b> on test. The classifier was
              picked on the dev split ({v.methods.classifier_plus_negativity && v.dev_micro.classifier_plus_negativity.f1.toFixed(3)} vs{' '}
              {v.dev_micro.seed_lexicon_plus_negativity.f1.toFixed(3)}) and not re-picked after seeing test. With ~200 sentences
              the gap is inside noise.
            </>
          )}
        </p>
      </div>
      <Details>
        <table className="tbl">
          <thead>
            <tr>
              <th>Method (test, {v.n_test} sentences)</th>
              <th className="r">Precision</th>
              <th className="r">Recall</th>
              <th className="r">F1</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(v.methods).map(([k, m]) => (
              <tr key={k} className={k === v.chosen ? 'hl' : ''}>
                <td>{METHOD_NAMES[k] ?? k}</td>
                <td className="r num">{m.micro.precision.toFixed(2)}</td>
                <td className="r num">{m.micro.recall.toFixed(2)}</td>
                <td className="r num">{m.micro.f1.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p>
          A sentence is a pain for theme <i>k</i> when the theme model says so (P ≥ {v.t_theme}) <b>and</b> the complaint
          model says it is negative (P ≥ {v.t_neg}). Theme models are logistic regressions on TF-IDF word 1–2 grams, trained on
          weak labels; the complaint model learned from 1★ vs 5★ sentences. Thresholds were set on {v.n_dev} dev sentences.
          Per-theme F1 becomes the Confidence term in the roadmap, so weakly validated themes are discounted.
        </p>
        <Confusion d={d} />
      </Details>
    </Step>
  )
}

function Confusion({ d }: { d: Results }) {
  const c = d.validation.confusion
  const max = Math.max(...c.matrix.flat())
  const name = (k: string) => (k === 'none' ? 'none' : SHORT[k] ?? k)
  return (
    <div className="conf-wrap">
      <p className="muted">Confusion on test sentences (rows: hand label, columns: model). Darker cells hold more sentences.</p>
      <div className="conf-scroll">
        <table className="conf">
          <thead>
            <tr>
              <th />
              {c.labels.map((l) => (
                <th key={l} scope="col">
                  <span>{name(l)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {c.matrix.map((row, i) => (
              <tr key={i}>
                <th scope="row">{name(c.labels[i])}</th>
                {row.map((v, j) => (
                  <td key={j} style={{ ['--a' as string]: v ? 0.12 + 0.88 * Math.sqrt(v / max) : 0 }} className={v / max > 0.45 ? 'dark' : ''}>
                    {v || ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ───────────────────────── 4. Star cost ───────────────────────── */

export function StepStars({ d }: { d: Results }) {
  const rows = [...d.themes].sort((a, b) => a.star_delta - b.star_delta)
  const [worst, next] = rows
  const ratio = worst.star_delta / next.star_delta
  const { ref, w } = useWidth<HTMLDivElement>()
  const narrow = w < 520
  const L = narrow ? 126 : 170
  const R = 20
  const rowH = 32
  const H = rows.length * rowH + 40
  const lo = -1.75
  const hi = 0.5
  const x = (v: number) => L + ((v - lo) / (hi - lo)) * (w - L - R)
  const f = worst
  return (
    <Step
      id="stars"
      n={4}
      title="Which pains cost the most stars"
      lede={
        <>
          Compared with other reviews of the same model, a dead earbud costs <b className="num">{stars(f.star_delta)}</b> stars.
          That is {ratio.toFixed(1)}× the next-worst pain.
        </>
      }
    >
      <div className="sheet graph">
        <Pin className="pin-tl" />
        <div ref={ref} className="chart">
          <svg width={w} height={H} role="img" aria-label="Stars lost per pain theme with 95% confidence intervals">
            {[-1.5, -1, -0.5, 0].map((g) => (
              <g key={g}>
                <line x1={x(g)} x2={x(g)} y1={6} y2={H - 28} className={g === 0 ? 'zero' : 'grid'} />
                <text x={x(g)} y={H - 10} className="tick" textAnchor="middle">
                  {g === 0 ? '0' : '−' + Math.abs(g).toFixed(1)}
                </text>
              </g>
            ))}
            <text x={x(0) + 6} y={14} className="tick">
              no effect
            </text>
            {rows.map((t, i) => {
              const y = 26 + i * rowH
              const top = t.key === f.key
              return (
                <g key={t.key} className="row">
                  <title>{`${t.label}: ${stars(t.star_delta)} stars (95% CI ${stars(t.star_delta_lo)} to ${stars(t.star_delta_hi)})`}</title>
                  <rect x={0} y={y - rowH / 2} width={w} height={rowH} className="hit" />
                  <text x={L - 12} y={y + 4} className={top ? 'row-label strong' : 'row-label'} textAnchor="end">
                    {SHORT[t.key]}
                  </text>
                  <rect
                    x={Math.min(x(0), x(t.star_delta))}
                    y={y - 7}
                    width={Math.abs(x(t.star_delta) - x(0))}
                    height={14}
                    className={top ? 'cost-bar top' : 'cost-bar'}
                  />
                  <line x1={x(t.star_delta_lo)} x2={x(t.star_delta_hi)} y1={y} y2={y} className="ci" />
                  {top ? (
                    <circle cx={x(t.star_delta)} cy={y} r={9} className="sticker" />
                  ) : (
                    <circle cx={x(t.star_delta)} cy={y} r={5} className="dot-model" />
                  )}
                  <text
                    x={t.star_delta < 0 && !top ? x(t.star_delta_lo) - 10 : x(t.star_delta_hi) + (top ? 14 : 10)}
                    y={y + 4}
                    className={top ? 'val strong' : 'val'}
                    textAnchor={t.star_delta < 0 && !top ? 'end' : 'start'}
                  >
                    {stars(t.star_delta)}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>
        <p className="verdict">
          {pct(f.p_low_given_pain, 0)} of those reviews are 1–2 stars, against {pct(f.p_low_given_none, 0)} without it. Touch
          controls, noise cancelling and app issues cost nothing measurable once the model is held fixed.
        </p>
      </div>
      <Details>
        <p>
          Stars lost is the coefficient from a regression of stars on all ten pains with a fixed effect per earbud model and
          review length as a control, standard errors clustered by model ({fmt(d.overall.ols_n)} reviews, {fmt(d.overall.ols_items)}{' '}
          models). It is a within-model association, not the causal effect of a fix.
        </p>
        <table className="tbl">
          <thead>
            <tr>
              <th>Pain</th>
              <th className="r">Stars</th>
              <th className="r">95% CI</th>
              <th className="r">1–2★ with</th>
              <th className="r">1–2★ without</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.key}>
                <td>{t.label}</td>
                <td className="r num">{stars(t.star_delta)}</td>
                <td className="r num">
                  {stars(t.star_delta_lo)} to {stars(t.star_delta_hi)}
                </td>
                <td className="r num">{pct(t.p_low_given_pain)}</td>
                <td className="r num">{pct(t.p_low_given_none)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p>
          <b>It gets worse with age.</b> Share of reviews describing a dead earbud, by months since the model’s first review:
        </p>
        <table className="tbl">
          <thead>
            <tr>
              {d.lifecycle_bins.map((b) => (
                <th key={b} className="r">
                  {b}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {f.lifecycle.map((v, i) => (
                <td key={i} className="r num">
                  {pct(v)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
        <p className="muted">
          Where reviewers say when it died (n = {fmt(f.time_to_complaint.n)}), the median is {f.time_to_complaint.median_months}{' '}
          months (quartiles {f.time_to_complaint.p25}–{f.time_to_complaint.p75}).
        </p>
      </Details>
    </Step>
  )
}

/* ───────────────────────── 5. Roadmap ───────────────────────── */

type W = { r: number; i: number; c: number; e: number }
const W0: W = { r: 1, i: 1, c: 1, e: 1 }

export function StepRoadmap({ d }: { d: Results }) {
  const [wt, setWt] = useState<W>(W0)
  const ranked = useMemo(
    () =>
      d.themes
        .map((t) => ({ t, s: riceScore(t, wt) }))
        .sort((a, b) => b.s - a.s || a.t.rank - b.t.rank),
    [d, wt],
  )
  const isDefault = wt.r === 1 && wt.i === 1 && wt.c === 1 && wt.e === 1
  return (
    <Step
      id="roadmap"
      n={5}
      title="Turn pains into a roadmap"
      lede="RICE: reach × stars lost × model confidence ÷ effort. Drag the weights to see how much the order leans on each."
    >
      <div className="roadmap">
        <Grid d={d} />
        <div className="sheet board">
          <Pin tone="green" className="pin-tr" />
          <RankList ranked={ranked} />
          <Weights wt={wt} setWt={setWt} isDefault={isDefault} />
        </div>
      </div>
      <Details>
        <p>
          Reach is the share of reviews (in points), Impact the stars lost (floored at 0), Confidence the detector’s test F1 for
          that pain. <b>Effort is an assumption</b> in engineering person-months. Weights raise each term to a power; at 1 the
          scores match the pipeline exactly.
        </p>
        <table className="tbl">
          <thead>
            <tr>
              <th>Pain</th>
              <th className="r">Effort (pm)</th>
              <th>Why that effort</th>
              <th className="r">Top 3 when effort varies</th>
            </tr>
          </thead>
          <tbody>
            {d.themes.map((t) => (
              <tr key={t.key}>
                <td>{t.label}</td>
                <td className="r num">{t.effort_pm}</td>
                <td>{EFFORT_WHY[t.key]}</td>
                <td className="r num">{pct(t.effort_sensitivity.p_top3, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">
          Sensitivity: each effort scaled independently by a log-uniform factor between ½ and 2, 5,000 draws. Sound leads on
          reach alone, and its detector precision is the lowest of the big themes ({d.themes.find((t) => t.key === 'sound_quality')!.precision.toFixed(2)}), so
          its reach is likely overstated.
        </p>
      </Details>
    </Step>
  )
}

function Weights({ wt, setWt, isDefault }: { wt: W; setWt: (w: W) => void; isDefault: boolean }) {
  const items: { k: keyof W; label: string }[] = [
    { k: 'r', label: 'Reach' },
    { k: 'i', label: 'Stars lost' },
    { k: 'c', label: 'Confidence' },
    { k: 'e', label: 'Effort' },
  ]
  return (
    <fieldset className="weights">
      <legend>Weights</legend>
      {items.map(({ k, label }) => (
        <label key={k} className="wt">
          <span className="wt-name">{label}</span>
          <input
            type="range"
            min={0}
            max={2}
            step={0.25}
            value={wt[k]}
            onChange={(e) => setWt({ ...wt, [k]: Number(e.target.value) })}
            aria-valuetext={`${label} weight ${wt[k]}`}
          />
          <span className="wt-val num">{wt[k].toFixed(2)}</span>
        </label>
      ))}
      <button className="reset" onClick={() => setWt(W0)} disabled={isDefault}>
        Reset
      </button>
    </fieldset>
  )
}

function RankList({ ranked }: { ranked: { t: Theme; s: number }[] }) {
  const listRef = useRef<HTMLOListElement>(null)
  const prev = useRef<Map<string, number>>(new Map())
  const order = ranked.map((r) => r.t.key).join()
  useLayoutEffect(() => {
    const el = listRef.current
    if (!el) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const items = Array.from(el.querySelectorAll<HTMLElement>('[data-k]'))
    const next = new Map<string, number>()
    items.forEach((it) => next.set(it.dataset.k!, it.getBoundingClientRect().top))
    if (!reduce) {
      items.forEach((it) => {
        const before = prev.current.get(it.dataset.k!)
        const now = next.get(it.dataset.k!)!
        if (before !== undefined && before !== now) {
          it.animate([{ transform: `translateY(${before - now}px)` }, { transform: 'translateY(0)' }], {
            duration: 260,
            easing: 'cubic-bezier(0.77, 0, 0.175, 1)',
          })
        }
      })
    }
    prev.current = next
  }, [order])
  const max = Math.max(...ranked.map((r) => r.s), 1e-9)
  const band = (i: number) => (i < 3 ? 'Now' : i < 6 ? 'Next' : 'Later')
  return (
    <ol className="ranks" ref={listRef}>
      {ranked.map(({ t, s }, i) => (
        <li key={t.key} data-k={t.key} className={`rank band-${band(i).toLowerCase()}`}>
          {(i === 0 || i === 3 || i === 6) && <span className="band-tag">{band(i)}</span>}
          <span className="rank-n num">{i + 1}</span>
          <span className={`rank-note tone-${toneOf(t.key)}`}>{SHORT[t.key]}</span>
          <span className="rank-bar" aria-hidden="true">
            <span style={{ transform: `scaleX(${s / max})` }} />
          </span>
          <span className="rank-s num">{s < 0.005 ? '0' : s.toFixed(2)}</span>
        </li>
      ))}
    </ol>
  )
}

// Label placement to avoid collisions between neighbouring points (layout only).
const GRID_LABEL: Record<string, { dx: number; dy: number; a: 'start' | 'end' | 'middle' }> = {
  sound_quality: { dx: 0, dy: -15, a: 'middle' },
  connectivity: { dx: 0, dy: -15, a: 'middle' },
  failure: { dx: 13, dy: 4, a: 'start' },
  fit_comfort: { dx: 11, dy: 5, a: 'start' },
  battery: { dx: 9, dy: 17, a: 'start' },
  call_mic: { dx: -30, dy: -12, a: 'start' },
  charging_case: { dx: -9, dy: 17, a: 'end' },
}

function Grid({ d }: { d: Results }) {
  const { ref, w } = useWidth<HTMLDivElement>()
  const H = Math.round(Math.min(560, Math.max(320, w * 1.05)))
  const pad = { l: 40, r: 16, t: 18, b: 40 }
  const maxR = 28
  const maxI = 1.7
  const x = (r: number) => pad.l + (r / maxR) * (w - pad.l - pad.r)
  const y = (i: number) => H - pad.b - (i / maxI) * (H - pad.t - pad.b)
  const midR = 12
  const midI = 0.5
  return (
    <div className="sheet gridsheet">
      <Tape className="tape-tl" />
      <Tape className="tape-br" />
      <div ref={ref} className="chart">
        <svg width={w} height={H} role="img" aria-label="Prioritisation grid: reach against stars lost">
          <defs>
            <filter id="rough" x="-5%" y="-5%" width="110%" height="110%">
              <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="4" />
              <feDisplacementMap in="SourceGraphic" scale="2.2" />
            </filter>
          </defs>
          <g filter="url(#rough)" className="marker-lines">
            <line x1={pad.l} y1={H - pad.b} x2={w - pad.r} y2={H - pad.b} />
            <line x1={pad.l} y1={H - pad.b} x2={pad.l} y2={pad.t} />
            <line x1={x(midR)} y1={H - pad.b} x2={x(midR)} y2={pad.t} className="dash" />
            <line x1={pad.l} y1={y(midI)} x2={w - pad.r} y2={y(midI)} className="dash" />
          </g>
          <text x={w - pad.r} y={pad.t + 4} className="quad" textAnchor="end">
            many owners, big hit
          </text>
          {w >= 480 && (
            <text x={pad.l + 8} y={pad.t + 4} className="quad">
              few owners, big hit
            </text>
          )}
          <text x={(pad.l + w - pad.r) / 2} y={H - 10} className="axis" textAnchor="middle">
            Reach: % of reviews →
          </text>
          <text x={14} y={(pad.t + H - pad.b) / 2} className="axis" textAnchor="middle" transform={`rotate(-90 14 ${(pad.t + H - pad.b) / 2})`}>
            Stars lost →
          </text>
          {[0, 10, 20].map((r) => (
            <text key={r} x={x(r)} y={H - pad.b + 16} className="tick" textAnchor="middle">
              {r}
            </text>
          ))}
          {[0, 0.5, 1, 1.5].map((i) => (
            <text key={i} x={pad.l - 8} y={y(i) + 4} className="tick" textAnchor="end">
              {i}
            </text>
          ))}
          {d.themes.map((t) => {
            const I = Math.max(0, -t.star_delta)
            const cx = x(t.share * 100)
            const cy = y(I)
            const top3 = t.rank <= 3
            const pos = GRID_LABEL[t.key]
            const anchor = pos ? pos.a : cx < w * 0.62 ? 'start' : 'end'
            const right = anchor !== 'end'
            const lx = cx + (pos?.dx ?? (right ? 13 : -13))
            const ly = cy + (pos?.dy ?? 4)
            return (
              <g key={t.key} className="pt">
                <title>{`${t.label}: ${pct(t.share)} of reviews, ${stars(t.star_delta)} stars, RICE ${t.rice.toFixed(2)}`}</title>
                <circle cx={cx} cy={cy} r={top3 ? 8 : 5} className={top3 ? 'sticker' : 'dot-model'} />
                {(top3 || I > 0.2) && (
                  <text x={lx} y={ly} className={top3 ? 'pt-label strong' : 'pt-label'} textAnchor={anchor}>
                    {SHORT[t.key]}
                  </text>
                )}
              </g>
            )
          })}
        </svg>
      </div>
      <p className="foot-note">Orange dot stickers mark the RICE top three at default weights.</p>
    </div>
  )
}

/* ───────────────────────── 6. Experiment ───────────────────────── */

export function StepExperiment({ d }: { d: Results }) {
  const top = [...d.themes].sort((a, b) => a.rank - b.rank).slice(0, 3)
  const [key, setKey] = useState(d.experiment.theme)
  const [eff, setEff] = useState(d.experiment.efficacy_assumption)
  const [weekly, setWeekly] = useState(1000)
  const t = top.find((x) => x.key === key) ?? top[0]
  const p1 = d.overall.low_star_share
  const p2 = targetP2(p1, t, eff)
  const n = nPerArm(p1, p2)
  const weeks = Math.ceil(n / weekly)
  return (
    <Step
      id="experiment"
      n={6}
      title="Size the test for the top bet"
      lede="The metric is the share of 1–2 star reviews. Say how much of the pain a fix removes, and the card works out how many owners each arm needs."
    >
      <div className="exp">
        <div className="sheet expcard">
          <Pin className="pin-tl" />
          <div className="seg" role="radiogroup" aria-label="Pain to test">
            <span className="seg-label">Test a fix for</span>
            {top.map((x) => (
              <button key={x.key} role="radio" aria-checked={key === x.key} onClick={() => setKey(x.key)}>
                {SHORT[x.key]}
              </button>
            ))}
          </div>
          <label className="slider">
            <span className="sl-head">
              <span>Fix removes</span>
              <b className="num">{Math.round(eff * 100)}% of the pain</b>
            </span>
            <input type="range" min={0.1} max={1} step={0.05} value={eff} onChange={(e) => setEff(Number(e.target.value))} />
            <span className="sl-hint">assumption; the pipeline uses {Math.round(d.experiment.efficacy_assumption * 100)}%</span>
          </label>
          <label className="slider">
            <span className="sl-head">
              <span>Owners you can enrol</span>
              <b className="num">{fmt(weekly)} per arm a week</b>
            </span>
            <input type="range" min={250} max={10000} step={250} value={weekly} onChange={(e) => setWeekly(Number(e.target.value))} />
            <span className="sl-hint">assumption; set it to your rollout rate</span>
          </label>
          <dl className="readout">
            <div>
              <dt>1–2★ share now</dt>
              <dd className="num">{pct(p1)}</dd>
            </div>
            <div>
              <dt>Target</dt>
              <dd className="num">{pct(p2)}</dd>
            </div>
            <div className="big">
              <dt>Owners per arm</dt>
              <dd className="num">{fmt(n)}</dd>
            </div>
            <div className="big">
              <dt>Duration</dt>
              <dd className="num">
                {weeks} {weeks === 1 ? 'week' : 'weeks'}
              </dd>
            </div>
          </dl>
          <p className="foot-note">Two-sided, α = {d.experiment.alpha}, power = {d.experiment.power}.</p>
        </div>
        <PowerCurve p1={p1} t={t} eff={eff} />
      </div>
      <Details>
        <p>Worked by hand for the shipped case ({d.experiment.label}, half the pain removed):</p>
        <pre className="calc">{`p1 = ${p1.toFixed(5)}
p2 = p1 − ${d.experiment.efficacy_assumption} × reach × (P(1–2★ | pain) − P(1–2★ | no pain))
   = ${d.experiment.target_p2.toFixed(5)}
n  = (z₀.₉₇₅ + z₀.₈₀)² × [p1(1−p1) + p2(1−p2)] / (p1 − p2)²
   = ${fmt(d.experiment.n_per_arm_formula)} per arm   (statsmodels: ${fmt(d.experiment.n_per_arm_statsmodels)})`}</pre>
        <p>
          Sample size grows with roughly 1 / efficacy², which is why the curve climbs so fast on the left. A fix to “stops
          working” is a hardware change, so it is compared across build cohorts rather than randomised; connection firmware can
          go out as a staged update with a holdout.
        </p>
        <table className="tbl">
          <thead>
            <tr>
              <th>Pain</th>
              <th className="r">Target at {Math.round(d.experiment.efficacy_assumption * 100)}%</th>
              <th className="r">Owners per arm</th>
            </tr>
          </thead>
          <tbody>
            {top.map((x) => (
              <tr key={x.key}>
                <td>{x.label}</td>
                <td className="r num">{pct(x.experiment_p2)}</td>
                <td className="r num">{fmt(x.experiment_n_per_arm)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Details>
    </Step>
  )
}

function PowerCurve({ p1, t, eff }: { p1: number; t: Theme; eff: number }) {
  const { ref, w } = useWidth<HTMLDivElement>()
  const H = 300
  const pad = { l: 58, r: 18, t: 20, b: 42 }
  const es = Array.from({ length: 37 }, (_, i) => 0.1 + i * 0.025)
  const ns = es.map((e) => nPerArm(p1, targetP2(p1, t, e)))
  // Log scale: n grows roughly with 1 / efficacy², so a linear axis would hide the right half.
  const lo = 1000
  const cap = 1_000_000
  const x = (e: number) => pad.l + ((e - 0.1) / 0.9) * (w - pad.l - pad.r)
  const y = (n: number) =>
    H - pad.b - ((Math.log10(Math.min(Math.max(n, lo), cap)) - 3) / (Math.log10(cap) - 3)) * (H - pad.t - pad.b)
  const path = es.map((e, i) => `${i ? 'L' : 'M'}${x(e).toFixed(1)},${y(ns[i]).toFixed(1)}`).join('')
  const n = nPerArm(p1, targetP2(p1, t, eff))
  return (
    <div className="sheet graph curve">
      <Tape className="tape-top" />
      <p className="chart-title">Owners per arm vs how much the fix removes</p>
      <p className="chart-sub">Log scale. Halve the effect and the test needs about four times the owners.</p>
      <div ref={ref} className="chart">
        <svg width={w} height={H} role="img" aria-label={`Required owners per arm as fix efficacy varies, for ${t.label}`}>
          <defs>
            <clipPath id="plot">
              <rect x={pad.l} y={pad.t - 4} width={w - pad.l - pad.r} height={H - pad.t - pad.b + 4} />
            </clipPath>
          </defs>
          {[1000, 10000, 100000, 1000000].map((g) => (
            <g key={g}>
              <line x1={pad.l} x2={w - pad.r} y1={y(g)} y2={y(g)} className="grid" />
              <text x={pad.l - 8} y={y(g) + 4} className="tick" textAnchor="end">
                {g >= 1e6 ? '1M' : `${g / 1000}k`}
              </text>
            </g>
          ))}
          {[0.25, 0.5, 0.75, 1].map((e) => (
            <text key={e} x={x(e)} y={H - pad.b + 18} className="tick" textAnchor="middle">
              {Math.round(e * 100)}%
            </text>
          ))}
          <text x={(pad.l + w - pad.r) / 2} y={H - 6} className="axis" textAnchor="middle">
            Share of the pain removed
          </text>
          <path d={path} className="curve-line" clipPath="url(#plot)" />
          <line x1={x(eff)} x2={x(eff)} y1={y(n)} y2={H - pad.b} className="drop" />
          <circle cx={x(eff)} cy={y(n)} r={8} className="sticker" />
          <text
            x={x(eff) + (x(eff) > w * 0.6 ? -14 : 14)}
            y={Math.max(pad.t + 10, y(n) - 10)}
            className="val strong"
            textAnchor={x(eff) > w * 0.6 ? 'end' : 'start'}
          >
            {n > cap ? `${fmt(n)} (off chart)` : fmt(n)}
          </text>
        </svg>
      </div>
    </div>
  )
}

/* ───────────────────────── 7. How we know ───────────────────────── */

export function StepKnow({ d }: { d: Results }) {
  const v = d.validation
  const checks = [
    `${v.n_dev + v.n_test} sentences labelled by hand with stars and model scores hidden; ${v.n_dev} to tune, ${v.n_test} held out for every score on this page.`,
    'Confidence intervals resample whole earbud models, because reviews of one model are not independent.',
    'The fixed-effects regression recovers planted coefficients on synthetic data before it touches real reviews.',
    `The sample-size formula matches statsmodels (${fmt(d.experiment.n_per_arm_formula)} vs ${fmt(d.experiment.n_per_arm_statsmodels)}) and a textbook case.`,
    'The ten pain themes were checked against an unsupervised topic model run blind to them.',
  ]
  const limits = [
    'One annotator. A second labeller and an agreement score come next.',
    'Reviews are not support tickets: failures that end in a return may never be reviewed.',
    'Stars lost is an association within a model, not the effect of a fix.',
    'Effort and fix efficacy are assumptions, shown as such and stress-tested.',
  ]
  return (
    <Step id="know" n={7} title="How we know" lede="What was checked, and where the numbers are still soft.">
      <div className="know">
        <div className="sheet card lined">
          <Pin tone="blue" className="pin-tl" />
          <h3 className="card-h">Checked</h3>
          <ul className="ticks">
            {checks.map((c) => (
              <li key={c}>
                <svg viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M3.5 10.5 8 15l8.5-10" fill="none" />
                </svg>
                {c}
              </li>
            ))}
          </ul>
        </div>
        <div className="sheet card lined">
          <Pin className="pin-tr" />
          <h3 className="card-h">Still soft</h3>
          <ul className="softs">
            {limits.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      </div>
    </Step>
  )
}
