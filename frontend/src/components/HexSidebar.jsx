import { useState, useEffect } from 'react'
import { t } from '../i18n'
import { useLang } from './LangToggle'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TIER_COLOR  = { red: '#e74c3c', orange: '#f09438', yellow: '#f1c40f', green: '#2ecc71' }
const TIER_LABEL  = { red: 'HIGH RISK', orange: 'ELEVATED', yellow: 'MODERATE', green: 'LOW' }
const TACTC_COLOR = { DANGER: '#c0392b', WARNING: '#e67e22', WATCH: '#f1c40f', CLEAR: '#2ecc71' }

export function HexSidebar({ h3Id, onClose, backtestDate }) {
  const [data,      setData]      = useState(null)
  const [drivers,   setDrivers]   = useState(null)
  const [narrative, setNarrative] = useState(null)
  const [clusterIds,setClusterIds]= useState([])
  const [loading,   setLoading]   = useState(true)
  const [narLoading,setNarLoading]= useState(false)
  const [history,   setHistory]   = useState([])
  useLang()

  useEffect(() => {
    if (!h3Id) return
    setLoading(true)
    setNarrative(null)
    setClusterIds([])
    setDrivers(null)
    setHistory([])

    // Fetch hex data, drivers, and 14-day score history in parallel
    Promise.all([
      fetch(`${API_URL}/hex/${h3Id}`).then(r => r.json()),
      fetch(`${API_URL}/hex/${h3Id}/drivers`).then(r => r.json()),
      fetch(`${API_URL}/hex/${h3Id}/history?days=14`).then(r => r.json()).catch(() => []),
    ])
      .then(([d, dr, hist]) => { setData(d); setDrivers(dr); setHistory(hist || []); setLoading(false) })
      .catch(() => setLoading(false))

    // Narrative (can arrive later)
    const dateParam = backtestDate ? `&date=${backtestDate}` : ''
    setNarLoading(true)
    fetch(`${API_URL}/hex/${h3Id}/cluster-narrative?${dateParam}`)
      .then(r => r.json())
      .then(d => { setNarrative(d.narrative); setClusterIds(d.cluster_ids || []); setNarLoading(false) })
      .catch(() =>
        fetch(`${API_URL}/hex/${h3Id}/narrative`)
          .then(r => r.json())
          .then(d => { setNarrative(d.narrative); setNarLoading(false) })
          .catch(() => setNarLoading(false))
      )
  }, [h3Id, backtestDate])

  if (!h3Id) return null

  const tier   = data?.strategic_tier || 'green'
  const score  = data?.strategic_score ?? null
  const tacticalTier = data?.tactical_tier || null

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
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ ...styles.tierPill, background: TIER_COLOR[tier] }}>
                {TIER_LABEL[tier]}
              </span>
              {tacticalTier && tacticalTier !== 'CLEAR' && (
                <span style={{ ...styles.tierPill, background: TACTC_COLOR[tacticalTier] || '#888', fontSize: 10 }}>
                  {tacticalTier}
                </span>
              )}
              {clusterIds.length > 1 && (
                <span style={{ color: '#666', fontSize: 10 }}>
                  {clusterIds.length} hexes
                </span>
              )}
            </div>
          </div>

          {/* ── Score bar ── */}
          {score !== null && <ScoreBar score={score} tier={tier} />}

          {/* ── 14-day risk sparkline ── */}
          {history.length >= 2 && <RiskSparkline history={history} tier={tier} />}

          {/* ── Driver chips ── */}
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

          {/* ── Intelligence narrative ── */}
          <div style={styles.section}>
            <div style={styles.label}>
              {t('intelSummary')}
            </div>
            {narLoading ? (
              <div style={styles.narrativeSkeleton}>
                {[100, 88, 95, 72].map((w, i) => (
                  <div key={i} style={{ ...styles.skeletonLine, width: `${w}%` }} />
                ))}
              </div>
            ) : narrative ? (
              <p style={styles.narrative}>{narrative}</p>
            ) : (
              <p style={styles.muted}>{t('noIntel')}</p>
            )}
          </div>

          {/* ── GDELT signals ── */}
          {data.gdelt && (
            <div style={styles.section}>
              <div style={styles.label}>{t('gdeltSignals')}</div>
              <StatRow label={t('hostility')}    value={(data.gdelt.gdelt_hostility || 0).toFixed(2)} accent={data.gdelt.gdelt_hostility > 0.5} />
              <StatRow label={t('avgTone')}      value={(data.gdelt.gdelt_avg_tone || 0).toFixed(1)} />
              <StatRow label={t('minGoldstein')} value={(data.gdelt.gdelt_min_goldstein || 0).toFixed(1)} />
              <StatRow label={t('articles')}     value={data.gdelt.gdelt_num_articles || 0} />
            </div>
          )}

          {/* ── FIRMS thermal ── */}
          {data.firms && data.firms.firms_hotspot_count > 0 && (
            <div style={styles.section}>
              <div style={styles.label}>{t('firmsThermal')}</div>
              <StatRow label={t('hotspots')}   value={data.firms.firms_hotspot_count} accent />
              <StatRow label={t('maxFrp')}     value={`${(data.firms.firms_max_frp || 0).toFixed(0)} MW`} />
              <StatRow label={t('spikeFlag')}  value={data.firms.firms_spike ? `⚠ ${t('yes')}` : t('no')} accent={data.firms.firms_spike} />
            </div>
          )}

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

          <div style={styles.footer}>
            {t('scored')} {data.scored_at ? new Date(data.scored_at).toLocaleString() : '—'}
          </div>
        </>
      )}
    </div>
  )
}


// ── Score bar ─────────────────────────────────────────────────────────────────

function ScoreBar({ score, tier }) {
  const pct = Math.round(score * 100)
  const fillColor = TIER_COLOR[tier] || '#2ecc71'

  // Threshold positions as percentages of the 0-1 bar
  const thresholds = [
    { pct: 54, label: 'Y', color: '#f1c40f' },
    { pct: 63, label: 'O', color: '#f09438' },
    { pct: 70, label: 'R', color: '#e74c3c' },
  ]

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={styles.label}>Risk score</span>
        <span style={{ color: fillColor, fontWeight: 700, fontSize: 13 }}>{pct}%</span>
      </div>
      <div style={styles.barTrack}>
        {/* Fill */}
        <div style={{ ...styles.barFill, width: `${pct}%`, background: fillColor }} />
        {/* Threshold tick marks */}
        {thresholds.map(t => (
          <div key={t.label} style={{
            position: 'absolute',
            left: `${t.pct}%`,
            top: 0,
            bottom: 0,
            width: 1,
            background: t.color,
            opacity: 0.6,
          }} />
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 2, fontSize: 10, color: '#555' }}>
        <span>0</span>
        <span style={{ color: '#f1c40f' }}>54</span>
        <span style={{ color: '#f09438' }}>63</span>
        <span style={{ color: '#e74c3c' }}>70</span>
        <span>100</span>
      </div>
    </div>
  )
}


// ── Risk sparkline ────────────────────────────────────────────────────────────

function RiskSparkline({ history, tier }) {
  const W = 268, H = 56
  const PAD = { t: 6, r: 4, b: 16, l: 28 }
  const iw = W - PAD.l - PAD.r
  const ih = H - PAD.t - PAD.b

  const scores = history.map(d => d.strategic_score)
  const n = scores.length

  // Threshold lines (same as ScoreBar: 0.54, 0.63, 0.70)
  const THRESHOLDS = [
    { v: 0.54, color: '#f1c40f' },
    { v: 0.63, color: '#f09438' },
    { v: 0.70, color: '#e74c3c' },
  ]

  const px = i => PAD.l + (i / Math.max(n - 1, 1)) * iw
  const py = v => PAD.t + ih - v * ih   // score 0=bottom, 1=top

  // Polyline points for the history line
  const pts = scores.map((s, i) => `${px(i).toFixed(1)},${py(s).toFixed(1)}`).join(' ')

  // 3-day trend projection from the last 7 data points
  const lookback = Math.min(7, n)
  const ys = scores.slice(-lookback)
  const xs = ys.map((_, i) => i)
  const xm = xs.reduce((a, b) => a + b, 0) / lookback
  const ym = ys.reduce((a, b) => a + b, 0) / lookback
  const slope = xs.reduce((acc, x, i) => acc + (x - xm) * (ys[i] - ym), 0) /
                (xs.reduce((acc, x) => acc + (x - xm) ** 2, 0) || 1)
  const intercept = ym - slope * xm

  // Project 3 steps ahead (3 days)
  const projScore = Math.min(1, Math.max(0, intercept + slope * (lookback - 1 + 3)))
  const projX = px(n - 1 + 3 * (iw / (Math.max(n - 1, 1) * iw)) * iw).toFixed(1)  // x for +3 steps
  // Simpler: extend x by 3/(n-1) * iw from last point
  const lastX = px(n - 1)
  const extX  = Math.min(W - PAD.r, lastX + (iw / Math.max(n - 1, 1)) * 3)
  const extY  = py(projScore)

  const lineColor = TIER_COLOR[tier] || '#2ecc71'

  const trendDir = slope > 0.002 ? '↗' : slope < -0.002 ? '↘' : '→'
  const trendColor = slope > 0.002 ? '#e74c3c' : slope < -0.002 ? '#2ecc71' : '#888'

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={styles.label}>{t('riskTrend14d')}</span>
        <span style={{ fontSize: 12, color: trendColor, fontWeight: 700 }}>{trendDir} trend</span>
      </div>
      <svg width={W} height={H} style={{ display: 'block', overflow: 'visible' }}>
        {/* Y-axis labels */}
        {[0, 0.5, 1].map(v => (
          <text key={v} x={PAD.l - 4} y={py(v) + 3} textAnchor="end"
            fontSize="8" fill="#444">{(v * 100).toFixed(0)}</text>
        ))}

        {/* Threshold lines */}
        {THRESHOLDS.map(t => (
          <line key={t.v}
            x1={PAD.l} y1={py(t.v)} x2={W - PAD.r} y2={py(t.v)}
            stroke={t.color} strokeWidth="0.5" strokeOpacity="0.4" strokeDasharray="2,2" />
        ))}

        {/* History line */}
        <polyline
          points={pts}
          fill="none"
          stroke={lineColor}
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Trend projection (dashed) */}
        <line
          x1={lastX} y1={py(scores[n - 1])}
          x2={extX}  y2={extY}
          stroke={lineColor} strokeWidth="1" strokeDasharray="3,2" strokeOpacity="0.6"
        />

        {/* Data dots — only first, last, and any tier-change points */}
        {[0, n - 1].map(i => (
          <circle key={i} cx={px(i)} cy={py(scores[i])} r="2.5"
            fill={TIER_COLOR[history[i]?.strategic_tier] || lineColor} />
        ))}

        {/* Projection dot */}
        <circle cx={extX} cy={extY} r="2" fill="none"
          stroke={lineColor} strokeWidth="1" strokeOpacity="0.6" />

        {/* X-axis labels: first and last date */}
        {history.length > 0 && (
          <>
            <text x={PAD.l} y={H} textAnchor="middle" fontSize="8" fill="#444">
              {history[0].date.slice(5)}
            </text>
            <text x={lastX} y={H} textAnchor="middle" fontSize="8" fill="#444">
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
      {[80, 100, 60, 100, 90, 70].map((w, i) => (
        <div key={i} style={{ ...styles.skeletonLine, width: `${w}%`, marginBottom: 10 }} />
      ))}
    </div>
  )
}

function StatRow({ label, value, accent }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
      <span style={styles.muted}>{label}</span>
      <span style={{ color: accent ? '#f09438' : '#eee', fontWeight: 500 }}>{value}</span>
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
    borderRadius: 10,
    padding: '16px 16px 12px',
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
    top: 10,
    right: 12,
    background: 'none',
    border: 'none',
    color: '#555',
    fontSize: 16,
    cursor: 'pointer',
    padding: 4,
    lineHeight: 1,
    transition: 'color 0.15s',
  },
  header: {
    marginBottom: 12,
    paddingTop: 2,
    paddingRight: 20,
  },
  tierPill: {
    display: 'inline-block',
    padding: '3px 10px',
    borderRadius: 20,
    color: '#fff',
    fontWeight: 700,
    fontSize: 11,
    letterSpacing: '0.07em',
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
    height: 7,
    background: '#1e1e30',
    borderRadius: 4,
    overflow: 'visible',
  },
  barFill: {
    height: '100%',
    borderRadius: 4,
    transition: 'width 0.4s ease',
  },
  section: {
    marginBottom: 14,
    borderTop: '1px solid #1e1e30',
    paddingTop: 10,
  },
  label: {
    color: '#666',
    fontSize: 10,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    marginBottom: 6,
  },
  muted: {
    color: '#555',
    fontSize: 12,
  },
  narrative: {
    margin: 0,
    color: '#ccc',
    lineHeight: 1.65,
    fontSize: 12,
  },
  narrativeSkeleton: {
    display: 'flex',
    flexDirection: 'column',
    gap: 7,
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
    marginBottom: 5,
    flexWrap: 'wrap',
    alignItems: 'baseline',
  },
  eventDate: {
    color: '#555',
    fontFamily: 'monospace',
    fontSize: 11,
  },
  eventType: {
    color: '#bbb',
    fontSize: 12,
  },
  fatalities: {
    color: '#e74c3c',
    fontWeight: 700,
    fontSize: 11,
  },
  footer: {
    color: '#444',
    fontSize: 10,
    borderTop: '1px solid #1e1e30',
    paddingTop: 8,
    marginTop: 2,
  },
}
