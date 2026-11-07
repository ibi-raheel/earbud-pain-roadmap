import { useEffect, useState } from 'react'

export type PRF = { precision: number; recall: number; f1: number; support?: number }

export type Theme = {
  key: string
  label: string
  rank: number
  share: number
  share_lo: number
  share_hi: number
  star_delta: number
  star_delta_lo: number
  star_delta_hi: number
  p_low_given_pain: number
  p_low_given_none: number
  share_of_low_reviews: number
  confidence_f1: number
  precision: number
  effort_pm: number
  rice: number
  lifecycle: number[]
  time_to_complaint: { n: number; median_months: number; p25: number; p75: number; hist_bins: string[]; hist: number[] }
  top_bigrams: [string, number][]
  effort_sensitivity: { p_first: number; p_top3: number }
  experiment_p2: number
  experiment_n_per_arm: number
}

export type Results = {
  generated: string
  dataset: {
    name: string
    url: string
    citation: string
    raw: number
    after_exact_dupes: number
    after_text_dupes: number
    after_date_and_length: number
    items: number
    sample_reviews: number
    sample_items: number
    sample_sentences: number
  }
  overall: { mean_stars: number; low_star_share: number; any_pain_share: number; ols_n: number; ols_items: number }
  lifecycle_bins: string[]
  lifecycle_n: number[]
  themes: Theme[]
  experiment: {
    theme: string
    label: string
    metric: string
    baseline_p1: number
    efficacy_assumption: number
    target_p2: number
    mde_abs: number
    mde_rel: number
    alpha: number
    power: number
    n_per_arm_formula: number
    n_per_arm_statsmodels: number
  }
  validation: {
    chosen: string
    t_theme: number
    t_neg: number
    n_dev: number
    n_test: number
    methods: Record<string, { per_theme: Record<string, PRF>; micro: PRF }>
    dev_micro: Record<string, PRF>
    confusion: { labels: string[]; matrix: number[][] }
  }
  topics: { topic: number; top_terms: string[]; share: number; theme: string }[]
}

export function useResults() {
  const [data, setData] = useState<Results | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'results.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [])
  return { data, error }
}

// Short labels for sticky notes. Display text only; every number comes from results.json.
export const SHORT: Record<string, string> = {
  sound_quality: 'Sound',
  connectivity: 'Connection drops',
  failure: 'Stops working',
  fit_comfort: 'Fit',
  call_mic: 'Calls & mic',
  charging_case: 'Charging case',
  battery: 'Battery',
  controls: 'Touch controls',
  anc_noise: 'Noise cancelling',
  app_software: 'App & firmware',
}

// Wall groupings: a layout choice for the affinity wall, not a finding.
export const GROUPS: { id: string; title: string; tone: 'y' | 'b' | 'g' | 'p'; keys: string[] }[] = [
  { id: 'dies', title: 'It breaks or runs out', tone: 'y', keys: ['failure', 'charging_case', 'battery'] },
  { id: 'hear', title: 'Hearing and being heard', tone: 'b', keys: ['sound_quality', 'anc_noise', 'call_mic'] },
  { id: 'link', title: 'Links and software', tone: 'p', keys: ['connectivity', 'app_software'] },
  { id: 'wear', title: 'On the ear', tone: 'g', keys: ['fit_comfort', 'controls'] },
]

export const toneOf = (key: string) => GROUPS.find((g) => g.keys.includes(key))?.tone ?? 'y'

// Effort rationale, copied from pipeline/prioritise.py (the values themselves come from results.json).
export const EFFORT_WHY: Record<string, string> = {
  fit_comfort: 'Nozzle angle, shell geometry, tip set, ear-scan fit study',
  battery: 'Cell and power budget, firmware power states',
  charging_case: 'Hinge, magnet and pogo-contact redesign, case firmware',
  connectivity: 'Firmware and antenna tuning, mostly software',
  sound_quality: 'Tuning, driver choice',
  anc_noise: 'Mic placement and DSP',
  call_mic: 'Beamforming and DSP, vent design',
  controls: 'Touch-threshold firmware, gesture mapping',
  failure: 'Reliability: drop, sweat ingress, solder joints',
  app_software: 'Companion app and OTA',
}

export const METHOD_NAMES: Record<string, string> = {
  keyword_baseline: 'Keyword search',
  seed_lexicon: 'Word list alone',
  seed_lexicon_plus_negativity: 'Word list + complaint gate',
  classifier_plus_negativity: 'Trained classifier + complaint gate',
}

// Two-sided two-proportion z-test, unpooled variance (METHOD.md section 5).
const Z = 1.959964 + 0.841621
export function nPerArm(p1: number, p2: number) {
  const d = p1 - p2
  if (d <= 0) return Infinity
  return Math.ceil((Z * Z * (p1 * (1 - p1) + p2 * (1 - p2))) / (d * d))
}
export function targetP2(p1: number, t: Theme, efficacy: number) {
  return p1 - efficacy * t.share * (t.p_low_given_pain - t.p_low_given_none)
}

export function riceScore(t: Theme, w: { r: number; i: number; c: number; e: number }) {
  const R = t.share * 100
  const I = Math.max(0, -t.star_delta)
  const C = t.confidence_f1
  const E = t.effort_pm
  if (I === 0 && w.i > 0) return 0
  return (R ** w.r * I ** w.i * C ** w.c) / E ** w.e
}

export const pct = (x: number, d = 1) => (100 * x).toFixed(d) + '%'
export const fmt = (x: number) => Math.round(x).toLocaleString('en-US')
export const stars = (x: number) => (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x).toFixed(2)
