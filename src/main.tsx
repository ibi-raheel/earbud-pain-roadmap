import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { Results, fmt, useResults } from './data'
import { StepExperiment, StepKnow, StepModel, StepPile, StepRoadmap, StepStars, StepWall } from './steps'
import { Pin } from './ui'

const STEPS = [
  { id: 'pile', label: 'Reviews' },
  { id: 'wall', label: 'Complaints' },
  { id: 'model', label: 'Model check' },
  { id: 'stars', label: 'Star cost' },
  { id: 'roadmap', label: 'Roadmap' },
  { id: 'experiment', label: 'Experiment' },
  { id: 'know', label: 'How we know' },
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

function Hero({ d }: { d: Results }) {
  return (
    <header className="hero">
      <div className="hero-note">
        <Pin className="pin-top" />
        <h1>Which pains cost wireless earbuds the most stars?</h1>
        <p>
          A product-research wall built from {fmt(d.dataset.sample_reviews)} public reviews: what owners complain about, what
          each pain costs in stars, what to fix first, and how big a test has to be to prove it.
        </p>
        <a className="start" href="#pile">
          Walk the wall
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M8 3v10M3.5 8.5 8 13l4.5-4.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>
      </div>
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
