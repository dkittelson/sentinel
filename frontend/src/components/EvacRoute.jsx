import { useState } from 'react'
import { t } from '../i18n'
import { useLang } from './LangToggle'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function modeMeta(mode) {
  const map = {
    driving: { icon: '🚗', labelKey: 'drive', color: '#2ecc71' },
    walking: { icon: '🚶', labelKey: 'walk',  color: '#3498db' },
    cycling: { icon: '🚲', labelKey: 'cycle', color: '#9b59b6' },
  }
  return map[mode] || map.driving
}

function shelterIcon(type) {
  return type === 'hospital' ? '🏥' : type === 'un_shelter' ? '🇺🇳' :
         type === 'red_cross' ? '⛑️' : type === 'evacuation_point' ? '✈️' : '📍'
}


// ── Route card (one option) ───────────────────────────────────────────────────

function RouteCard({ route, selected, onSelect }) {
  const meta = modeMeta(route.mode)
  const hasWarning = route.danger_hexes_on_route?.length > 0

  return (
    <button
      style={{
        ...styles.card,
        borderColor: selected ? meta.color : '#2a2a3d',
        background: selected ? `rgba(${hexToRgb(meta.color)}, 0.08)` : 'rgba(255,255,255,0.02)',
      }}
      onClick={() => onSelect(route)}
      aria-pressed={selected}
    >
      <div style={styles.cardTop}>
        <span style={{ fontSize: 18 }}>{meta.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ ...styles.cardDest, color: selected ? meta.color : '#ddd' }}>
            {route.destination}{route.destination_country ? `, ${route.destination_country}` : ''}
          </div>
          <div style={styles.cardMeta}>
            {route.distance_km} km
            {route.duration_min ? ` · ~${Math.round(route.duration_min)} min` : ''}
          </div>
        </div>
        <span style={{ ...styles.modeTag, color: meta.color, borderColor: meta.color }}>
          {t(meta.labelKey)}
        </span>
      </div>
      {hasWarning && (
        <div style={styles.cardWarning}>
          ⚠ {route.danger_hexes_on_route.length} danger zone{route.danger_hexes_on_route.length > 1 ? 's' : ''} on route
        </div>
      )}
    </button>
  )
}


// ── Main panel ────────────────────────────────────────────────────────────────

export function EvacRoute({ active, routeData, loading, error, onClose, onRouteSelect, onRetry }) {
  const [selectedIdx, setSelectedIdx] = useState(0)
  useLang()  // re-render on language change

  if (!active) return null

  const routes    = routeData?.routes ?? (routeData ? [routeData] : [])
  const selected  = routes[selectedIdx] || routeData
  const hasRoutes = routes.length > 0 && routes.some(r => r.route_points?.length > 1)

  function handleSelect(route) {
    const idx = routes.findIndex(r => r.destination === route.destination && r.mode === route.mode)
    setSelectedIdx(idx >= 0 ? idx : 0)
    onRouteSelect?.(route)
  }

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>{t('evacuationRoute')}</span>
        <button style={styles.closeBtn} onClick={onClose} aria-label="Close">✕</button>
      </div>

      {loading ? (
        <div style={styles.loadingContainer}>
          <div style={styles.pulseRing} />
          <p style={styles.loadingText}>{t('findingSafe')}</p>
        </div>
      ) : error || !hasRoutes ? (
        <div style={styles.errorBlock}>
          <p style={styles.errorText}>{error || t('noSafeRoute')}</p>
          {onRetry && (
            <button style={styles.retryBtn} onClick={onRetry}>
              {t('retry')}
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Route option cards */}
          {routes.length > 1 && (
            <div style={styles.cardsSection}>
              <div style={styles.label}>{t('chooseRoute')}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {routes.map((r, i) => (
                  <RouteCard
                    key={`${r.destination}-${r.mode}`}
                    route={r}
                    selected={i === selectedIdx}
                    onSelect={handleSelect}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Single route summary (when only one option or selection made) */}
          {routes.length <= 1 && selected && (
            <div style={styles.destRow}>
              <div style={{ fontSize: 22 }}>📍</div>
              <div>
                <div style={styles.destName}>
                  {selected.destination}{selected.destination_country ? `, ${selected.destination_country}` : ''}
                </div>
                <div style={styles.destMeta}>
                  {selected.distance_km} km
                  {selected.duration_min ? ` · ~${Math.round(selected.duration_min)} min drive` : ''}
                  {selected.danger_hexes_on_route?.length > 0 && (
                    <span style={{ color: '#e74c3c', marginLeft: 8 }}>
                      ⚠ {selected.danger_hexes_on_route.length} danger zone{selected.danger_hexes_on_route.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* AI narrative (always for the best route) */}
          {routeData.narrative && (
            <div style={styles.narrative}>
              <p style={styles.narrativeText}>{routeData.narrative}</p>
            </div>
          )}

          {/* Nearest shelter */}
          {(selected?.nearest_shelter || routeData.nearest_shelter) && (() => {
            const sh = selected?.nearest_shelter || routeData.nearest_shelter
            return (
              <div style={styles.shelter}>
                <span style={{ fontSize: 20 }}>{shelterIcon(sh.type)}</span>
                <div>
                  <div style={styles.shelterName}>{sh.name}</div>
                  <div style={styles.shelterDist}>
                    {sh.distance_km} km · {sh.notes || sh.type || ''}
                  </div>
                </div>
              </div>
            )
          })()}

          <button style={styles.closeBtnBottom} onClick={onClose}>
            {t('closeRoute')}
          </button>
        </>
      )}
    </div>
  )
}


// ── Hook ──────────────────────────────────────────────────────────────────────

export function useEvacRoute() {
  const [active,    setActive]    = useState(false)
  const [routeData, setRouteData] = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)
  const [lastReq,   setLastReq]   = useState(null)  // for retry

  const activate   = () => { setActive(true); setRouteData(null); setError(null) }
  const deactivate = () => {
    setActive(false); setRouteData(null); setLoading(false); setError(null); setLastReq(null)
  }

  const fetchRoute = async (lat, lng, backtestDate = null) => {
    setLoading(true)
    setError(null)
    setLastReq({ lat, lng, backtestDate })
    try {
      let url = `${API_URL}/evac-route?from_lat=${lat}&from_lng=${lng}`
      if (backtestDate) url += `&date=${backtestDate}`
      const res  = await fetch(url)
      if (!res.ok) {
        const body = await res.text().catch(() => '')
        throw new Error(`Route service error (${res.status}). ${body.slice(0, 120)}`)
      }
      const data = await res.json()
      setRouteData(data)
    } catch (err) {
      console.error('Evac route failed:', err)
      setRouteData(null)
      setError(err.message || 'Failed to fetch route')
    } finally {
      setLoading(false)
    }
  }

  const retry = () => {
    if (lastReq) fetchRoute(lastReq.lat, lastReq.lng, lastReq.backtestDate)
  }

  return { active, routeData, loading, error, activate, deactivate, fetchRoute, retry }
}


// ── Helpers ───────────────────────────────────────────────────────────────────

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r}, ${g}, ${b}`
}


// ── Styles ────────────────────────────────────────────────────────────────────

const styles = {
  panel: {
    position: 'absolute',
    bottom: 24,
    right: 16,
    width: 310,
    maxHeight: '70vh',
    overflowY: 'auto',
    background: 'rgba(12, 12, 22, 0.96)',
    border: '1px solid #2ecc71',
    borderRadius: 10,
    padding: '14px 14px 12px',
    color: '#ddd',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 13,
    zIndex: 25,
    boxShadow: '0 4px 32px rgba(0,0,0,0.7), 0 0 24px rgba(46,204,113,0.08)',
    scrollbarWidth: 'thin',
    scrollbarColor: '#2a2a3d transparent',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    fontWeight: 700,
    fontSize: 12,
    letterSpacing: '0.1em',
    color: '#2ecc71',
    textTransform: 'uppercase',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#555',
    fontSize: 16,
    cursor: 'pointer',
    padding: 4,
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '20px 0',
    gap: 12,
  },
  pulseRing: {
    width: 36,
    height: 36,
    border: '2px solid #2ecc71',
    borderRadius: '50%',
    opacity: 0.6,
  },
  loadingText: { color: '#666', fontSize: 12, margin: 0 },
  prompt: {
    color: '#666',
    fontSize: 12,
    textAlign: 'center',
    padding: '16px 4px',
    margin: 0,
    lineHeight: 1.6,
  },
  errorBlock: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    padding: '16px 4px',
  },
  errorText: {
    color: '#f09438',
    fontSize: 12,
    textAlign: 'center',
    margin: 0,
    lineHeight: 1.6,
  },
  retryBtn: {
    background: 'rgba(46, 204, 113, 0.12)',
    border: '1px solid #2ecc71',
    color: '#2ecc71',
    fontSize: 11,
    fontWeight: 700,
    padding: '6px 18px',
    borderRadius: 6,
    cursor: 'pointer',
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    fontFamily: 'system-ui, sans-serif',
  },
  label: {
    color: '#555',
    fontSize: 10,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    marginBottom: 6,
  },
  cardsSection: {
    marginBottom: 10,
  },
  card: {
    width: '100%',
    textAlign: 'left',
    background: 'rgba(255,255,255,0.02)',
    border: '1px solid #2a2a3d',
    borderRadius: 8,
    padding: '8px 10px',
    cursor: 'pointer',
    transition: 'all 0.15s',
    fontFamily: 'system-ui, sans-serif',
  },
  cardTop: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  cardDest: {
    fontWeight: 600,
    fontSize: 13,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  cardMeta: {
    color: '#666',
    fontSize: 11,
    marginTop: 1,
  },
  cardWarning: {
    color: '#e74c3c',
    fontSize: 10,
    marginTop: 5,
    paddingTop: 5,
    borderTop: '1px solid rgba(231,76,60,0.2)',
  },
  modeTag: {
    fontSize: 10,
    fontWeight: 700,
    border: '1px solid',
    borderRadius: 10,
    padding: '1px 6px',
    whiteSpace: 'nowrap',
    letterSpacing: '0.05em',
    flexShrink: 0,
  },
  destRow: {
    display: 'flex',
    gap: 10,
    alignItems: 'center',
    padding: '8px 10px',
    background: 'rgba(46, 204, 113, 0.07)',
    borderRadius: 7,
    marginBottom: 10,
    border: '1px solid rgba(46, 204, 113, 0.2)',
  },
  destName: {
    fontWeight: 700,
    fontSize: 14,
    color: '#2ecc71',
  },
  destMeta: { color: '#888', fontSize: 11, marginTop: 2 },
  narrative: {
    background: 'rgba(255,255,255,0.03)',
    borderRadius: 6,
    padding: '8px 10px',
    marginBottom: 10,
    border: '1px solid #2a2a3d',
  },
  narrativeText: { margin: 0, color: '#bbb', lineHeight: 1.6, fontSize: 12 },
  shelter: {
    display: 'flex',
    gap: 8,
    alignItems: 'flex-start',
    padding: '7px 10px',
    background: 'rgba(255,255,255,0.02)',
    borderRadius: 6,
    marginBottom: 10,
    border: '1px solid #222',
  },
  shelterName: { fontWeight: 600, color: '#ddd', fontSize: 12 },
  shelterDist:  { color: '#666', fontSize: 11, marginTop: 1 },
  closeBtnBottom: {
    width: '100%',
    background: 'transparent',
    border: '1px solid #333',
    borderRadius: 6,
    color: '#555',
    fontSize: 11,
    fontWeight: 700,
    padding: '7px 0',
    cursor: 'pointer',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  },
}
