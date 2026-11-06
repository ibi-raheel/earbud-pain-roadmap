import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'

// Placeholder page: loads the pipeline output. The full guided-story UI is built later.
type Theme = { rank: number; key: string; label: string; share: number; star_delta: number; confidence_f1: number; effort_pm: number; rice: number }
type Results = { themes: Theme[]; experiment: { label: string; baseline_p1: number; target_p2: number; n_per_arm_formula: number }; dataset: { sample_reviews: number; sample_items: number } }

function App() {
  const [r, setR] = useState<Results | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    fetch('/results.json').then((x) => x.json()).then(setR).catch((e) => setErr(String(e)))
  }, [])
  if (err) return <p>Could not load results: {err}</p>
  if (!r) return <p>Loading…</p>
  const pct = (x: number) => (100 * x).toFixed(1) + '%'
  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', maxWidth: 860, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Earbud pain-to-roadmap</h1>
      <p>{r.dataset.sample_reviews.toLocaleString()} public reviews of {r.dataset.sample_items.toLocaleString()} true-wireless earbud models, ranked by RICE.</p>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead><tr><th>#</th><th align="left">Pain theme</th><th>Reach</th><th>Stars lost</th><th>Confidence (F1)</th><th>Effort (pm, assumed)</th><th>RICE</th></tr></thead>
        <tbody>
          {r.themes.map((t) => (
            <tr key={t.key}>
              <td>{t.rank}</td><td>{t.label}</td><td align="right">{pct(t.share)}</td>
              <td align="right">{(-t.star_delta).toFixed(2)}</td><td align="right">{t.confidence_f1.toFixed(2)}</td>
              <td align="right">{t.effort_pm}</td><td align="right">{t.rice.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>
        Experiment for "{r.experiment.label}": 1-2 star share {pct(r.experiment.baseline_p1)} to {pct(r.experiment.target_p2)},{' '}
        {r.experiment.n_per_arm_formula.toLocaleString()} reviews per arm (alpha 0.05, power 0.8).
      </p>
    </main>
  )
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
