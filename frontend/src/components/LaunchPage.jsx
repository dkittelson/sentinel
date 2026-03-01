import { useEffect, useState } from 'react'

export function LaunchPage({ onEnter }) {
  const [phase, setPhase] = useState('in')   // 'in' | 'idle' | 'out'

  useEffect(() => {
    // Fade in → hold → allow entry
    const t1 = setTimeout(() => setPhase('idle'), 1200)
    return () => clearTimeout(t1)
  }, [])

  function handleEnter() {
    setPhase('out')
    setTimeout(onEnter, 700)
  }

  return (
    <div style={{ ...styles.root, opacity: phase === 'out' ? 0 : 1 }}>
      {/* Background grid lines */}
      <div style={styles.grid} />

      <div style={{
        ...styles.content,
        opacity: phase === 'in' ? 0 : 1,
        transform: phase === 'in' ? 'translateY(18px)' : 'translateY(0)',
      }}>
        {/* Logo mark */}
        <div style={styles.logoMark}>
          <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
            <polygon
              points="26,2 50,14 50,38 26,50 2,38 2,14"
              stroke="url(#silver)"
              strokeWidth="1.5"
              fill="none"
            />
            <polygon
              points="26,10 42,18 42,34 26,42 10,34 10,18"
              stroke="url(#silver)"
              strokeWidth="1"
              fill="rgba(192,192,192,0.04)"
            />
            <circle cx="26" cy="26" r="4" fill="url(#silver)" />
            <defs>
              <linearGradient id="silver" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%"   stopColor="#e8e8e8" />
                <stop offset="40%"  stopColor="#ffffff" />
                <stop offset="70%"  stopColor="#a8a8a8" />
                <stop offset="100%" stopColor="#c8c8c8" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        {/* Wordmark */}
        <h1 style={styles.wordmark}>SENTINEL</h1>
        <p style={styles.tagline}>Conflict Risk Intelligence · Levant</p>

        {/* Divider */}
        <div style={styles.divider} />

        {/* Stats row */}
        <div style={styles.statsRow}>
          <Stat value="2,973" label="Monitored Hexes" />
          <Stat value="ROC 0.74" label="Model AUC" />
          <Stat value="15 min" label="Update Cycle" />
        </div>

        {/* Enter button */}
        <button style={styles.btn} onClick={handleEnter}>
          ENTER
        </button>

        <p style={styles.disclaimer}>
          For situational awareness only · Not a substitute for official advisories
        </p>
      </div>
    </div>
  )
}

function Stat({ value, label }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ color: '#d4d4d4', fontWeight: 700, fontSize: 15, letterSpacing: '0.04em' }}>
        {value}
      </div>
      <div style={{ color: '#555', fontSize: 11, marginTop: 2 }}>{label}</div>
    </div>
  )
}

const styles = {
  root: {
    position: 'fixed',
    inset: 0,
    background: '#07070f',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
    transition: 'opacity 0.7s ease',
    fontFamily: 'system-ui, sans-serif',
  },
  grid: {
    position: 'absolute',
    inset: 0,
    backgroundImage: `
      linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
    `,
    backgroundSize: '48px 48px',
    pointerEvents: 'none',
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 0,
    transition: 'opacity 0.8s ease, transform 0.8s ease',
  },
  logoMark: {
    marginBottom: 20,
    filter: 'drop-shadow(0 0 18px rgba(192,192,192,0.2))',
  },
  wordmark: {
    margin: 0,
    fontSize: 48,
    fontWeight: 900,
    letterSpacing: '0.22em',
    background: 'linear-gradient(135deg, #c0c0c0 0%, #ffffff 35%, #a0a0a0 60%, #e0e0e0 80%, #909090 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
    textShadow: 'none',
    lineHeight: 1,
  },
  tagline: {
    margin: '12px 0 0',
    color: '#444',
    fontSize: 12,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
  },
  divider: {
    width: 280,
    height: 1,
    background: 'linear-gradient(90deg, transparent, #333, transparent)',
    margin: '28px 0',
  },
  statsRow: {
    display: 'flex',
    gap: 40,
    marginBottom: 36,
  },
  btn: {
    background: 'transparent',
    border: '1px solid #444',
    color: '#bbb',
    padding: '10px 48px',
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: '0.18em',
    cursor: 'pointer',
    borderRadius: 2,
    transition: 'border-color 0.2s, color 0.2s',
    fontFamily: 'system-ui, sans-serif',
  },
  disclaimer: {
    marginTop: 20,
    color: '#333',
    fontSize: 10,
    letterSpacing: '0.06em',
  },
}
