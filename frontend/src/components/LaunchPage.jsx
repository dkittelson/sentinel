import { useEffect, useRef, useState } from 'react'

// ── Hex grid background ───────────────────────────────────────────────────────
// Mirrors the product's own visual language: tier colors pulsing across hexes
const HEX_SIZE  = 28
const COL_STEP  = HEX_SIZE * Math.sqrt(3)
const ROW_STEP  = HEX_SIZE * 1.5

const TIER_COLORS = [
  { rgb: [235, 30,  40 ], weight: 10 },  // vivid red
  { rgb: [225, 90,  30 ], weight: 3  },  // orange-red
]

const MAX_ACTIVE = 3   // at most 3 hexes lit at once

function pickTierColor() {
  const total = TIER_COLORS.reduce((s, c) => s + c.weight, 0)
  let r = Math.random() * total
  for (const c of TIER_COLORS) { r -= c.weight; if (r <= 0) return c.rgb }
  return TIER_COLORS[0].rgb
}

function HexGridBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let rafId
    let hexes = []
    let activeCount = 0

    function buildGrid(W, H) {
      const cols = Math.ceil(W / COL_STEP) + 2
      const rows = Math.ceil(H / ROW_STEP) + 2
      const result = []
      for (let row = -1; row < rows; row++) {
        for (let col = -1; col < cols; col++) {
          const x = col * COL_STEP + (row % 2 === 0 ? 0 : COL_STEP / 2)
          const y = row * ROW_STEP
          result.push({
            x, y,
            alpha: 0, targetAlpha: 0,
            color: [255, 255, 255],
            phase: 'idle',
            timer: (60 + Math.random() * 300) | 0,
            holdTimer: 0,
          })
        }
      }
      return result
    }

    function drawHex(x, y) {
      ctx.beginPath()
      for (let i = 0; i < 6; i++) {
        const a = (Math.PI / 3) * i - Math.PI / 6
        const px = x + HEX_SIZE * Math.cos(a)
        const py = y + HEX_SIZE * Math.sin(a)
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)
      }
      ctx.closePath()
    }

    function resize() {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
      activeCount = 0
      hexes = buildGrid(canvas.width, canvas.height)
    }
    resize()
    window.addEventListener('resize', resize)

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      hexes.forEach(h => {
        // Phase state machine — capped at MAX_ACTIVE simultaneously
        if (h.phase === 'idle') {
          if (--h.timer <= 0) {
            if (activeCount < MAX_ACTIVE) {
              activeCount++
              h.color = pickTierColor()
              h.targetAlpha = 0.38 + Math.random() * 0.18   // bright
              h.phase = 'rising'
            } else {
              h.timer = (40 + Math.random() * 80) | 0        // retry soon
            }
          }
        } else if (h.phase === 'rising') {
          h.alpha += 0.012                                    // ~0.75s to peak
          if (h.alpha >= h.targetAlpha) {
            h.alpha = h.targetAlpha
            h.phase = 'hold'
            h.holdTimer = (30 + Math.random() * 30) | 0      // ~0.5 – 1s hold
          }
        } else if (h.phase === 'hold') {
          if (--h.holdTimer <= 0) h.phase = 'falling'
        } else if (h.phase === 'falling') {
          h.alpha -= 0.006                                    // ~1s to fade out
          if (h.alpha <= 0) {
            h.alpha = 0
            h.phase = 'idle'
            activeCount--
            h.timer = (80 + Math.random() * 160) | 0
          }
        }

        drawHex(h.x, h.y)

        // Colored fill when active
        if (h.alpha > 0.004) {
          const [r, g, b] = h.color
          ctx.fillStyle = `rgba(${r},${g},${b},${h.alpha})`
          ctx.fill()
        }

        // Always-visible subtle border
        ctx.strokeStyle = 'rgba(255,255,255,0.04)'
        ctx.lineWidth = 0.5
        ctx.stroke()
      })

      rafId = requestAnimationFrame(draw)
    }

    draw()
    return () => {
      cancelAnimationFrame(rafId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }} />
}

// ── Scattered flicker pixel dissolve on wordmark ─────────────────────────────
const BLOCK_COLORS = ['#07070f', '#08081a', '#060614', '#050510', '#09090e']
const BLOCK_SIZE   = 8
const DURATION_IN  = 1600
const DURATION_OUT = 700

function usePixelCanvas(wrapperRef, phase, onDone) {
  const canvasRef = useRef(null)
  const onDoneRef = useRef(onDone)
  onDoneRef.current = onDone

  useEffect(() => {
    if (!phase || !canvasRef.current || !wrapperRef.current) return
    const canvas  = canvasRef.current
    const wrapper = wrapperRef.current
    const W = canvas.width  = wrapper.offsetWidth
    const H = canvas.height = wrapper.offsetHeight
    if (!W || !H) return
    const ctx = canvas.getContext('2d')

    const duration = phase === 'in' ? DURATION_IN : DURATION_OUT

    // Each block gets a flicker window biased by x-column (left resolves first).
    // 'out' uses tighter windows so all blocks fully settle before duration ends.
    const cols = Math.ceil(W / BLOCK_SIZE)
    const blocks = []
    for (let r = 0; r < Math.ceil(H / BLOCK_SIZE); r++) {
      for (let c = 0; c < cols; c++) {
        const xFrac     = c / Math.max(cols - 1, 1)
        const flickerMs = phase === 'out'
          ? 55 + Math.random() * 80                          // short flicker: 55–135 ms
          : 80 + Math.random() * 150                         // longer flicker: 80–230 ms
        const spread    = phase === 'out' ? 0.55 : 0.62      // tighter spread on exit
        const jitter    = phase === 'out' ? 0.06 : 0.10
        const startMs   = xFrac * (duration * spread) + Math.random() * (duration * jitter)
        blocks.push({
          x: c * BLOCK_SIZE, y: r * BLOCK_SIZE,
          color: BLOCK_COLORS[Math.floor(Math.random() * BLOCK_COLORS.length)],
          startMs,
          endMs: startMs + flickerMs,
        })
      }
    }

    // Pre-fill for 'in' (start fully covered)
    if (phase === 'in') {
      ctx.fillStyle = BLOCK_COLORS[0]
      ctx.fillRect(0, 0, W, H)
    }

    const start = performance.now()
    let rafId

    function draw(now) {
      const elapsed  = now - start
      const progress = Math.min(elapsed / duration, 1)
      ctx.clearRect(0, 0, W, H)

      for (const b of blocks) {
        const state = elapsed < b.startMs ? 'before'
                    : elapsed < b.endMs   ? 'flicker'
                    :                       'after'

        if (phase === 'in') {
          if (state === 'before') {
            // Still covered — draw dark block
            ctx.fillStyle = b.color
            ctx.fillRect(b.x, b.y, BLOCK_SIZE, BLOCK_SIZE)
          } else if (state === 'flicker') {
            // Rapid random bright/dark flashes
            const rnd = Math.random()
            if (rnd > 0.42) {
              const v = 35 + Math.floor(Math.random() * 210)
              ctx.fillStyle = `rgba(${v},${Math.floor(v * 1.01)},${Math.floor(v * 1.1)},${0.4 + Math.random() * 0.6})`
              ctx.fillRect(b.x, b.y, BLOCK_SIZE, BLOCK_SIZE)
            }
            // else: transparent this frame — text shows through mid-flicker
          }
          // after: transparent — text permanently visible
        } else {
          // phase === 'out'
          if (state === 'after') {
            // Fully covered
            ctx.fillStyle = b.color
            ctx.fillRect(b.x, b.y, BLOCK_SIZE, BLOCK_SIZE)
          } else if (state === 'flicker') {
            const rnd = Math.random()
            if (rnd > 0.42) {
              const v = 35 + Math.floor(Math.random() * 210)
              ctx.fillStyle = `rgba(${v},${Math.floor(v * 1.01)},${Math.floor(v * 1.1)},${0.4 + Math.random() * 0.6})`
              ctx.fillRect(b.x, b.y, BLOCK_SIZE, BLOCK_SIZE)
            }
          }
          // before: transparent — text still visible
        }
      }

      // Ambient glitch: settled blocks briefly re-flash (CRT artifact)
      if (progress > 0.12 && progress < 0.88 && Math.random() > 0.72) {
        const n = 1 + Math.floor(Math.random() * 3)
        for (let i = 0; i < n; i++) {
          const b = blocks[Math.floor(Math.random() * blocks.length)]
          if (elapsed < b.endMs) continue  // only glitch settled blocks
          const v = 25 + Math.floor(Math.random() * 120)
          ctx.fillStyle = `rgba(${v},${v},${Math.floor(v * 1.18)},${0.12 + Math.random() * 0.28})`
          ctx.fillRect(b.x, b.y, BLOCK_SIZE, BLOCK_SIZE)
        }
      }

      if (progress < 1) {
        rafId = requestAnimationFrame(draw)
      } else {
        if (phase === 'in') {
          ctx.clearRect(0, 0, W, H)   // reveal complete — canvas transparent
        } else {
          // 'out': fill solid so words stay hidden during the zoom
          ctx.fillStyle = '#05050d'
          ctx.fillRect(0, 0, W, H)
        }
        onDoneRef.current?.()
      }
    }

    rafId = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(rafId)
  }, [phase])

  return canvasRef
}

// ── Launch page ───────────────────────────────────────────────────────────────
export function LaunchPage({ onEnter }) {
  const [canEnter, setCanEnter]     = useState(false)
  const [exiting, setExiting]       = useState(false)
  const [pixelPhase, setPixelPhase] = useState('in')
  const wrapperRef = useRef(null)

  const canvasRef = usePixelCanvas(wrapperRef, pixelPhase, () => {
    if (pixelPhase === 'in') setCanEnter(true)
    // 'out' completion: no-op — handleEnter's setTimeout drives the actual transition
  })

  // Fallback: guarantee content appears even if canvas animation misfires
  useEffect(() => {
    const id = setTimeout(() => setCanEnter(true), DURATION_IN + 400)
    return () => clearTimeout(id)
  }, [])

  function handleEnter() {
    if (!canEnter) return
    setCanEnter(false)
    setExiting(true)
    setPixelPhase('out')
    // Zoom fully completes at 1200ms then hand off to the map
    setTimeout(onEnter, 1200)
  }

  const exitStyle = exiting ? {
    opacity: 0,
    transform: 'scale(2.0)',
    filter: 'blur(6px)',
    transition: 'opacity 1.2s ease-in, transform 1.2s cubic-bezier(0.4, 0, 0.8, 1), filter 1.2s ease-in',
  } : {}

  return (
    <div style={{ ...styles.root, ...exitStyle }}>

      {/* Hex grid animation */}
      <HexGridBackground />

      {/* Radial vignette so edges are dark */}
      <div style={styles.vignette} />

      <div style={styles.content}>
        <div style={styles.pixelWrapper}>
          {/* Logo sits above — no scan effect */}
          <div style={styles.logoMark}>
            <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
              <polygon points="26,2 50,14 50,38 26,50 2,38 2,14" stroke="url(#sg)" strokeWidth="1.5" fill="none"/>
              <polygon points="26,10 42,18 42,34 26,42 10,34 10,18" stroke="url(#sg)" strokeWidth="1" fill="rgba(192,192,192,0.04)"/>
              <circle cx="26" cy="26" r="4" fill="url(#sg)"/>
              <defs>
                <linearGradient id="sg" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%"   stopColor="#e8e8e8"/>
                  <stop offset="40%"  stopColor="#ffffff"/>
                  <stop offset="70%"  stopColor="#a8a8a8"/>
                  <stop offset="100%" stopColor="#c8c8c8"/>
                </linearGradient>
              </defs>
            </svg>
          </div>

          {/* Wordmark only — this is what the scan pixelates */}
          <div ref={wrapperRef} style={{ position: 'relative' }}>
            <h1 style={styles.wordmark}>SENTINEL</h1>
            <canvas ref={canvasRef} style={styles.pixelCanvas} />
          </div>
        </div>

        {/* Rest fades in after pixel-in completes */}
        <div style={{
          ...styles.belowFold,
          opacity: canEnter || exiting ? 1 : 0,
          transform: canEnter || exiting ? 'translateY(0)' : 'translateY(10px)',
        }}>
          <p style={styles.tagline}>
            Conflict threat visibility for civilians in active combat zones
          </p>

          <div style={styles.divider}>
            <span style={styles.dividerLabel}>OPERATIONAL</span>
          </div>

          <div style={styles.statsRow}>
            <Stat value="4,735" label="Monitored Hexes" />
            <Stat value="15 min" label="Update Cycle" />
          </div>

          <button
            style={{ ...styles.btn, opacity: canEnter ? 1 : 0.4, cursor: canEnter ? 'pointer' : 'default' }}
            onClick={handleEnter}
          >
            ENTER
          </button>

          <p style={styles.disclaimer}>
            For situational awareness only · Not a substitute for official advisories
          </p>
        </div>
      </div>
    </div>
  )
}

function Stat({ value, label }) {
  return (
    <div style={{ textAlign: 'center', minWidth: 90 }}>
      <div style={{ color: '#d0d0d0', fontWeight: 700, fontSize: 18, letterSpacing: '0.02em' }}>{value}</div>
      <div style={{ color: '#3a3a4a', fontSize: 9, marginTop: 4, letterSpacing: '0.2em', textTransform: 'uppercase', fontWeight: 600 }}>{label}</div>
    </div>
  )
}

const styles = {
  root: {
    position: 'fixed',
    inset: 0,
    background: '#05050d',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
    fontFamily: 'system-ui, -apple-system, sans-serif',
    overflow: 'hidden',
  },
  vignette: {
    position: 'absolute',
    inset: 0,
    background: 'radial-gradient(ellipse at center, transparent 20%, rgba(5,5,13,0.6) 55%, #05050d 80%)',
    pointerEvents: 'none',
    zIndex: 1,
  },
  content: {
    position: 'relative',
    zIndex: 2,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  pixelWrapper: {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    paddingBottom: 8,
  },
  pixelCanvas: {
    position: 'absolute',
    inset: 0,
    pointerEvents: 'none',
    zIndex: 5,
  },
  logoMark: {
    marginBottom: 18,
    filter: 'drop-shadow(0 0 18px rgba(192,192,192,0.2))',
  },
  wordmark: {
    margin: 0,
    fontSize: 56,
    fontWeight: 900,
    letterSpacing: '0.45em',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    background: 'linear-gradient(180deg, #ffffff 0%, #c8c8c8 40%, #888 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
    lineHeight: 1,
    filter: 'drop-shadow(0 1px 0 rgba(0,0,0,0.8))',
  },
  belowFold: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    transition: 'opacity 0.6s ease 0.1s, transform 0.6s ease 0.1s',
  },
  tagline: {
    margin: '16px 0 0',
    color: '#3a3a4a',
    fontSize: 10,
    letterSpacing: '0.18em',
    textTransform: 'uppercase',
    maxWidth: 360,
    textAlign: 'center',
    lineHeight: 1.7,
    fontWeight: 500,
  },
  divider: {
    position: 'relative',
    width: 300,
    height: 1,
    background: 'linear-gradient(90deg, transparent, #2a2a3d, transparent)',
    margin: '28px 0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  dividerLabel: {
    position: 'absolute',
    background: '#05050d',
    padding: '0 10px',
    fontSize: 9,
    letterSpacing: '0.25em',
    color: '#2a4a2a',
    fontWeight: 700,
    textTransform: 'uppercase',
    border: '1px solid #1a2a1a',
    borderRadius: 1,
  },
  statsRow: {
    display: 'flex',
    gap: 40,
    marginBottom: 36,
  },
  btn: {
    background: 'transparent',
    border: '1px solid #3a3a4a',
    color: '#aaa',
    padding: '10px 52px',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.3em',
    borderRadius: 1,
    transition: 'border-color 0.2s, color 0.2s, opacity 0.3s',
    fontFamily: 'system-ui, sans-serif',
    textTransform: 'uppercase',
  },
  disclaimer: {
    marginTop: 20,
    color: '#2a2a3a',
    fontSize: 10,
    letterSpacing: '0.06em',
  },
}
