import { useMemo, useState } from 'react'

/**
 * BacktestSlider — bottom-center time-travel control bar for demo mode.
 *
 * Features:
 *   - Date slider (range input) with event annotation markers
 *   - Play / Pause button
 *   - Speed control (1x / 2x / 4x)
 *   - Current date + tier counts display
 *   - Preset jump buttons (Oct 7, Oct 17, Nov 23)
 *   - Key historical event annotations on the timeline
 */

// Key historical events for annotation markers
const TIMELINE_EVENTS = [
  { date: '2023-10-07', label: 'Hamas attack on Israel',      color: '#e74c3c', major: true },
  { date: '2023-10-17', label: 'Al-Ahli hospital blast',      color: '#e67e22', major: false },
  { date: '2023-10-27', label: 'IDF ground incursion',         color: '#e74c3c', major: false },
  { date: '2023-11-24', label: 'Israel-Hamas truce begins',    color: '#2ecc71', major: true },
  { date: '2024-01-02', label: 'Al-Arouri assassinated',       color: '#e74c3c', major: false },
  { date: '2024-04-01', label: 'Strike on Iran consulate',     color: '#e67e22', major: false },
  { date: '2024-04-13', label: 'Iran retaliatory attack',      color: '#e74c3c', major: false },
  { date: '2024-09-17', label: 'Lebanon pager attacks',        color: '#e74c3c', major: true },
  { date: '2024-10-01', label: 'Israel invades Lebanon',       color: '#e74c3c', major: true },
  { date: '2024-11-27', label: 'Israel-Lebanon ceasefire',     color: '#2ecc71', major: true },
]

export function BacktestSlider({
  currentDate,
  dateRange,
  playing,
  loading,
  hexes,
  speed,
  onPlay,
  onPause,
  onGoToDate,
  onSetSpeed,
  onExit,
}) {
  if (!dateRange || !currentDate) return null

  const minDate = new Date(dateRange.min_date)
  const maxDate = new Date(dateRange.max_date)
  const curDate = new Date(currentDate)

  const totalDays = Math.round((maxDate - minDate) / 86400000)
  const currentDay = Math.round((curDate - minDate) / 86400000)

  // Tier counts (strategic tiers in backtest mode)
  const counts = useMemo(() => {
    const c = { red: 0, orange: 0, yellow: 0, green: 0 }
    hexes.forEach(h => { c[h.strategic_tier] = (c[h.strategic_tier] || 0) + 1 })
    return c
  }, [hexes])

  const formatDate = (d) => {
    const date = new Date(d)
    return date.toLocaleDateString('en-US', { 
      month: 'short', day: 'numeric', year: 'numeric' 
    })
  }

  const handleSlider = (e) => {
    const day = parseInt(e.target.value)
    const d = new Date(minDate)
    d.setDate(d.getDate() + day)
    onGoToDate(d.toISOString().slice(0, 10))
  }

  const jumpTo = (dateStr) => onGoToDate(dateStr)

  const speedLabel = speed <= 250 ? '4x' : speed <= 500 ? '2x' : '1x'

  const cycleSpeed = () => {
    if (speed >= 1000) onSetSpeed(500)
    else if (speed >= 500) onSetSpeed(250)
    else onSetSpeed(1000)
  }

  // Compute event marker positions
  const eventMarkers = useMemo(() => {
    return TIMELINE_EVENTS.map(evt => {
      const evtDate = new Date(evt.date)
      const day = Math.round((evtDate - minDate) / 86400000)
      const pct = totalDays > 0 ? (day / totalDays) * 100 : 0
      if (pct < 0 || pct > 100) return null
      return { ...evt, pct, day }
    }).filter(Boolean)
  }, [minDate, totalDays])

  const [hoveredEvent, setHoveredEvent] = useState(null)

  return (
    <div style={styles.container}>
      {/* Top row: date + counts */}
      <div style={styles.topRow}>
        <span style={styles.dateLabel}>{formatDate(currentDate)}</span>
        <div style={styles.counts}>
          {counts.red > 0 && (
            <span style={{ ...styles.badge, background: '#e74c3c' }}>
              {counts.red} RED
            </span>
          )}
          {counts.orange > 0 && (
            <span style={{ ...styles.badge, background: '#f09438' }}>
              {counts.orange} ORANGE
            </span>
          )}
          {counts.yellow > 0 && (
            <span style={{ ...styles.badge, background: '#f6d860', color: '#111' }}>
              {counts.yellow} YELLOW
            </span>
          )}
          <span style={styles.muted}>{hexes.length} hexes</span>
        </div>
        {loading && <span style={styles.spinner}>⟳</span>}
      </div>

      {/* Slider with event annotations */}
      <div style={styles.sliderContainer}>
        <input
          type="range"
          min={0}
          max={totalDays}
          value={currentDay}
          onChange={handleSlider}
          style={styles.slider}
        />

        {/* Event markers */}
        {eventMarkers.map((evt, i) => (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${evt.pct}%`,
              top: evt.major ? -6 : -3,
              width: evt.major ? 3 : 2,
              height: evt.major ? 18 : 12,
              background: evt.color,
              borderRadius: 1,
              cursor: 'pointer',
              opacity: evt.major ? 0.9 : 0.6,
              zIndex: 2,
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={() => setHoveredEvent(evt)}
            onMouseLeave={() => setHoveredEvent(null)}
            onClick={() => jumpTo(evt.date)}
          />
        ))}

        {/* Tooltip for hovered event */}
        {hoveredEvent && (
          <div style={{
            position: 'absolute',
            left: `${hoveredEvent.pct}%`,
            bottom: 28,
            transform: 'translateX(-50%)',
            background: 'rgba(10,10,20,0.95)',
            border: `1px solid ${hoveredEvent.color}`,
            borderRadius: 6,
            padding: '5px 10px',
            whiteSpace: 'nowrap',
            fontSize: 11,
            color: '#eee',
            zIndex: 30,
            pointerEvents: 'none',
          }}>
            <span style={{ color: hoveredEvent.color, fontWeight: 700 }}>
              {formatDate(hoveredEvent.date)}
            </span>
            {' — '}
            {hoveredEvent.label}
          </div>
        )}
      </div>

      {/* Bottom row: controls */}
      <div style={styles.controls}>
        <button onClick={playing ? onPause : onPlay} style={styles.btn}>
          {playing ? '⏸' : '▶'}
        </button>
        <button onClick={cycleSpeed} style={styles.btnSmall} title="Playback speed">
          {speedLabel}
        </button>

        <div style={styles.presets}>
          <button onClick={() => jumpTo('2023-10-01')} style={styles.preset}>
            Oct 1
          </button>
          <button onClick={() => jumpTo('2023-10-07')} style={styles.preset}>
            Oct 7 ⚡
          </button>
          <button onClick={() => jumpTo('2023-10-17')} style={styles.preset}>
            Oct 17
          </button>
          <button onClick={() => jumpTo('2023-11-24')} style={styles.preset}>
            Nov 24
          </button>
          <button onClick={() => jumpTo('2024-10-01')} style={styles.preset}>
            Oct '24
          </button>
        </div>

        <button onClick={onExit} style={styles.exitBtn}>
          EXIT BACKTEST
        </button>
      </div>
    </div>
  )
}

const styles = {
  container: {
    position: 'absolute',
    bottom: 24,
    left: '50%',
    transform: 'translateX(-50%)',
    width: 'min(700px, 90vw)',
    background: 'rgba(10, 10, 20, 0.92)',
    border: '1px solid #2a2a3d',
    borderRadius: 12,
    padding: '12px 20px',
    fontFamily: 'system-ui, sans-serif',
    color: '#ddd',
    backdropFilter: 'blur(8px)',
    zIndex: 20,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  topRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  dateLabel: {
    fontWeight: 700,
    fontSize: 16,
    color: '#fff',
    letterSpacing: '0.02em',
    minWidth: 140,
  },
  counts: {
    display: 'flex',
    gap: 8,
    alignItems: 'center',
    flex: 1,
  },
  badge: {
    padding: '2px 8px',
    borderRadius: 4,
    color: '#fff',
    fontWeight: 700,
    fontSize: 11,
  },
  muted: {
    color: '#666',
    fontSize: 12,
  },
  spinner: {
    animation: 'spin 1s linear infinite',
    fontSize: 16,
    color: '#888',
  },
  sliderContainer: {
    position: 'relative',
    width: '100%',
    height: 20,
    display: 'flex',
    alignItems: 'center',
  },
  slider: {
    width: '100%',
    height: 6,
    cursor: 'pointer',
    accentColor: '#e74c3c',
  },
  controls: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  btn: {
    background: '#e74c3c',
    border: 'none',
    borderRadius: 6,
    color: '#fff',
    fontSize: 18,
    width: 40,
    height: 32,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnSmall: {
    background: '#333',
    border: '1px solid #555',
    borderRadius: 4,
    color: '#ccc',
    fontSize: 11,
    fontWeight: 700,
    padding: '4px 8px',
    cursor: 'pointer',
  },
  presets: {
    display: 'flex',
    gap: 4,
    marginLeft: 8,
  },
  preset: {
    background: 'transparent',
    border: '1px solid #444',
    borderRadius: 4,
    color: '#aaa',
    fontSize: 11,
    padding: '3px 8px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  exitBtn: {
    marginLeft: 'auto',
    background: 'transparent',
    border: '1px solid #e74c3c',
    borderRadius: 4,
    color: '#e74c3c',
    fontSize: 11,
    fontWeight: 700,
    padding: '4px 10px',
    cursor: 'pointer',
    letterSpacing: '0.05em',
  },
}
