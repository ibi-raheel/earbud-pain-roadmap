import { ReactNode, useEffect, useRef, useState } from 'react'

export function Pin({ tone = 'red', className = '' }: { tone?: 'red' | 'blue' | 'green'; className?: string }) {
  return (
    <svg className={`pin pin-${tone} ${className}`} viewBox="0 0 24 24" aria-hidden="true">
      <ellipse cx="13.5" cy="15" rx="6" ry="3" className="pin-shadow" />
      <circle cx="12" cy="10" r="7" className="pin-head" />
      <circle cx="9.6" cy="7.6" r="2.1" className="pin-shine" />
    </svg>
  )
}

export function Tape({ className = '' }: { className?: string }) {
  return <span className={`tape ${className}`} aria-hidden="true" />
}

export function Details({ label = 'Show details', children }: { label?: string; children: ReactNode }) {
  return (
    <details className="details">
      <summary>
        <svg viewBox="0 0 16 16" aria-hidden="true" className="chev">
          <path d="M6 3.5 10.5 8 6 12.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="summary-open">{label}</span>
        <span className="summary-close">Hide details</span>
      </summary>
      <div className="details-body">{children}</div>
    </details>
  )
}

/** Adds data-seen once the element scrolls into view; the CSS decides what that means. */
export function useSeen<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [seen, setSeen] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (!('IntersectionObserver' in window)) {
      setSeen(true)
      return
    }
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setSeen(true)
          io.disconnect()
        }
      },
      { rootMargin: '0px 0px -15% 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return { ref, seen }
}

export function Step({
  id,
  n,
  title,
  lede,
  children,
}: {
  id: string
  n: number
  title: string
  lede: ReactNode
  children: ReactNode
}) {
  const { ref, seen } = useSeen<HTMLElement>()
  return (
    <section id={id} ref={ref} className="step" data-seen={seen || undefined} aria-labelledby={`${id}-h`}>
      <header className="step-head">
        <span className="step-num" aria-hidden="true">
          {n}
        </span>
        <div>
          <h2 id={`${id}-h`}>{title}</h2>
          <p className="lede">{lede}</p>
        </div>
      </header>
      {children}
    </section>
  )
}

/** Deterministic small tilt so the wall looks hand-pinned but renders the same every time. */
export function tilt(seed: string, max = 2.2) {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0
  return (((h % 1000) / 1000) * 2 - 1) * max
}
