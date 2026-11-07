import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { Results, SHORT, fmt, stars, useResults } from './data'
import { StepExperiment, StepKnow, StepModel, StepPile, StepRoadmap, StepSolution, StepStars, StepWall } from './steps'
import { Pin } from './ui'

const STEPS = [
  { id: 'pile', label: 'Reviews' },
  { id: 'wall', label: 'Complaints' },
  { id: 'model', label: 'Model check' },
  { id: 'stars', label: 'Star cost' },
  { id: 'roadmap', label: 'Roadmap' },
  { id: 'experiment', label: 'Experiment' },
  { id: 'know', label: 'How we know' },
  { id: 'solution', label: 'Solution' },
]

function useActiveStep() {
  const [active, setActive] = useState(-1)
  const [progress, setProgress] = useState(0)
  useEffect(() => {
    const onScroll = () => {
      const mid = window.innerHeight * 0.4
      let a = -1
      STEPS.forEach((s, i) => {
        const el = document.getElementById(s.id)
        if (el && el.getBoundingClientRect().top < mid) a = i
      })
      setActive(a)
      const max = document.documentElement.scrollHeight - window.innerHeight
      setProgress(max > 0 ? Math.min(1, window.scrollY / max) : 0)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])
  return { active, progress }
}

function Rail({ active, progress }: { active: number; progress: number }) {
  return (
    <>
      <nav className="rail" aria-label="Steps">
        <ol>
          {STEPS.map((s, i) => (
            <li key={s.id} className={i === active ? 'on' : i < active ? 'done' : ''}>
              <a href={`#${s.id}`} aria-current={i === active ? 'step' : undefined}>
                <span className="rail-n num">{i + 1}</span>
                <span className="rail-l">{s.label}</span>
              </a>
            </li>
          ))}
        </ol>
      </nav>
      <div className="progress" aria-hidden="true">
        <span style={{ transform: `scaleX(${progress})` }} />
        <em>{active >= 0 ? `${active + 1}/${STEPS.length} · ${STEPS[active].label}` : `${STEPS.length} steps`}</em>
      </div>
    </>
  )
}

const NAME: Record<string, string> = { controls: 'Touch controls', anc_noise: 'ANC', app_software: 'app' }
const list = (xs: string[]) => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`)

function Hero({ d }: { d: Results }) {
  const byStars = [...d.themes].sort((a, b) => a.star_delta - b.star_delta)
  const [worst, next] = byStars
  const top3 = [...d.themes].sort((a, b) => a.rank - b.rank).slice(0, 3)
  const battery = d.themes.find((t) => t.key === 'battery')!
  const life = worst.lifecycle
  const ratio = life[life.length - 1] / life[0]
  const growth = ratio >= 2 ? 'more than double' : `grow ${ratio.toFixed(1)}×`
  // pains whose 95% CI on stars lost includes 0 or is positive
  const free = [...d.themes].filter((t) => t.star_delta_hi >= 0).sort((a, b) => a.rank - b.rank)
  return (
    <header className="hero">
      <div className="hero-note">
        <Pin className="pin-top" />
        <p className="eyebrow">
          {fmt(d.dataset.sample_reviews)} public reviews · {fmt(d.dataset.sample_items)} earbud models
        </p>
        <h1>Which earbud pains cost the most stars, and what should the next model fix first?</h1>
        <p>
          A dead earbud costs <b className="num">{Math.abs(worst.star_delta).toFixed(2)}</b> stars,{' '}
          {(worst.star_delta / next.star_delta).toFixed(1)}× any other pain, and those complaints {growth} as a model ages.
          Battery costs <b className="num">{Math.abs(battery.star_delta).toFixed(2)}</b>. {list(free.map((t) => NAME[t.key] ?? SHORT[t.key]))}{' '}
          cost nothing measurable.
        </p>
        <div className="hero-cta">
          <a className="start" href="#solution">
            Here’s the playbook
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M3 8h10M8.5 3.5 13 8l-4.5 4.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
          <a className="start quiet" href="#pile">
            Walk the evidence
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M8 3v10M3.5 8.5 8 13l4.5-4.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
        </div>
      </div>
      <aside className="answer" aria-label="The short answer">
        <Pin tone="blue" className="pin-top" />
        <p className="answer-h">The short answer</p>
        <ol>
          <li>
            A dead earbud costs <b className="num">{stars(worst.star_delta)}</b> stars, {(worst.star_delta / next.star_delta).toFixed(1)}× the
            next-worst pain.
          </li>
          <li>
            Fix first, by RICE score: <b>{top3.map((t) => SHORT[t.key]).join(', ')}</b>.
          </li>
          <li>
            A test of a {d.experiment.label.toLowerCase()} fix needs <b className="num">{fmt(d.experiment.n_per_arm_formula)}</b> owners
            per arm.
          </li>
        </ol>
      </aside>
    </header>
  )
}

function Footer({ d }: { d: Results }) {
  return (
    <footer className="foot">
      <div className="foot-card">
        <p>
          Data: <a href={d.dataset.url}>Amazon Reviews 2023</a>, Electronics category, McAuley Lab, UC San Diego.{' '}
          {d.dataset.citation} Released for research; no licence is stated, so this page shows only aggregate statistics and no
          review text. Effort and fix efficacy are labelled assumptions. Nothing is simulated.
        </p>
        <p className="more">
          More work at <a href="https://ibiraheel.com">ibiraheel.com</a>
        </p>
      </div>
    </footer>
  )
}

function App() {
  const { data, error } = useResults()
  const { active, progress } = useActiveStep()
  if (error)
    return (
      <main className="state">
        <p>Could not load the results file ({error}). Reload the page to try again.</p>
      </main>
    )
  if (!data)
    return (
      <main className="state" aria-busy="true">
        <p>Pinning up the wall…</p>
      </main>
    )
  return (
    <>
      <Rail active={active} progress={progress} />
      <main className="page">
        <Hero d={data} />
        <StepPile d={data} />
        <StepWall d={data} />
        <StepModel d={data} />
        <StepStars d={data} />
        <StepRoadmap d={data} />
        <StepExperiment d={data} />
        <StepKnow d={data} />
        <StepSolution d={data} />
        <Footer d={data} />
      </main>
    </>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
