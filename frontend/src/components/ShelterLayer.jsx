import { useState, useEffect, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Map shelter types to Mapbox marker colors and emojis
const TYPE_CONFIG = {
  hospital:        { color: '#e74c3c', emoji: '🏥', mapColor: '#ff4444' },
  un_shelter:      { color: '#3498db', emoji: '🇺🇳', mapColor: '#4488ff' },
  red_cross:       { color: '#e74c3c', emoji: '⛑️', mapColor: '#ff6666' },
  evacuation_point:{ color: '#f39c12', emoji: '✈️', mapColor: '#ffaa33' },
  border_crossing: { color: '#9b59b6', emoji: '🛂', mapColor: '#aa66cc' },
}

/**
 * Hook to manage shelter layer state + data fetching.
 * Returns shelter data + visibility toggle.
 */
export function useShelters() {
  const [shelters, setShelters] = useState([])
  const [visible, setVisible]  = useState(false)
  const [loaded, setLoaded]    = useState(false)

  const loadShelters = useCallback(async () => {
    if (loaded) return
    try {
      const res = await fetch(`${API_URL}/shelters`)
      if (!res.ok) throw new Error(`API ${res.status}`)
      const data = await res.json()
      setShelters(data.shelters || [])
      setLoaded(true)
    } catch (err) {
      console.error('Failed to load shelters:', err)
    }
  }, [loaded])

  const toggle = useCallback(() => {
    if (!loaded) loadShelters()
    setVisible(v => !v)
  }, [loaded, loadShelters])

  return { shelters, visible, toggle, loadShelters }
}

/**
 * Convert shelter data to GeoJSON for Mapbox.
 */
export function sheltersToGeoJSON(shelters) {
  return {
    type: 'FeatureCollection',
    features: shelters.map(s => ({
      type: 'Feature',
      properties: {
        name: s.name,
        type: s.type,
        capacity: s.capacity,
        notes: s.notes,
        emoji: TYPE_CONFIG[s.type]?.emoji || '📍',
        color: TYPE_CONFIG[s.type]?.mapColor || '#ffffff',
      },
      geometry: {
        type: 'Point',
        coordinates: [s.lng, s.lat],
      },
    })),
  }
}

/**
 * Add shelter layers to a Mapbox map instance.
 * Uses hospital cross icon rendered via SDF for crisp display.
 * Call once after map loads; control visibility via setLayoutProperty.
 */
export function addShelterLayers(map) {
  const SOURCE_ID = 'shelter-source'
  const ICON_LAYER = 'shelter-icons'
  const LABEL_LAYER = 'shelter-labels'

  // Source
  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    })
  }

  // Load custom hospital cross icon (rendered as canvas → image)
  if (!map.hasImage('hospital-cross')) {
    const size = 40
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const ctx = canvas.getContext('2d')

    // White circle background
    ctx.beginPath()
    ctx.arc(size / 2, size / 2, size / 2 - 1, 0, Math.PI * 2)
    ctx.fillStyle = '#ffffff'
    ctx.fill()
    ctx.strokeStyle = '#cc3333'
    ctx.lineWidth = 2
    ctx.stroke()

    // Red cross
    const cx = size / 2, cy = size / 2
    const arm = 6, half = 3
    ctx.fillStyle = '#cc3333'
    ctx.fillRect(cx - half, cy - arm, half * 2, arm * 2) // vertical
    ctx.fillRect(cx - arm, cy - half, arm * 2, half * 2) // horizontal

    map.addImage('hospital-cross', { width: size, height: size, data: ctx.getImageData(0, 0, size, size).data })
  }

  // Icon layer (hospital cross markers)
  if (!map.getLayer(ICON_LAYER)) {
    map.addLayer({
      id: ICON_LAYER,
      type: 'symbol',
      source: SOURCE_ID,
      layout: {
        'icon-image': 'hospital-cross',
        'icon-size': [
          'interpolate', ['linear'], ['zoom'],
          5, 0.4,
          8, 0.6,
          12, 0.8,
        ],
        'icon-allow-overlap': true,
        'icon-ignore-placement': false,
        visibility: 'none',
      },
    })
  }

  // Label layer
  if (!map.getLayer(LABEL_LAYER)) {
    map.addLayer({
      id: LABEL_LAYER,
      type: 'symbol',
      source: SOURCE_ID,
      layout: {
        'text-field': ['get', 'name'],
        'text-size': 11,
        'text-offset': [0, 1.5],
        'text-anchor': 'top',
        'text-optional': true,
        visibility: 'none',
      },
      paint: {
        'text-color': '#ddd',
        'text-halo-color': '#000',
        'text-halo-width': 1,
      },
      minzoom: 8,
    })
  }

  return { SOURCE_ID, CIRCLE_LAYER: ICON_LAYER, LABEL_LAYER }
}

/**
 * ShelterToggleButton — small button to show/hide shelter pins.
 */
export function ShelterToggleButton({ visible, onToggle }) {
  return (
    <button
      onClick={onToggle}
      style={{
        ...btnStyle,
        borderColor: visible ? '#2ecc71' : '#444',
        color: visible ? '#2ecc71' : '#aaa',
        background: visible ? 'rgba(46,204,113,0.1)' : 'transparent',
      }}
    >
      🏥 Shelters
    </button>
  )
}

const btnStyle = {
  background: 'transparent',
  border: '1px solid #444',
  borderRadius: 4,
  padding: '3px 10px',
  fontSize: 11,
  fontWeight: 700,
  cursor: 'pointer',
  letterSpacing: '0.04em',
  fontFamily: 'system-ui, sans-serif',
  transition: 'all 0.15s',
}
