import { useState, useEffect } from 'react'

const STORAGE_KEY = 'sentinel_onboarded'

const STEPS = [
  {
    title: 'Drag your position',
    body: 'Move the blue dot to your current location. The map will score risk for that area.',
    arrow: 'center',    // points to map center (where blue dot starts)
    highlight: null,
  },
  {
    title: 'Get an evacuation route',
    body: 'Open the menu (bottom-left ☰) → Show Evac Route. Sentinel finds the safest exit to a secure city.',
    arrow: 'menu',
    highlight: 'menu',
  },
  {
    title: 'Tap any hex for intel',
    body: 'Click a colored hex cell to see the ML risk score, active threat drivers, and an AI intelligence summary.',
    arrow: 'map',
    highlight: null,
  },
]

export function Onboarding({ onDone }) {
  const [step, setStep] = useState(0)

  function finish() {
    localStorage.setItem(STORAGE_KEY, '1')
    onDone?.()
  }

  function next() {
    if (step < STEPS.length - 1) {
      setStep(s => s + 1)
    } else {
      finish()
    }
  }

  const s = STEPS[step]
  const isLast = step === STEPS.length - 1

  return (
    <div style={styles.overlay}>
      {/* Translucent backdrop */}
      <div style={styles.backdrop} onClick={finish} />

      {/* Card — always centred */}
      <div style={styles.card}>
        {/* Step dots */}
        <div style={styles.dots}>
          {STEPS.map((_, i) => (
            <div
              key={i}
              style={{ ...styles.dot, background: i === step ? '#2ecc71' : '#2a2a3d' }}
            />
          ))}
        </div>

        <div style={styles.stepLabel}>STEP {step + 1} OF {STEPS.length}</div>
        <div style={styles.title}>{s.title}</div>
        <p style={styles.body}>{s.body}</p>

        <div style={styles.actions}>
          <button style={styles.skipBtn} onClick={finish}>Skip</button>
          <button style={styles.nextBtn} onClick={next}>
            {isLast ? 'Got it' : 'Next →'}
          </button>
        </div>
      </div>

      {/* Contextual arrow indicators */}
      {s.arrow === 'menu' && <ArrowMenu />}
      {s.arrow === 'map'  && <ArrowMap />}
    </div>
  )
}

// Returns true if the user has already completed onboarding
export function hasOnboarded() {
  return !!localStorage.getItem(STORAGE_KEY)
}


// ── Arrow callouts ────────────────────────────────────────────────────────────

function ArrowMenu() {
  return (
    <div style={{ position: 'fixed', bottom: 90, left: 24, zIndex: 1001, pointerEvents: 'none' }}>
      <div style={styles.arrowLabel}>☰ menu is here</div>
      <div style={styles.arrowDown}>↓</div>
    </div>
  )
}

function ArrowMap() {
  return (
    <div style={{ position: 'fixed', top: '45%', left: '50%', transform: 'translate(-50%,-50%)', zIndex: 1001, pointerEvents: 'none', textAlign: 'center' }}>
      <div style={styles.arrowLabel}>tap any colored hex</div>
      <div style={{ ...styles.arrowDown, fontSize: 28 }}>↓</div>
    </div>
  )
}


// ── Styles ────────────────────────────────────────────────────────────────────

const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    zIndex: 1000,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    pointerEvents: 'none',
  },
  backdrop: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.55)',
    pointerEvents: 'all',
  },
  card: {
    position: 'relative',
    zIndex: 1001,
    background: 'rgba(14,14,26,0.97)',
    border: '1px solid #2ecc71',
    borderRadius: 12,
    padding: '22px 24px 18px',
    width: 320,
    boxShadow: '0 8px 40px rgba(0,0,0,0.7), 0 0 30px rgba(46,204,113,0.1)',
    fontFamily: 'system-ui, sans-serif',
    pointerEvents: 'all',
  },
  dots: {
    display: 'flex',
    gap: 6,
    marginBottom: 14,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    transition: 'background 0.2s',
  },
  stepLabel: {
    color: '#555',
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    marginBottom: 6,
  },
  title: {
    color: '#2ecc71',
    fontWeight: 700,
    fontSize: 16,
    marginBottom: 8,
  },
  body: {
    color: '#bbb',
    fontSize: 13,
    lineHeight: 1.65,
    margin: '0 0 18px',
  },
  actions: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  skipBtn: {
    background: 'none',
    border: 'none',
    color: '#555',
    fontSize: 12,
    cursor: 'pointer',
    fontFamily: 'system-ui, sans-serif',
    padding: '4px 0',
  },
  nextBtn: {
    background: '#2ecc71',
    border: 'none',
    borderRadius: 6,
    color: '#000',
    fontWeight: 700,
    fontSize: 13,
    padding: '8px 18px',
    cursor: 'pointer',
    fontFamily: 'system-ui, sans-serif',
    letterSpacing: '0.03em',
  },
  arrowLabel: {
    color: '#2ecc71',
    fontWeight: 700,
    fontSize: 13,
    fontFamily: 'system-ui, sans-serif',
    background: 'rgba(0,0,0,0.7)',
    borderRadius: 6,
    padding: '4px 10px',
    marginBottom: 4,
    display: 'inline-block',
  },
  arrowDown: {
    color: '#2ecc71',
    fontSize: 22,
    textAlign: 'center',
    animation: 'bounce 0.8s ease infinite alternate',
  },
}
