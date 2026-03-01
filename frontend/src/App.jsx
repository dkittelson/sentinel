import { useEffect, useRef, useState, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

import { useHexData } from './hooks/useHexData'
import { useUserLocation } from './hooks/useUserLocation'
import { useAreaSummary } from './hooks/useAreaSummary'
import { useBacktest } from './hooks/useBacktest'
import { hexesToGeoJSON } from './utils/h3ToGeoJSON'
import { TIER_COLOR_EXPRESSION, TIER_OPACITY_EXPRESSION, STRATEGIC_COLOR_EXPRESSION, STRATEGIC_OPACITY_EXPRESSION } from './utils/tierColors'
import { HexSidebar } from './components/HexSidebar'
import { NewsSidebar } from './components/NewsSidebar'
import { LaunchPage } from './components/LaunchPage'
import { BacktestSlider } from './components/BacktestSlider'

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

  const { location } = useUserLocation()
  const { hexes: liveHexes, loading: hexLoading }     = useHexData()
  const { summary, loading: summaryLoading } = useAreaSummary(mapBounds)
  const backtest = useBacktest()

  // Use backtest hexes when active, otherwise live
  const hexes = backtest.active ? backtest.hexes : liveHexes
  const isLoading = backtest.active ? backtest.loading : hexLoading

  const updateBounds = useCallback(() => {
    if (!map.current) return
    setMapBounds(getMapBounds(map.current))
  }, [])

  // Init map immediately when user clicks ENTER (no waiting for GPS)
  useEffect(() => {
    if (!launched || map.current) return

    const BEIRUT = [35.5, 33.9]

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: BEIRUT,
      zoom: 3,
    })

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-left')

    map.current.on('load', () => {
      // Dramatic zoom-in — will update to user GPS once it resolves
      map.current.flyTo({
        center: BEIRUT,
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
  }, [launched])

  // Fly to real GPS once it resolves (after map is ready)
  useEffect(() => {
    if (!mapReady || !location) return
    map.current.flyTo({
      center: [location.lng, location.lat],
      zoom: 7.5,
      duration: 1800,
    })
  }, [mapReady, location])

  // Update hex layer on data refresh
  useEffect(() => {
    if (!mapReady || isLoading || !hexes.length) return
    const source = map.current.getSource(SOURCE_ID)
    if (!source) return
    source.setData(hexesToGeoJSON(hexes))
  }, [mapReady, hexes, isLoading])

  // Switch paint expressions based on backtest mode
  useEffect(() => {
    if (!mapReady || !map.current.getLayer(LAYER_ID)) return
    const colorExpr = backtest.active ? STRATEGIC_COLOR_EXPRESSION : TIER_COLOR_EXPRESSION
    const opacityExpr = backtest.active ? STRATEGIC_OPACITY_EXPRESSION : TIER_OPACITY_EXPRESSION
    map.current.setPaintProperty(LAYER_ID, 'fill-color', colorExpr)
    map.current.setPaintProperty(LAYER_ID, 'fill-opacity', opacityExpr)
  }, [mapReady, backtest.active])

  const dangerCount  = backtest.active
    ? hexes.filter(h => h.strategic_tier === 'red').length
    : hexes.filter(h => h.tactical_tier === 'DANGER').length
  const warningCount = backtest.active
    ? hexes.filter(h => h.strategic_tier === 'orange').length
    : hexes.filter(h => h.tactical_tier === 'WARNING').length

  return (
    <>
      {!launched && <LaunchPage onEnter={() => setLaunched(true)} />}

      <div style={{ width: '100vw', height: '100vh', position: 'relative', background: '#0a0a14' }}>
        <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

        {launched && (
          <>
            <div style={styles.statusBar}>
              <span style={styles.brand}>SENTINEL</span>
              {isLoading ? (
                <span style={styles.muted}>Connecting…</span>
              ) : (
                <>
                  {backtest.active && (
                    <span style={{ ...styles.badge, background: '#8e44ad' }}>
                      BACKTEST
                    </span>
                  )}
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
                  <span style={styles.muted}>
                    {hexes.length} hexes · {backtest.active ? backtest.currentDate : 'live'}
                  </span>
                  {!backtest.active && (
                    <button
                      onClick={() => backtest.enter()}
                      style={styles.backtestBtn}
                    >
                      ⏪ BACKTEST
                    </button>
                  )}
                </>
              )}
            </div>

            {!backtest.active && (
              <NewsSidebar summary={summary} loading={summaryLoading} hidden={!!selectedHex} />
            )}

            <HexSidebar
              h3Id={selectedHex}
              onClose={() => setSelectedHex(null)}
            />

            {backtest.active && (
              <BacktestSlider
                currentDate={backtest.currentDate}
                dateRange={backtest.dateRange}
                playing={backtest.playing}
                loading={backtest.loading}
                hexes={hexes}
                speed={backtest.speed}
                onPlay={backtest.play}
                onPause={backtest.pause}
                onGoToDate={backtest.goToDate}
                onSetSpeed={backtest.setSpeed}
                onExit={backtest.exit}
              />
            )}
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
  backtestBtn: {
    marginLeft: 8,
    background: 'transparent',
    border: '1px solid #8e44ad',
    borderRadius: 4,
    color: '#8e44ad',
    fontSize: 11,
    fontWeight: 700,
    padding: '3px 10px',
    cursor: 'pointer',
    letterSpacing: '0.05em',
  },
}
