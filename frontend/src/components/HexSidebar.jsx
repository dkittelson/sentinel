import { useState, useEffect } from 'react'
import { t } from '../i18n'
import { useLang } from './LangToggle'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TIER_COLOR = { red: '#e74c3c', orange: '#f09438', yellow: '#f1c40f', green: '#2ecc71' }
const TIER_LABEL = { red: 'High Risk', orange: 'Elevated', yellow: 'Moderate', green: 'Low Risk' }
const TIER_SUBTEXT = {
  red:    'Active conflict patterns detected',
  orange: 'Elevated tension in this area',
  yellow: 'Situation requires monitoring',
  green:  'No significant risk indicators',
}

export function HexSidebar({ h3Id, onClose, backtestDate }) {
  const [data,      setData]      = useState(null)
  const [drivers,   setDrivers]   = useState(null)
  const [narrative, setNarrative] = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [narLoading,setNarLoading]= useState(false)
  const [history,   setHistory]   = useState([])
  useLang()

  useEffect(() => {
    if (!h3Id) return
    setLoading(true)
    setNarrative(null)
    setDrivers(null)
    setHistory([])

    Promise.all([
      fetch(`${API_URL}/hex/${h3Id}`).then(r => r.json()),
      fetch(`${API_URL}/hex/${h3Id}/drivers`).then(r => r.json()),
      fetch(`${API_URL}/hex/${h3Id}/history?days=14`).then(r => r.json()).catch(() => []),
    ])
      .then(([d, dr, hist]) => { setData(d); setDrivers(dr); setHistory(hist || []); setLoading(false) })
      .catch(() => setLoading(false))

    const dateParam = backtestDate ? `&date=${backtestDate}` : ''
    setNarLoading(true)
    fetch(`${API_URL}/hex/${h3Id}/cluster-narrative?${dateParam}`)
      .then(r => r.json())
      .then(d => { setNarrative(d.narrative); setNarLoading(false) })
      .catch(() =>
        fetch(`${API_URL}/hex/${h3Id}/narrative`)
          .then(r => r.json())
          .then(d => { setNarrative(d.narrative); setNarLoading(false) })
          .catch(() => setNarLoading(false))
      )
  }, [h3Id, backtestDate])

  if (!h3Id) return null

  const tier  = data?.strategic_tier || 'green'
  const score = data?.strategic_score ?? null

  return (
    <div style={styles.panel}>
      <button style={styles.close} onClick={onClose} aria-label="Close">✕</button>

      {loading ? (
        <LoadingSkeleton />
      ) : !data ? (
        <p style={styles.muted}>No data for this hex.</p>
      ) : (
        <>
          {/* ── Risk header ── */}
          <div style={styles.header}>
            <div style={{ ...styles.tierPill, background: TIER_COLOR[tier] }}>
              {TIER_LABEL[tier]}
            </div>
            <p style={{ ...styles.tierSubtext, color: TIER_COLOR[tier] }}>
              {TIER_SUBTEXT[tier]}
            </p>
          </div>

          {/* ── Score bar (clean, no threshold numbers) ── */}
          {score !== null && <ScoreBar score={score} tier={tier} />}

          {/* ── Intelligence briefing (hero content) ── */}
          <div style={styles.section}>
            <div style={styles.label}>{t('intelSummary')}</div>
            {narLoading ? (
              <div style={styles.narrativeSkeleton}>
                {[100, 88, 95, 72, 85].map((w, i) => (
                  <div key={i} style={{ ...styles.skeletonLine, width: `${w}%` }} />
                ))}
              </div>
            ) : narrative ? (
              <p style={styles.narrative}>{narrative}</p>
            ) : (
              <p style={styles.muted}>{t('noIntel')}</p>
            )}
          </div>

          {/* ── Recent ACLED events ── */}
          {data.recent_events?.length > 0 && (
            <div style={styles.section}>
              <div style={styles.label}>{t('recentEvents')}</div>
              {data.recent_events.map((ev, i) => (
                <div key={i} style={styles.event}>
                  <span style={styles.eventDate}>{ev.event_date}</span>
                  <span style={styles.eventType}>{ev.event_type}</span>
                  {ev.fatalities > 0 && (
                    <span style={styles.fatalities}>{ev.fatalities} {t('fatalities')}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* ── Active signals ── */}
          {drivers?.drivers?.length > 0 && (
            <div style={styles.section}>
              <div style={styles.label}>{t('activeTriggers')}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 4 }}>
                {drivers.drivers.map((d, i) => (
                  <span key={i} style={{ ...styles.chip, borderColor: d.color, color: d.color }}>
                    {d.label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ── 14-day trend (at bottom, supplementary) ── */}
          {history.length >= 2 && <RiskSparkline history={history} tier={tier} />}
        </>
      )}
    </div>
  )
}


// ── Score bar (simplified — no threshold tick marks) ──────────────────────────

function ScoreBar({ score, tier }) {
  const pct = Math.round(score * 100)
  const fillColor = TIER_COLOR[tier] || '#2ecc71'

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={styles.barTrack}>
        <div style={{ ...styles.barFill, width: `${pct}%`, background: fillColor }} />
      </div>
    </div>
  )
}


// ── Risk sparkline (simplified — no threshold lines, no Y-axis numbers) ───────

function RiskSparkline({ history, tier }) {
  const W = 268, H = 48
  const PAD = { t: 4, r: 4, b: 14, l: 6 }
  const iw = W - PAD.l - PAD.r
  const ih = H - PAD.t - PAD.b

  const scores = history.map(d => d.strategic_score)
  const n = scores.length

  const px = i => PAD.l + (i / Math.max(n - 1, 1)) * iw
  const py = v => PAD.t + ih - v * ih

  const pts = scores.map((s, i) => `${px(i).toFixed(1)},${py(s).toFixed(1)}`).join(' ')

  const lookback = Math.min(7, n)
  const ys = scores.slice(-lookback)
  const xs = ys.map((_, i) => i)
  const xm = xs.reduce((a, b) => a + b, 0) / lookback
  const ym = ys.reduce((a, b) => a + b, 0) / lookback
  const slope = xs.reduce((acc, x, i) => acc + (x - xm) * (ys[i] - ym), 0) /
                (xs.reduce((acc, x) => acc + (x - xm) ** 2, 0) || 1)

  const trendDir   = slope > 0.002 ? '↗ Rising' : slope < -0.002 ? '↘ Easing' : '→ Stable'
  const trendColor = slope > 0.002 ? '#e74c3c' : slope < -0.002 ? '#2ecc71' : '#888'
  const lineColor  = TIER_COLOR[tier] || '#2ecc71'

  return (
    <div style={styles.section}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={styles.label}>{t('riskTrend14d')}</span>
        <span style={{ fontSize: 11, color: trendColor, fontWeight: 700 }}>{trendDir}</span>
      </div>
      <svg width={W} height={H} style={{ display: 'block', overflow: 'visible' }}>
        <polyline
          points={pts}
          fill="none"
          stroke={lineColor}
          strokeWidth="1.8"
          strokeLinejoin="round"
          strokeLinecap="round"
          strokeOpacity="0.85"
        />
        {[0, n - 1].map(i => (
          <circle key={i} cx={px(i)} cy={py(scores[i])} r="2.5"
            fill={TIER_COLOR[history[i]?.strategic_tier] || lineColor} />
        ))}
        {history.length > 0 && (
          <>
            <text x={PAD.l} y={H} textAnchor="start" fontSize="9" fill="#444">
              {history[0].date.slice(5)}
            </text>
            <text x={W - PAD.r} y={H} textAnchor="end" fontSize="9" fill="#444">
              {history[n - 1].date.slice(5)}
            </text>
          </>
        )}
      </svg>
    </div>
  )
}


// ── Sub-components ────────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div style={{ paddingTop: 8 }}>
      {[60, 100, 80, 100, 90, 70, 85].map((w, i) => (
        <div key={i} style={{ ...styles.skeletonLine, width: `${w}%`, marginBottom: 10 }} />
      ))}
    </div>
  )
}


// ── Styles ────────────────────────────────────────────────────────────────────

const styles = {
  panel: {
    position: 'absolute',
    top: 16,
    right: 16,
    width: 300,
    maxHeight: 'calc(100vh - 32px)',
    overflowY: 'auto',
    background: '#12121f',
    border: '1px solid #2a2a3d',
    borderRadius: 12,
    padding: '20px 18px 16px',
    color: '#ddd',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 13,
    zIndex: 10,
    boxShadow: '0 4px 32px rgba(0,0,0,0.7)',
    scrollbarWidth: 'thin',
    scrollbarColor: '#2a2a3d transparent',
  },
  close: {
    position: 'absolute',
    top: 12,
    right: 14,
    background: 'none',
    border: 'none',
    color: '#444',
    fontSize: 15,
    cursor: 'pointer',
    padding: 4,
    lineHeight: 1,
    transition: 'color 0.15s',
  },
  header: {
    marginBottom: 14,
    paddingRight: 20,
  },
  tierPill: {
    display: 'inline-block',
    padding: '5px 14px',
    borderRadius: 20,
    color: '#fff',
    fontWeight: 700,
    fontSize: 13,
    letterSpacing: '0.04em',
    marginBottom: 6,
  },
  tierSubtext: {
    margin: 0,
    fontSize: 12,
    opacity: 0.8,
    fontWeight: 500,
  },
  chip: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 12,
    border: '1px solid',
    fontSize: 11,
    fontWeight: 500,
    background: 'rgba(255,255,255,0.03)',
  },
  barTrack: {
    position: 'relative',
    height: 4,
    background: '#1e1e30',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 16,
  },
  barFill: {
    height: '100%',
    borderRadius: 4,
    transition: 'width 0.5s ease',
    opacity: 0.85,
  },
  section: {
    marginBottom: 16,
    borderTop: '1px solid #1a1a2c',
    paddingTop: 12,
  },
  label: {
    color: '#555',
    fontSize: 10,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.09em',
    marginBottom: 8,
  },
  muted: {
    color: '#555',
    fontSize: 12,
    margin: 0,
    lineHeight: 1.6,
  },
  narrative: {
    margin: 0,
    color: '#c8c8d4',
    lineHeight: 1.7,
    fontSize: 13,
  },
  narrativeSkeleton: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  skeletonLine: {
    height: 10,
    borderRadius: 3,
    background: 'linear-gradient(90deg, #1a1a2e 0%, #22223a 50%, #1a1a2e 100%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.4s ease infinite',
  },
  event: {
    display: 'flex',
    gap: 8,
    marginBottom: 7,
    flexWrap: 'wrap',
    alignItems: 'baseline',
  },
  eventDate: {
    color: '#444',
    fontFamily: 'monospace',
    fontSize: 11,
  },
  eventType: {
    color: '#bbb',
    fontSize: 12,
  },
  fatalities: {
    color: '#c0392b',
    fontWeight: 700,
    fontSize: 11,
  },
}