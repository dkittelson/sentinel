import { useMemo } from 'react'

/**
 * BacktestSlider — bottom-center time-travel control bar for demo mode.
 *
 * Features:
 *   - Date slider (range input)
 *   - Play / Pause button
 *   - Speed control (1x / 2x / 4x)
 *   - Current date + tier counts display
 *   - Preset jump buttons (Oct 7, Oct 17, Nov 23)
 */
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

      {/* Slider */}
      <input
        type="range"
        min={0}
        max={totalDays}
        value={currentDay}
        onChange={handleSlider}
        style={styles.slider}
      />

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
