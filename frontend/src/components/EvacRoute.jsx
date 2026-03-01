import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * EvacRoute — Evacuation route overlay (v2 — real roads).
 *
 * Shows:
 * - Distance + destination name
 * - Gemini AI narrative
 * - Nearest shelter info
 */
export function EvacRoute({ active, routeData, loading, onClose }) {
  if (!active) return null

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>EVACUATION ROUTE</span>
        <button style={styles.closeBtn} onClick={onClose}>✕</button>
      </div>

      {loading ? (
        <div style={styles.loadingContainer}>
          <div style={styles.pulseRing} />
          <p style={styles.loadingText}>Finding safest route…</p>
        </div>
      ) : !routeData ? (
        <p style={styles.prompt}>Press EVACUATE then click the map — or drag your blue dot and press again</p>
      ) : (
        <>
          {/* Destination + distance */}
          <div style={styles.destRow}>
            <div style={styles.destIcon}>📍</div>
            <div>
              <div style={styles.destName}>
                {routeData.destination || 'Safe area'}
                {routeData.destination_country ? `, ${routeData.destination_country}` : ''}
              </div>
              <div style={styles.destMeta}>
                {routeData.distance_km} km
                {routeData.duration_min ? ` · ~${routeData.duration_min} min drive` : ''}
                {routeData.danger_hexes_on_route?.length > 0 && (
                  <span style={{ color: '#e74c3c', marginLeft: 8 }}>
                    ⚠ {routeData.danger_hexes_on_route.length} danger zone{routeData.danger_hexes_on_route.length > 1 ? 's' : ''} on route
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* AI narrative */}
          {routeData.narrative && (
            <div style={styles.narrative}>
              <p style={styles.narrativeText}>{routeData.narrative}</p>
            </div>
          )}

          {/* Nearest shelter */}
          {routeData.nearest_shelter && (
            <div style={styles.shelter}>
              <span style={styles.shelterIcon}>
                {routeData.nearest_shelter.type === 'hospital' ? '🏥' :
                 routeData.nearest_shelter.type === 'un_shelter' ? '🇺🇳' :
                 routeData.nearest_shelter.type === 'red_cross' ? '⛑️' :
                 routeData.nearest_shelter.type === 'evacuation_point' ? '✈️' : '📍'}
              </span>
              <div>
                <div style={styles.shelterName}>{routeData.nearest_shelter.name}</div>
                <div style={styles.shelterDist}>
                  {routeData.nearest_shelter.distance_km} km · {routeData.nearest_shelter.notes}
                </div>
              </div>
            </div>
          )}

          <button style={styles.closeBtnBottom} onClick={onClose}>
            CLOSE ROUTE
          </button>
        </>
      )}
    </div>
  )
}

/** Hook to manage evac route state */
export function useEvacRoute() {
  const [active, setActive]       = useState(false)
  const [routeData, setRouteData] = useState(null)
  const [loading, setLoading]     = useState(false)

  const activate = () => {
    setActive(true)
    setRouteData(null)
  }

  const deactivate = () => {
    setActive(false)
    setRouteData(null)
    setLoading(false)
  }

  const fetchRoute = async (lat, lng, backtestDate = null) => {
    setLoading(true)
    try {
      let url = `${API_URL}/evac-route?from_lat=${lat}&from_lng=${lng}`
      if (backtestDate) url += `&date=${backtestDate}`

      const res = await fetch(url)
      if (!res.ok) throw new Error(`API ${res.status}`)
      const data = await res.json()
      setRouteData(data)
    } catch (err) {
      console.error('Evac route failed:', err)
      setRouteData(null)
    } finally {
      setLoading(false)
    }
  }

  return { active, routeData, loading, activate, deactivate, fetchRoute }
}

const styles = {
  panel: {
    position: 'absolute',
    bottom: 24,
    right: 16,
    width: 320,
    background: 'rgba(12, 12, 22, 0.95)',
    border: '1px solid #2ecc71',
    borderRadius: 10,
    padding: '14px 16px',
    color: '#ddd',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 13,
    zIndex: 25,
    boxShadow: '0 4px 24px rgba(0,0,0,0.6), 0 0 20px rgba(46,204,113,0.1)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    fontWeight: 700,
    fontSize: 13,
    letterSpacing: '0.1em',
    color: '#2ecc71',
    textTransform: 'uppercase',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#888',
    fontSize: 16,
    cursor: 'pointer',
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '20px 0',
    gap: 12,
  },
  pulseRing: {
    width: 40,
    height: 40,
    border: '3px solid #2ecc71',
    borderRadius: '50%',
    opacity: 0.6,
    animation: 'pulse 1.5s ease-in-out infinite',
  },
  loadingText: {
    color: '#888',
    fontSize: 12,
    margin: 0,
  },
  prompt: {
    color: '#888',
    fontSize: 12,
    textAlign: 'center',
    padding: '16px 0',
    margin: 0,
    lineHeight: 1.5,
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: 8,
    marginBottom: 12,
  },
  stat: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '8px 4px',
    background: 'rgba(255,255,255,0.03)',
    borderRadius: 6,
  },
  statValue: {
    fontWeight: 700,
    fontSize: 17,
    color: '#eee',
  },
  statLabel: {
    fontSize: 9,
    color: '#666',
    marginTop: 2,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    textAlign: 'center',
  },
  destRow: {
    display: 'flex',
    gap: 10,
    alignItems: 'center',
    padding: '8px 10px',
    background: 'rgba(46, 204, 113, 0.08)',
    borderRadius: 6,
    marginBottom: 12,
    border: '1px solid rgba(46, 204, 113, 0.2)',
  },
  destIcon: {
    fontSize: 22,
  },
  destName: {
    fontWeight: 700,
    fontSize: 14,
    color: '#2ecc71',
  },
  destMeta: {
    color: '#aaa',
    fontSize: 12,
    marginTop: 2,
  },
  narrative: {
    background: 'rgba(46, 204, 113, 0.06)',
    border: '1px solid rgba(46, 204, 113, 0.2)',
    borderRadius: 6,
    padding: '10px 12px',
    marginBottom: 12,
  },
  narrativeText: {
    margin: 0,
    color: '#ccc',
    lineHeight: 1.6,
    fontSize: 12,
  },
  shelter: {
    display: 'flex',
    gap: 10,
    alignItems: 'flex-start',
    padding: '8px 10px',
    background: 'rgba(255,255,255,0.03)',
    borderRadius: 6,
    marginBottom: 12,
  },
  shelterIcon: {
    fontSize: 20,
    marginTop: 2,
  },
  shelterName: {
    fontWeight: 600,
    color: '#eee',
    fontSize: 13,
  },
  shelterDist: {
    color: '#888',
    fontSize: 11,
    marginTop: 2,
  },
  closeBtnBottom: {
    width: '100%',
    background: 'transparent',
    border: '1px solid #555',
    borderRadius: 6,
    color: '#aaa',
    fontSize: 11,
    fontWeight: 700,
    padding: '8px 0',
    cursor: 'pointer',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  },
}
