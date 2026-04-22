import { useEffect, useRef, useState } from 'react'

// ── Data network background ───────────────────────────────────────────────────
// Nodes + edges that slowly drift — Palantir Gotham intel-graph aesthetic
function DataNetworkBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    // Skip particle animation for users who prefer reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const ctx = canvas.getContext('2d')
    let rafId

    const NODE_COUNT = 55
    const CONNECT_DIST = 180
    let nodes = []

    function buildNodes(W, H) {
      return Array.from({ length: NODE_COUNT }, () => ({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.22,
        vy: (Math.random() - 0.5) * 0.22,
        r: 1.2 + Math.random() * 2.2,
        pulse: Math.random() * Math.PI * 2,
        kind: Math.random() > 0.82 ? 'hot' : 'cold',
      }))
    }

    function resize() {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
      nodes = buildNodes(canvas.width, canvas.height)
    }
    resize()
    window.addEventListener('resize', resize)

    function draw() {
      const W = canvas.width, H = canvas.height
      ctx.clearRect(0, 0, W, H)

      // Update positions + bounce
      for (const n of nodes) {
        n.x += n.vx
        n.y += n.vy
        n.pulse += 0.018
        if (n.x < 0 || n.x > W) n.vx *= -1
        if (n.y < 0 || n.y > H) n.vy *= -1
      }

      // Edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j]
          const dx = a.x - b.x, dy = a.y - b.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < CONNECT_DIST) {
            const alpha = (1 - dist / CONNECT_DIST) * 0.18
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.strokeStyle = `rgba(59,130,246,${alpha})`
            ctx.lineWidth = 0.6
            ctx.stroke()
          }
        }
      }

      // Nodes
      for (const n of nodes) {
        const glow = 0.55 + 0.45 * Math.sin(n.pulse)
        const color = n.kind === 'hot' ? `rgba(251,191,36,${glow * 0.9})` : `rgba(96,165,250,${glow * 0.75})`
        ctx.beginPath()
        ctx.arc(n.x, n.y, n.r + (n.kind === 'hot' ? 0.6 : 0), 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.fill()
      }

      rafId = requestAnimationFrame(draw)
    }

    draw()
    return () => {
      cancelAnimationFrame(rafId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }}
    />
  )
}

// ── Scan-line reveal on hero text ─────────────────────────────────────────────
function useScanReveal(active) {
  const [progress, setProgress] = useState(0)
  useEffect(() => {
    if (!active) return
    // Instant reveal for users who prefer reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setProgress(1)
      return
    }
    const start = performance.now()
    const dur = 900
    let id
    function tick(now) {
      setProgress(Math.min((now - start) / dur, 1))
      if (now - start < dur) id = requestAnimationFrame(tick)
    }
    id = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(id)
  }, [active])
  return progress
}

// ── LivePing indicator ─────────────────────────────────────────────────────────
function LivePing() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span style={{
        width: 7, height: 7, borderRadius: '50%',
        background: '#22c55e',
        boxShadow: '0 0 6px 2px rgba(34,197,94,0.5)',
        animation: 'ping 1.8s ease-in-out infinite',
      }} />
      <span style={{ color: '#22c55e', fontSize: 10, letterSpacing: '0.2em', fontWeight: 700 }}>LIVE</span>
    </span>
  )
}

// ── Feature pillar card ────────────────────────────────────────────────────────
function FeatureCard({ icon, title, body, accent }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flex: 1,
        minWidth: 220,
        maxWidth: 300,
        background: hovered
          ? 'rgba(59,130,246,0.07)'
          : 'rgba(255,255,255,0.025)',
        border: `1px solid ${hovered ? 'rgba(59,130,246,0.35)' : 'rgba(255,255,255,0.07)'}`,
        borderTop: `2px solid ${accent}`,
        padding: '28px 24px',
        transition: 'all 0.25s ease',
        cursor: 'default',
      }}
    >
      <div style={{ fontSize: 22, marginBottom: 14 }}>{icon}</div>
      <div style={{
        fontSize: 11, fontWeight: 700, letterSpacing: '0.2em',
        color: '#94a3b8', textTransform: 'uppercase', marginBottom: 10,
      }}>
        {title}
      </div>
      <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.7 }}>
        {body}
      </div>
    </div>
  )
}

// ── Situation Report panel (right-column hero card) ───────────────────────────
function SitrepPanel() {
  const stats = [
    { label: 'Monitored Hexes',   sub: 'H3 resolution 6 · Levant',  value: '2,973' },
    { label: 'Onset AUC-PR',      sub: 'XGBoost · anomaly framing', value: '0.246' },
    { label: 'Continuation AUC',  sub: 'PerHexGRU · 14-day seq',    value: '0.739' },
    { label: 'Active Sources',    sub: 'ACLED · GDELT · FIRMS · +9', value: '12+' },
    { label: 'Update Cycle',      sub: 'APScheduler · live push',    value: '15 min' },
  ]

  return (
    <div style={s.statsPanel}>
      <div style={s.statsPanelHeader}>
        <span style={s.statsPanelTitle}>SYSTEM STATUS</span>
        <LivePing />
      </div>

      {stats.map((st, i) => (
        <div key={i} style={s.statRow}>
          <div>
            <div style={s.statLabel}>{st.label}</div>
            <div style={s.statSub}>{st.sub}</div>
          </div>
          <div style={s.statValue}>{st.value}</div>
        </div>
      ))}

      <div style={s.statsPanelFooter}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
          <span style={{ color: '#1e3a5f', fontSize: 9, letterSpacing: '0.15em', fontWeight: 700 }}>
            OPERATIONAL · LEVANT CORRIDOR
          </span>
        </div>
      </div>
    </div>
  )
}


// ── Main launch page ──────────────────────────────────────────────────────────
export function LaunchPage({ onEnter }) {
  const [ready, setReady]     = useState(false)
  const [exiting, setExiting] = useState(false)
  const heroProgress = useScanReveal(ready)

  useEffect(() => {
    const id = setTimeout(() => setReady(true), 300)
    return () => clearTimeout(id)
  }, [])

  function handleEnter() {
    if (!ready) return
    setExiting(true)
    setTimeout(onEnter, 700)
  }

  const exitStyle = exiting ? {
    opacity: 0,
    transform: 'scale(1.06)',
    filter: 'blur(8px)',
    transition: 'opacity 0.7s ease-in, transform 0.7s ease-in, filter 0.7s ease-in',
  } : {}

  return (
    <div style={{ ...s.root, ...exitStyle }}>
      <style>{`
        @keyframes ping {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.55; transform: scale(1.5); }
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(14px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .enter-btn:hover {
          background: rgba(59,130,246,0.12) !important;
          border-color: rgba(59,130,246,0.8) !important;
          color: #60a5fa !important;
        }
        .nav-link { color: #475569; font-size: 12px; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; cursor: pointer; transition: color .2s; }
        .nav-link:hover { color: #94a3b8; }
      `}</style>

      <DataNetworkBackground />

      {/* Deep gradient overlay */}
      <div style={s.overlay} />

      {/* ── Nav bar ── */}
      <nav style={s.nav}>
        <div style={s.navLogo}>
          <svg width="22" height="22" viewBox="0 0 52 52" fill="none">
            <polygon points="26,2 50,14 50,38 26,50 2,38 2,14" stroke="#3b82f6" strokeWidth="1.5" fill="none"/>
            <circle cx="26" cy="26" r="4" fill="#3b82f6"/>
          </svg>
          <span style={{ color: '#e2e8f0', fontWeight: 800, fontSize: 13, letterSpacing: '0.3em' }}>SENTINEL</span>
        </div>
        <div style={s.navLinks}>
          {['Platform', 'Intelligence', 'Solutions', 'Docs'].map(l => (
            <span key={l} className="nav-link">{l}</span>
          ))}
        </div>
        <button
          onClick={handleEnter}
          style={s.navCta}
          className="enter-btn"
        >
          Access Platform
        </button>
      </nav>

      {/* ── Hero ── */}
      <main style={s.hero}>
        {/* Left column */}
        <div style={{ ...s.heroLeft, opacity: ready ? 1 : 0, transition: 'opacity 0.5s ease 0.1s' }}>

          {/* Status badge */}
          <div style={s.statusBadge}>
            <LivePing />
            <span style={s.statusDivider}>|</span>
            <span style={{ color: '#475569', fontSize: 10, letterSpacing: '0.15em' }}>
              LEVANT CORRIDOR · OPERATIONAL
            </span>
          </div>

          {/* Headline */}
          <h1 style={s.headline}>
            <span style={{ display: 'block', overflow: 'hidden' }}>
              <span style={{
                display: 'block',
                transform: `translateY(${(1 - heroProgress) * 40}px)`,
                opacity: heroProgress,
                transition: 'none',
              }}>
                CONFLICT
              </span>
            </span>
            <span style={{ display: 'block', overflow: 'hidden' }}>
              <span style={{
                display: 'block',
                transform: `translateY(${(1 - Math.min(heroProgress * 1.4, 1)) * 40}px)`,
                opacity: Math.min(heroProgress * 1.4, 1),
                transition: 'none',
              }}>
                INTELLIGENCE
              </span>
            </span>
            <span style={{ ...s.headlineAccent, display: 'block', overflow: 'hidden' }}>
              <span style={{
                display: 'block',
                transform: `translateY(${(1 - Math.min(heroProgress * 1.8, 1)) * 40}px)`,
                opacity: Math.min(heroProgress * 1.8, 1),
                transition: 'none',
              }}>
                PLATFORM
              </span>
            </span>
          </h1>

          <p style={{ ...s.subtext, opacity: heroProgress * 0.9 }}>
            Real-time spatial threat assessment and AI-powered decision support for civilians and organizations operating in active conflict environments.
          </p>

          {/* CTAs */}
          <div style={{ display: 'flex', gap: 14, marginTop: 36, opacity: heroProgress }}>
            <button onClick={handleEnter} style={s.primaryBtn} className="enter-btn">
              ACCESS PLATFORM →
            </button>
            <button style={s.secondaryBtn}>
              VIEW BRIEFING
            </button>
          </div>

          {/* Disclaimer */}
          <p style={{ ...s.disclaimer, opacity: heroProgress * 0.6 }}>
            Decision support only · Not a substitute for official advisories
          </p>
        </div>

        {/* Right column — citizen SITREP panel */}
        <div style={{
          ...s.heroRight,
          opacity: ready ? 1 : 0,
          transform: ready ? 'translateX(0)' : 'translateX(30px)',
          transition: 'opacity 0.6s ease 0.4s, transform 0.6s ease 0.4s',
        }}>
          <SitrepPanel />
        </div>
      </main>

      {/* ── Feature pillars ── */}
      <section style={{
        ...s.pillars,
        opacity: ready ? 1 : 0,
        transform: ready ? 'translateY(0)' : 'translateY(20px)',
        transition: 'opacity 0.7s ease 0.6s, transform 0.7s ease 0.6s',
      }}>
        <FeatureCard
          icon="⬡"
          accent="#3b82f6"
          title="Spatial Threat Detection"
          body="H3 hexagonal grid at 36 km² resolution. XGBoost classifier scores every hex every 15 minutes with 72-hour lookahead."
        />
        <FeatureCard
          icon="◈"
          accent="#f59e0b"
          title="AI Situation Analysis"
          body="Gemini 2.5 Flash synthesizes ACLED, GDELT news sentiment, and NASA FIRMS thermal anomalies into plain-language briefings."
        />
        <FeatureCard
          icon="→"
          accent="#10b981"
          title="Routing Intelligence"
          body="Real-road evacuation routing via Mapbox Directions. Routes are scored for danger crossings and rerouted around Red hexes automatically."
        />
      </section>

      {/* ── Bottom bar ── */}
      <footer style={s.footer}>
        <span style={{ color: '#1e293b', fontSize: 10, letterSpacing: '0.12em' }}>
          © 2026 SENTINEL · CONFLICT EARLY WARNING SYSTEM
        </span>
        <span style={{ color: '#1e293b', fontSize: 10 }}>
          For situational awareness only · Not a substitute for official advisories
        </span>
      </footer>
    </div>
  )
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = {
  root: {
    position: 'fixed',
    inset: 0,
    background: '#080c14',
    fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
    color: '#e2e8f0',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    zIndex: 100,
  },
  overlay: {
    position: 'absolute',
    inset: 0,
    background: 'radial-gradient(ellipse 70% 60% at 30% 50%, rgba(8,12,20,0) 0%, rgba(8,12,20,0.75) 100%)',
    pointerEvents: 'none',
    zIndex: 1,
  },
  nav: {
    position: 'relative',
    zIndex: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 48px',
    height: 60,
    borderBottom: '1px solid rgba(255,255,255,0.05)',
    background: 'rgba(8,12,20,0.7)',
    backdropFilter: 'blur(8px)',
  },
  navLogo: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  navLinks: {
    display: 'flex',
    gap: 32,
    position: 'absolute',
    left: '50%',
    transform: 'translateX(-50%)',
  },
  navCta: {
    background: 'transparent',
    border: '1px solid rgba(59,130,246,0.4)',
    color: '#60a5fa',
    padding: '7px 20px',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.15em',
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontFamily: 'inherit',
  },
  hero: {
    position: 'relative',
    zIndex: 5,
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    gap: 60,
    padding: '0 48px',
    maxWidth: 1200,
    width: '100%',
    margin: '0 auto',
  },
  heroLeft: {
    flex: 1,
    maxWidth: 560,
  },
  heroRight: {
    width: 320,
    flexShrink: 0,
  },
  statusBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 10,
    padding: '5px 14px',
    border: '1px solid rgba(34,197,94,0.2)',
    background: 'rgba(34,197,94,0.05)',
    marginBottom: 28,
  },
  statusDivider: {
    color: '#1e3a5f',
    fontSize: 12,
  },
  headline: {
    margin: 0,
    fontSize: 'clamp(40px, 6vw, 68px)',
    fontWeight: 900,
    lineHeight: 1.0,
    letterSpacing: '-0.01em',
    color: '#f1f5f9',
  },
  headlineAccent: {
    background: 'linear-gradient(135deg, #3b82f6 0%, #60a5fa 50%, #93c5fd 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
  },
  subtext: {
    marginTop: 24,
    fontSize: 14,
    color: '#475569',
    lineHeight: 1.75,
    maxWidth: 480,
  },
  primaryBtn: {
    background: 'rgba(59,130,246,0.08)',
    border: '1px solid rgba(59,130,246,0.5)',
    color: '#60a5fa',
    padding: '12px 32px',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.2em',
    cursor: 'pointer',
    fontFamily: 'inherit',
    transition: 'all 0.2s',
  },
  secondaryBtn: {
    background: 'transparent',
    border: '1px solid rgba(255,255,255,0.1)',
    color: '#475569',
    padding: '12px 24px',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.15em',
    cursor: 'pointer',
    fontFamily: 'inherit',
    transition: 'all 0.2s',
  },
  disclaimer: {
    marginTop: 24,
    fontSize: 10,
    color: '#1e293b',
    letterSpacing: '0.08em',
  },
  statsPanel: {
    border: '1px solid rgba(59,130,246,0.15)',
    background: 'rgba(8,12,20,0.8)',
    backdropFilter: 'blur(12px)',
  },
  statsPanelHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 18px',
    borderBottom: '1px solid rgba(59,130,246,0.1)',
    background: 'rgba(59,130,246,0.04)',
  },
  statsPanelTitle: {
    fontSize: 9,
    fontWeight: 700,
    letterSpacing: '0.25em',
    color: '#334155',
    textTransform: 'uppercase',
  },
  statRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 18px',
    borderBottom: '1px solid rgba(255,255,255,0.03)',
  },
  statLabel: {
    fontSize: 11,
    color: '#64748b',
    fontWeight: 600,
    letterSpacing: '0.05em',
    marginBottom: 2,
  },
  statSub: {
    fontSize: 9,
    color: '#1e3a5f',
    letterSpacing: '0.1em',
  },
  statValue: {
    fontSize: 15,
    fontWeight: 800,
    color: '#93c5fd',
    letterSpacing: '0.02em',
  },
  statsPanelFooter: {
    padding: '10px 18px',
    background: 'rgba(59,130,246,0.03)',
  },
  pillars: {
    position: 'relative',
    zIndex: 5,
    display: 'flex',
    gap: 1,
    padding: '0 48px',
    maxWidth: 1200,
    width: '100%',
    margin: '0 auto 0',
    borderTop: '1px solid rgba(255,255,255,0.05)',
  },
  footer: {
    position: 'relative',
    zIndex: 5,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 48px',
    borderTop: '1px solid rgba(255,255,255,0.04)',
  },
}
