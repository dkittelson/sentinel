import { useState, useEffect } from 'react'
import { AlertBadge } from './AlertBadge'
import { STRATEGIC_TIER_COLORS, TIER_COLORS } from '../utils/tierColors'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function HexSidebar({ h3Id, onClose }) {
  const [data, setData]             = useState(null)
  const [loading, setLoading]       = useState(true)
  const [narrative, setNarrative]   = useState(null)
  const [narLoading, setNarLoading] = useState(false)

  useEffect(() => {
    if (!h3Id) return
    setLoading(true)
    setNarrative(null)

    fetch(`${API_URL}/hex/${h3Id}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))

    // Fetch LLM narrative with real news in parallel
    setNarLoading(true)
    fetch(`${API_URL}/hex/${h3Id}/narrative`)
      .then(r => r.json())
      .then(d => { setNarrative(d.narrative); setNarLoading(false) })
      .catch(() => setNarLoading(false))
  }, [h3Id])

  if (!h3Id) return null

  return (
    <div style={styles.panel}>
      <button style={styles.close} onClick={onClose}>✕</button>

      {loading ? (
        <p style={styles.muted}>Loading…</p>
      ) : !data ? (
        <p style={styles.muted}>No data for this hex.</p>
      ) : (
        <>
          {/* Header */}
          <div style={styles.header}>
            <AlertBadge tier={data.tactical_tier || 'CLEAR'} />
            <span style={styles.hexId}>{h3Id.slice(0, 12)}…</span>
          </div>

          {/* Gemini alert text */}
          {data.alert_text && (
            <div style={{ ...styles.alertBox, borderColor: TIER_COLORS.DANGER }}>
              <p style={styles.alertText}>{data.alert_text}</p>
            </div>
          )}

          {/* Tactical triggers */}
          {data.tactical_triggers && (
            <div style={styles.section}>
              <div style={styles.label}>Active triggers</div>
              {data.tactical_triggers.split(' | ').map((t, i) => (
                <div key={i} style={styles.trigger}>• {t}</div>
              ))}
            </div>
          )}

          {/* LLM narrative with real news */}
          <div style={styles.section}>
            <div style={styles.label}>
              Intelligence Summary
              <span style={{ color: '#3a7bd5', fontWeight: 500, marginLeft: 6, fontSize: 10 }}>⚡ web-grounded</span>
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
              <p style={styles.muted}>No recent intelligence available for this area.</p>
            )}
          </div>

          {/* Strategic score bar */}
          <div style={styles.section}>
            <div style={styles.label}>
              ML escalation probability
              <span style={{ ...styles.tier, color: STRATEGIC_TIER_COLORS[data.strategic_tier] || '#aaa' }}>
                {' '}{data.strategic_tier?.toUpperCase()}
              </span>
            </div>
            <div style={styles.barTrack}>
              <div style={{
                ...styles.barFill,
                width: `${(data.strategic_score || 0) * 100}%`,
                backgroundColor: STRATEGIC_TIER_COLORS[data.strategic_tier] || '#555',
              }} />
            </div>
            <div style={styles.barLabel}>{((data.strategic_score || 0) * 100).toFixed(0)}%</div>
          </div>

          {data.gdelt && (
            <div style={styles.section}>
              <div style={styles.label}>GDELT news signals (latest week)</div>
              <StatRow label="Hostility"     value={(data.gdelt.gdelt_hostility || 0).toFixed(2)} />
              <StatRow label="Avg tone"      value={(data.gdelt.gdelt_avg_tone || 0).toFixed(1)} />
              <StatRow label="Min Goldstein" value={(data.gdelt.gdelt_min_goldstein || 0).toFixed(1)} />
              <StatRow label="Articles"      value={data.gdelt.gdelt_num_articles || 0} />
            </div>
          )}

          {data.firms && data.firms.firms_hotspot_count > 0 && (
            <div style={styles.section}>
              <div style={styles.label}>NASA FIRMS thermal (latest week)</div>
              <StatRow label="Hotspots"  value={data.firms.firms_hotspot_count} />
              <StatRow label="Max FRP"   value={`${(data.firms.firms_max_frp || 0).toFixed(0)} MW`} />
              <StatRow label="Spike flag" value={data.firms.firms_spike ? 'Yes' : 'No'} />
            </div>
          )}

          {data.recent_events?.length > 0 && (
            <div style={styles.section}>
              <div style={styles.label}>Recent ACLED events</div>
              {data.recent_events.map((ev, i) => (
                <div key={i} style={styles.event}>
                  <span style={styles.eventDate}>{ev.event_date}</span>
                  <span style={styles.eventType}>{ev.event_type}</span>
                  {ev.fatalities > 0 && (
                    <span style={styles.fatalities}>{ev.fatalities} fatalities</span>
                  )}
                </div>
              ))}
            </div>
          )}

          <div style={styles.footer}>
            Scored at: {data.scored_at ? new Date(data.scored_at).toLocaleString() : '—'}
          </div>
        </>
      )}
    </div>
  )
}

function StatRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
      <span style={styles.muted}>{label}</span>
      <span style={{ color: '#eee', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

const styles = {
  panel: {
    position: 'absolute',
    top: 16,
    right: 16,
    width: 320,
    maxHeight: 'calc(100vh - 32px)',
    overflowY: 'auto',
    background: '#12121f',
    border: '1px solid #2a2a3d',
    borderRadius: 8,
    padding: '16px 18px',
    color: '#ddd',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 13,
    zIndex: 10,
    boxShadow: '0 4px 24px rgba(0,0,0,0.6)',
  },
  close: {
    position: 'absolute',
    top: 10,
    right: 12,
    background: 'none',
    border: 'none',
    color: '#888',
    fontSize: 16,
    cursor: 'pointer',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 14,
    paddingTop: 2,
  },
  hexId: {
    color: '#666',
    fontSize: 11,
    fontFamily: 'monospace',
  },
  alertBox: {
    border: '1px solid',
    borderRadius: 6,
    padding: '10px 12px',
    marginBottom: 14,
    background: 'rgba(231,76,60,0.08)',
  },
  alertText: {
    margin: 0,
    lineHeight: 1.5,
    color: '#f5a19a',
  },
  section: {
    marginBottom: 16,
  },
  label: {
    color: '#888',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginBottom: 6,
  },
  tier: {
    fontWeight: 700,
  },
  trigger: {
    color: '#ccc',
    marginBottom: 3,
    lineHeight: 1.4,
  },
  barTrack: {
    height: 6,
    background: '#2a2a3d',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 4,
  },
  barFill: {
    height: '100%',
    borderRadius: 3,
    transition: 'width 0.3s ease',
  },
  barLabel: {
    color: '#888',
    fontSize: 11,
    textAlign: 'right',
  },
  stat: {
    color: '#eee',
    fontWeight: 600,
    fontSize: 18,
  },
  muted: {
    color: '#666',
  },
  narrative: {
    margin: 0,
    color: '#d0d0d0',
    lineHeight: 1.65,
    fontSize: 13,
  },
  narrativeSkeleton: {
    display: 'flex',
    flexDirection: 'column',
    gap: 7,
  },
  skeletonLine: {
    height: 11,
    borderRadius: 4,
    background: 'linear-gradient(90deg, #1a1a2e, #22223a, #1a1a2e)',
    backgroundSize: '200% 100%',
  },
  event: {
    display: 'flex',
    gap: 8,
    marginBottom: 5,
    flexWrap: 'wrap',
  },
  eventDate: {
    color: '#888',
    fontFamily: 'monospace',
    fontSize: 11,
  },
  eventType: {
    color: '#ccc',
  },
  fatalities: {
    color: '#e74c3c',
    fontWeight: 600,
  },
  footer: {
    color: '#555',
    fontSize: 11,
    borderTop: '1px solid #2a2a3d',
    paddingTop: 10,
    marginTop: 4,
  },
}
