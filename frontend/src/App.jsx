import { useEffect, useRef, useState, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

import { useHexData } from './hooks/useHexData'
import { useUserLocation } from './hooks/useUserLocation'
import { useAreaSummary } from './hooks/useAreaSummary'
import { useBacktest } from './hooks/useBacktest'
import { hexesToGeoJSON } from './utils/h3ToGeoJSON'
import { STRATEGIC_COLOR_EXPRESSION, STRATEGIC_OPACITY_EXPRESSION } from './utils/tierColors'
import { HexSidebar } from './components/HexSidebar'
import { NewsSidebar } from './components/NewsSidebar'
import { LaunchPage } from './components/LaunchPage'
import { BacktestSlider } from './components/BacktestSlider'
import { EvacRoute, useEvacRoute } from './components/EvacRoute'
import { useShelters, sheltersToGeoJSON, addShelterLayers, ShelterToggleButton } from './components/ShelterLayer'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN

const SOURCE_ID  = 'hex-source'
const LAYER_ID   = 'hex-fill'
const OUTLINE_ID = 'hex-outline'
const EVAC_SOURCE = 'evac-route-source'
const EVAC_LAYER  = 'evac-route-line'

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
  const shelterLayerIds = useRef(null)
  const userMarker   = useRef(null)
  const USER_DEFAULT = useRef([34.7818, 32.0853]) // Tel Aviv [lng, lat]
  const [launched, setLaunched]       = useState(false)
  const [mapReady, setMapReady]       = useState(false)
  const [selectedHex, setSelectedHex] = useState(null)
  const [mapBounds, setMapBounds]     = useState(null)

  const { location } = useUserLocation()
  const { hexes: liveHexes, loading: hexLoading }     = useHexData()
  const { summary, loading: summaryLoading } = useAreaSummary(mapBounds)
  const backtest = useBacktest()
  const evac = useEvacRoute()
  const shelters = useShelters()

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

    const USER_POS = USER_DEFAULT.current

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: USER_POS,
      zoom: 3,
    })

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-left')

    map.current.on('load', () => {
      // Dramatic zoom-in to user location on ENTER
      map.current.flyTo({
        center: USER_POS,
        zoom: 9,
        duration: 2800,
        easing: x => x < 0.5 ? 2 * x * x : -1 + (4 - 2 * x) * x,
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
          'fill-color':   STRATEGIC_COLOR_EXPRESSION,
          'fill-opacity': STRATEGIC_OPACITY_EXPRESSION,
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

      // Evacuation route layer
      map.current.addSource(EVAC_SOURCE, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.current.addLayer({
        id: EVAC_LAYER,
        type: 'line',
        source: EVAC_SOURCE,
        paint: {
          'line-color': '#2ecc71',
          'line-width': 4,
          'line-opacity': 0.85,
          'line-dasharray': [2, 1],
        },
        layout: { visibility: 'none' },
      })

      // Shelter layers (initially hidden)
      shelterLayerIds.current = addShelterLayers(map.current)

      // User location blue dot
      const el = document.createElement('div')
      el.style.cssText = 'width:18px;height:18px;border-radius:50%;background:#4A90D9;border:3px solid #fff;box-shadow:0 0 12px rgba(74,144,217,0.6);cursor:grab;'
      userMarker.current = new mapboxgl.Marker({ element: el, draggable: true })
        .setLngLat(USER_DEFAULT.current)
        .addTo(map.current)
      userMarker.current.on('dragend', () => {
        const lngLat = userMarker.current.getLngLat()
        USER_DEFAULT.current = [lngLat.lng, lngLat.lat]
      })

      map.current.on('click', LAYER_ID, e => {
        const props = e.features?.[0]?.properties
        if (props?.h3_id) setSelectedHex(props.h3_id)
      })

      // Map click: if evac mode, fetch route from clicked point
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

  // Update hex layer on data refresh
  useEffect(() => {
    if (!mapReady || isLoading || !hexes.length) return
    const source = map.current.getSource(SOURCE_ID)
    if (!source) return
    source.setData(hexesToGeoJSON(hexes))
  }, [mapReady, hexes, isLoading])

  // Draw evac route line when route data changes
  useEffect(() => {
    if (!mapReady) return
    const source = map.current.getSource(EVAC_SOURCE)
    if (!source) return

    if (evac.routeData?.route_points?.length > 1) {
      source.setData({
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'LineString',
            coordinates: evac.routeData.route_points,
          },
        }],
      })
      map.current.setLayoutProperty(EVAC_LAYER, 'visibility', 'visible')
    } else {
      source.setData({ type: 'FeatureCollection', features: [] })
      map.current.setLayoutProperty(EVAC_LAYER, 'visibility', 'none')
    }
  }, [mapReady, evac.routeData])

  // Toggle shelter layer visibility
  useEffect(() => {
    if (!mapReady || !shelterLayerIds.current) return
    const vis = shelters.visible ? 'visible' : 'none'
    const { CIRCLE_LAYER, LABEL_LAYER, SOURCE_ID: sSourceId } = shelterLayerIds.current
    map.current.setLayoutProperty(CIRCLE_LAYER, 'visibility', vis)
    map.current.setLayoutProperty(LABEL_LAYER, 'visibility', vis)

    // Update data if becoming visible and shelters are loaded
    if (shelters.visible && shelters.shelters.length > 0) {
      const source = map.current.getSource(sSourceId)
      if (source) source.setData(sheltersToGeoJSON(shelters.shelters))
    }
  }, [mapReady, shelters.visible, shelters.shelters])

  // Handle map click for evac mode — removed (now uses blue dot position directly)

  // Always color by strategic tier (ML model output) in both live and backtest mode
  const dangerCount  = hexes.filter(h => h.strategic_tier === 'red').length
  const warningCount = hexes.filter(h => h.strategic_tier === 'orange').length

  return (
    <>
      {!launched && <LaunchPage onEnter={() => setLaunched(true)} />}

      <div style={{ width: '100vw', height: '100vh', position: 'relative', background: '#0a0a14' }}>
        <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

        {launched && (
          <>
            {/* Status bar */}
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

            {/* Toolbar: bottom-left buttons */}
            <div style={styles.toolbar}>
              <ShelterToggleButton visible={shelters.visible} onToggle={shelters.toggle} />
              <button
                onClick={() => {
                  if (evac.active) {
                    evac.deactivate()
                  } else {
                    evac.activate()
                    // Route from user's blue dot position
                    const pos = USER_DEFAULT.current // [lng, lat]
                    const backtestDate = backtest.active ? backtest.currentDate : null
                    evac.fetchRoute(pos[1], pos[0], backtestDate)
                  }
                }}
                style={{
                  ...styles.evacBtn,
                  borderColor: evac.active ? '#2ecc71' : '#444',
                  color: evac.active ? '#2ecc71' : '#aaa',
                  background: evac.active ? 'rgba(46,204,113,0.1)' : 'transparent',
                }}
              >
                {evac.loading ? '⏳ ROUTING...' : evac.active ? '✕ CLOSE' : '🚨 EVACUATE'}
              </button>
            </div>

            {/* News sidebar (live mode only) */}
            {!backtest.active && (
              <NewsSidebar summary={summary} loading={summaryLoading} hidden={!!selectedHex || evac.active} />
            )}

            {/* Hex detail sidebar */}
            <HexSidebar
              h3Id={selectedHex}
              onClose={() => setSelectedHex(null)}
              backtestDate={backtest.active ? backtest.currentDate : null}
            />

            {/* Evac route panel */}
            <EvacRoute
              active={evac.active}
              routeData={evac.routeData}
              loading={evac.loading}
              onClose={evac.deactivate}
            />

            {/* Backtest slider */}
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
  toolbar: {
    position: 'absolute',
    bottom: 24,
    left: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    zIndex: 15,
  },
  evacBtn: {
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
  },
}
