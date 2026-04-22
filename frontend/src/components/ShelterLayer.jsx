import { useState, useEffect, useCallback } from 'react'
import localShelters from '../data/shelters.json'

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
    } catch {
      // Backend unavailable — use bundled static data
      setShelters(localShelters.shelters || [])
    } finally {
      setLoaded(true)
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
 * Uses type-aware colored circles + emoji labels — no canvas sprites needed.
 * Call once after map loads; control visibility via setLayoutProperty.
 */
export function addShelterLayers(map) {
  const SOURCE_ID   = 'shelter-source'
  const CIRCLE_LAYER = 'shelter-circles'
  const EMOJI_LAYER  = 'shelter-emoji'
  const LABEL_LAYER  = 'shelter-labels'

  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    })
  }

  // Colored circle per shelter type (driven by the 'color' property from sheltersToGeoJSON)
  if (!map.getLayer(CIRCLE_LAYER)) {
    map.addLayer({
      id: CIRCLE_LAYER,
      type: 'circle',
      source: SOURCE_ID,
      paint: {
        'circle-color': ['get', 'color'],
        'circle-radius': [
          'interpolate', ['linear'], ['zoom'],
          5, 4,
          9, 7,
          12, 10,
        ],
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 1.5,
        'circle-opacity': 0.9,
      },
      layout: { visibility: 'none' },
    })
  }

  // Emoji label centered on the circle (visible at zoom ≥ 7)
  if (!map.getLayer(EMOJI_LAYER)) {
    map.addLayer({
      id: EMOJI_LAYER,
      type: 'symbol',
      source: SOURCE_ID,
      layout: {
        'text-field': ['get', 'emoji'],
        'text-size': 13,
        'text-allow-overlap': true,
        'text-ignore-placement': true,
        visibility: 'none',
      },
      paint: { 'text-color': '#ffffff' },
      minzoom: 7,
    })
  }

  // Name label below the circle (visible only when zoomed in)
  if (!map.getLayer(LABEL_LAYER)) {
    map.addLayer({
      id: LABEL_LAYER,
      type: 'symbol',
      source: SOURCE_ID,
      layout: {
        'text-field': ['get', 'name'],
        'text-size': 11,
        'text-offset': [0, 1.6],
        'text-anchor': 'top',
        'text-optional': true,
        visibility: 'none',
      },
      paint: {
        'text-color': '#ddd',
        'text-halo-color': '#000',
        'text-halo-width': 1,
      },
      minzoom: 9,
    })
  }

  return { SOURCE_ID, CIRCLE_LAYER, LABEL_LAYER, EMOJI_LAYER }
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
