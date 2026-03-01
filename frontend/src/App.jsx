import { useEffect, useRef, useState, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

import { useHexData } from './hooks/useHexData'
import { useUserLocation } from './hooks/useUserLocation'
import { useAreaSummary } from './hooks/useAreaSummary'
import { hexesToGeoJSON } from './utils/h3ToGeoJSON'
import { TIER_COLOR_EXPRESSION, TIER_OPACITY_EXPRESSION } from './utils/tierColors'
import { HexSidebar } from './components/HexSidebar'
import { NewsSidebar } from './components/NewsSidebar'
import { LaunchPage } from './components/LaunchPage'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN

const SOURCE_ID  = 'hex-source'
const LAYER_ID   = 'hex-fill'
const OUTLINE_ID = 'hex-outline'

function getMapBounds(map) {
  const bounds = map.getBounds()
  const ne = bounds.getNorthEast()
  const sw = bounds.getSouthWest()
  const centerLat = (ne.lat + sw.lat) / 2
  const centerLon = (ne.lng + sw.lng) / 2
  const latDiff = Math.abs(ne.lat - sw.lat)
  const lonDiff = Math.abs(ne.lng - sw.lng)
  const radiusKm = Math.round(Math.max(latDiff, lonDiff) * 55)
  return { centerLat, centerLon, radiusKm }
}

export default function App() {
  const mapContainer = useRef(null)
  const map          = useRef(null)
  const [launched, setLaunched]       = useState(false)
  const [mapReady, setMapReady]       = useState(false)
  const [selectedHex, setSelectedHex] = useState(null)
  const [mapBounds, setMapBounds]     = useState(null)

  const { location, ready: locationReady } = useUserLocation()
  const { hexes, loading: hexLoading }     = useHexData()
  const { summary, loading: summaryLoading } = useAreaSummary(mapBounds)

  const updateBounds = useCallback(() => {
    if (!map.current) return
    setMapBounds(getMapBounds(map.current))
  }, [])

  // Init map after launch page dismisses
  useEffect(() => {
    if (!launched || !locationReady || map.current) return

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [location.lng, location.lat],
      zoom: 3,
    })

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-left')

    map.current.on('load', () => {
      // Dramatic zoom-in to user location
      map.current.flyTo({
        center: [location.lng, location.lat],
        zoom: 7.5,
        duration: 2800,
        easing: t => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
      })

      map.current.addSource(SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })

      map.current.addLayer({
        id: LAYER_ID,
        type: 'fill',
        source: SOURCE_ID,
        paint: {
          'fill-color':   TIER_COLOR_EXPRESSION,
          'fill-opacity': TIER_OPACITY_EXPRESSION,
        },
      })

      map.current.addLayer({
        id: OUTLINE_ID,
        type: 'line',
        source: SOURCE_ID,
        paint: {
          'line-color':   '#ffffff',
          'line-opacity': 0.08,
          'line-width':   0.5,
        },
      })

      map.current.on('click', LAYER_ID, e => {
        const props = e.features?.[0]?.properties
        if (props?.h3_id) setSelectedHex(props.h3_id)
      })

      map.current.on('click', e => {
        const features = map.current.queryRenderedFeatures(e.point, { layers: [LAYER_ID] })
        if (!features.length) setSelectedHex(null)
      })

      map.current.on('mouseenter', LAYER_ID, () => {
        map.current.getCanvas().style.cursor = 'pointer'
      })
      map.current.on('mouseleave', LAYER_ID, () => {
        map.current.getCanvas().style.cursor = ''
      })

      map.current.on('moveend', updateBounds)
      map.current.on('zoomend', updateBounds)

      setMapReady(true)
      updateBounds()
    })
  }, [launched, locationReady])

  // Update hex layer on data refresh
  useEffect(() => {
    if (!mapReady || hexLoading || !hexes.length) return
    const source = map.current.getSource(SOURCE_ID)
    if (!source) return
    source.setData(hexesToGeoJSON(hexes))
  }, [mapReady, hexes, hexLoading])

  const dangerCount  = hexes.filter(h => h.tactical_tier === 'DANGER').length
  const warningCount = hexes.filter(h => h.tactical_tier === 'WARNING').length

  return (
    <>
      {!launched && <LaunchPage onEnter={() => setLaunched(true)} />}

      <div style={{ width: '100vw', height: '100vh', position: 'relative', background: '#0a0a14' }}>
        <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

        {launched && (
          <>
            <div style={styles.statusBar}>
              <span style={styles.brand}>SENTINEL</span>
              {hexLoading ? (
                <span style={styles.muted}>Connecting…</span>
              ) : (
                <>
                  {dangerCount > 0 && (
                    <span style={{ ...styles.badge, background: '#e74c3c' }}>
                      {dangerCount} DANGER
                    </span>
                  )}
                  {warningCount > 0 && (
                    <span style={{ ...styles.badge, background: '#f09438' }}>
                      {warningCount} WARNING
                    </span>
                  )}
                  <span style={styles.muted}>{hexes.length} hexes · live</span>
                </>
              )}
            </div>

            <NewsSidebar summary={summary} loading={summaryLoading} hidden={!!selectedHex} />

            <HexSidebar
              h3Id={selectedHex}
              onClose={() => setSelectedHex(null)}
            />
          </>
        )}
      </div>
    </>
  )
}

const styles = {
  statusBar: {
    position: 'absolute',
    top: 16,
    left: '50%',
    transform: 'translateX(-50%)',
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    background: 'rgba(10, 10, 20, 0.85)',
    border: '1px solid #2a2a3d',
    borderRadius: 8,
    padding: '8px 16px',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 13,
    color: '#ddd',
    backdropFilter: 'blur(6px)',
    zIndex: 10,
    whiteSpace: 'nowrap',
  },
  brand: {
    fontWeight: 700,
    letterSpacing: '0.12em',
    color: '#e74c3c',
    fontSize: 14,
  },
  badge: {
    padding: '2px 8px',
    borderRadius: 4,
    color: '#fff',
    fontWeight: 700,
    fontSize: 12,
  },
  muted: {
    color: '#666',
  },
}
