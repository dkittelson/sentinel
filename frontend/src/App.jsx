import { useEffect, useRef, useState, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { latLngToCell } from 'h3-js'

import { useHexData } from './hooks/useHexData'
import { useUserLocation } from './hooks/useUserLocation'
import { useBacktest } from './hooks/useBacktest'
import { hexesToGeoJSON } from './utils/h3ToGeoJSON'
import { STRATEGIC_COLOR_EXPRESSION, STRATEGIC_OPACITY_EXPRESSION } from './utils/tierColors'
import { HexSidebar } from './components/HexSidebar'
import { LaunchPage } from './components/LaunchPage'
import { BacktestSlider } from './components/BacktestSlider'
import { EvacRoute, useEvacRoute } from './components/EvacRoute'
import { useShelters, sheltersToGeoJSON, addShelterLayers } from './components/ShelterLayer'
import { LangToggle, useLang } from './components/LangToggle'
import { isRTL, t } from './i18n'
import { Onboarding, hasOnboarded } from './components/Onboarding'

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
  const [menuOpen, setMenuOpen]       = useState(false)
  const [selectedRoute, setSelectedRoute] = useState(null)
  const [showOnboarding, setShowOnboarding] = useState(false)

  const lang = useLang()  // subscribe to language changes for re-render + RTL

  const prevTierRef = useRef(null)
  const TIER_ORDER = { green: 0, yellow: 1, orange: 2, red: 3 }

  const { location } = useUserLocation()
  const { hexes: liveHexes, loading: hexLoading, lastFetchedAt, timedOut } = useHexData()
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

  // Request notification permission + show onboarding on first launch
  useEffect(() => {
    if (!launched) return
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
    if (!hasOnboarded()) {
      setShowOnboarding(true)
    }
  }, [launched])

  // Reset selected route when evac route data refreshes
  useEffect(() => {
    setSelectedRoute(null)
  }, [evac.routeData])

  // Escalation detection: fire browser notification + haptic when user's hex tier rises
  useEffect(() => {
    if (!hexes.length) return
    const [lng, lat] = USER_DEFAULT.current
    const userH3 = latLngToCell(lat, lng, 6)
    const userHex = hexes.find(h => h.h3_id === userH3)
    if (!userHex) return

    const tier = userHex.strategic_tier || 'green'
    const prev = prevTierRef.current

    if (prev !== null && (TIER_ORDER[tier] ?? 0) > (TIER_ORDER[prev] ?? 0)) {
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('⚠ Sentinel Alert', {
          body: `Risk in your area escalated to ${tier.toUpperCase()}`,
          icon: '/favicon.ico',
        })
      }
      if ('vibrate' in navigator) {
        navigator.vibrate([200, 100, 200])
      }
    }

    prevTierRef.current = tier
  }, [hexes])

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

  // Draw evac route line — uses selected alternate route's points if chosen, else best route
  useEffect(() => {
    if (!mapReady) return
    const source = map.current.getSource(EVAC_SOURCE)
    if (!source) return

    const points = selectedRoute?.route_points ?? evac.routeData?.route_points
    const modeColor = { driving: '#2ecc71', walking: '#3498db', cycling: '#9b59b6' }
    const lineColor = modeColor[selectedRoute?.mode] ?? '#2ecc71'

    if (points?.length > 1) {
      source.setData({
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          properties: {},
          geometry: { type: 'LineString', coordinates: points },
        }],
      })
      map.current.setPaintProperty(EVAC_LAYER, 'line-color', lineColor)
      map.current.setLayoutProperty(EVAC_LAYER, 'visibility', 'visible')
    } else {
      source.setData({ type: 'FeatureCollection', features: [] })
      map.current.setLayoutProperty(EVAC_LAYER, 'visibility', 'none')
    }
  }, [mapReady, evac.routeData, selectedRoute])

  // Toggle shelter layer visibility
  useEffect(() => {
    if (!mapReady || !shelterLayerIds.current) return
    const vis = shelters.visible ? 'visible' : 'none'
    const { CIRCLE_LAYER, LABEL_LAYER, EMOJI_LAYER, SOURCE_ID: sSourceId } = shelterLayerIds.current
    map.current.setLayoutProperty(CIRCLE_LAYER, 'visibility', vis)
    map.current.setLayoutProperty(LABEL_LAYER, 'visibility', vis)
    if (EMOJI_LAYER) map.current.setLayoutProperty(EMOJI_LAYER, 'visibility', vis)

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

      <div style={{ width: '100vw', height: '100vh', position: 'relative', background: '#0a0a14' }} dir={isRTL() ? 'rtl' : 'ltr'}>
        <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

        {launched && (
          <>
            {/* Status bar — always LTR; lang toggle pinned to far right */}
            <div style={{ ...styles.statusBar, direction: 'ltr' }}>
              <svg width="22" height="22" viewBox="0 0 52 52" fill="none" style={{ flexShrink: 0 }} aria-hidden="true">
                <polygon points="26,2 50,14 50,38 26,50 2,38 2,14" stroke="#ffffff" strokeWidth="2" fill="none" />
                <polygon points="26,10 42,18 42,34 26,42 10,34 10,18" stroke="#ffffff" strokeWidth="1.2" fill="rgba(255,255,255,0.06)" />
                <circle cx="26" cy="26" r="4" fill="#ffffff" />
              </svg>

              {isLoading && hexes.length === 0 && !timedOut ? (
                <span style={styles.muted}>{t('connecting')}</span>
              ) : timedOut && hexes.length === 0 ? (
                <span style={{ ...styles.muted, color: '#f09438' }}>{t('liveDelayed')}</span>
              ) : (
                <>
                  {backtest.active && (
                    <span style={{ ...styles.badge, background: '#8e44ad' }}>{t('backtest')}</span>
                  )}
                  {dangerCount > 0 && (
                    <span style={{ ...styles.badge, background: '#e74c3c' }}>{dangerCount} {t('danger')}</span>
                  )}
                  {warningCount > 0 && (
                    <span style={{ ...styles.badge, background: '#f09438' }}>{warningCount} {t('warning')}</span>
                  )}
                  {!backtest.active && dangerCount === 0 && warningCount === 0 && hexes.length > 0 && (
                    <span style={{ ...styles.badge, background: '#1a7a3a' }}>{t('allClear')}</span>
                  )}
                  <span style={styles.liveDot} aria-hidden="true">●</span>
                  <span style={styles.liveText}>
                    {backtest.active
                      ? backtest.currentDate
                      : lastFetchedAt
                        ? lastFetchedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : t('live')}
                  </span>
                  <span style={styles.legendSep} aria-hidden="true">│</span>
                  <span style={styles.legendItem}>
                    <span style={{ ...styles.legendSwatch, background: '#800026' }} aria-hidden="true" />{t('high')}
                  </span>
                  <span style={styles.legendItem}>
                    <span style={{ ...styles.legendSwatch, background: '#fd8d3c' }} aria-hidden="true" />{t('moderate')}
                  </span>
                  <span style={styles.legendItem}>
                    <span style={{ ...styles.legendSwatch, background: '#ffffb2' }} aria-hidden="true" />{t('low')}
                  </span>
                </>
              )}
              <span style={{ marginLeft: 'auto' }}><LangToggle /></span>
            </div>

            {/* Menu button */}
            <div style={styles.menuContainer}>
              {menuOpen && (
                <div style={styles.menuPopup}>
                  <button
                    onClick={() => {
                      if (backtest.active) {
                        backtest.exit()
                      } else {
                        backtest.enter('2023-10-01')
                      }
                      setMenuOpen(false)
                    }}
                    style={{
                      ...styles.menuItem,
                      color: backtest.active ? '#8e44ad' : '#ccc',
                    }}
                  >
                    <svg style={styles.menuSvg} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="10" cy="10" r="7"/>
                      <polyline points="10 6 10 10 13 12"/>
                      <polyline points="3 6 6 6 6 3"/>
                    </svg>
                    {backtest.active ? t('exitBacktestMode') : t('backtestMode')}
                  </button>
                  <button
                    onClick={() => {
                      shelters.toggle()
                      setMenuOpen(false)
                    }}
                    style={{
                      ...styles.menuItem,
                      color: shelters.visible ? '#2ecc71' : '#ccc',
                    }}
                  >
                    <svg style={styles.menuSvg} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M10 2L2 7v11h16V7L10 2z"/><rect x="7" y="11" width="6" height="7"/></svg>
                    {shelters.visible ? t('hideSafeLocations') : t('showSafeLocations')}
                  </button>
                  <button
                    onClick={() => {
                      if (evac.active) {
                        evac.deactivate()
                      } else {
                        evac.activate()
                        const pos = USER_DEFAULT.current
                        const backtestDate = backtest.active ? backtest.currentDate : null
                        evac.fetchRoute(pos[1], pos[0], backtestDate)
                      }
                      setMenuOpen(false)
                    }}
                    style={{
                      ...styles.menuItem,
                      color: evac.active ? '#2ecc71' : '#ccc',
                    }}
                  >
                    <svg style={styles.menuSvg} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 10h4l2-6 3 12 2-6h3"/></svg>
                    {evac.loading ? t('routing') : evac.active ? t('closeEvacRoute') : t('showEvacRoute')}
                  </button>
                </div>
              )}
              <button
                onClick={() => setMenuOpen(m => !m)}
                aria-label={menuOpen ? 'Close menu' : 'Open menu'}
                aria-expanded={menuOpen}
                style={{
                  ...styles.menuBtn,
                  borderColor: menuOpen ? '#e74c3c' : '#555',
                  background: menuOpen ? 'rgba(231,76,60,0.15)' : 'rgba(10,10,20,0.85)',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' }} aria-hidden="true">
                  {menuOpen ? (
                    <svg width="16" height="16" viewBox="0 0 20 20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" fill="none"><line x1="5" y1="5" x2="15" y2="15"/><line x1="15" y1="5" x2="5" y2="15"/></svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 20 20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" fill="none"><line x1="4" y1="6" x2="16" y2="6"/><line x1="4" y1="10" x2="16" y2="10"/><line x1="4" y1="14" x2="16" y2="14"/></svg>
                  )}
                </span>
              </button>
            </div>

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
              error={evac.error}
              onClose={evac.deactivate}
              onRouteSelect={setSelectedRoute}
              onRetry={evac.retry}
            />

            {/* First-launch onboarding */}
            {showOnboarding && (
              <Onboarding onDone={() => setShowOnboarding(false)} />
            )}

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
  liveDot: {
    color: '#00e676',
    fontSize: 16,
    lineHeight: 1,
  },
  liveText: {
    color: '#00e676',
    fontWeight: 700,
    fontSize: 13,
    letterSpacing: '0.06em',
  },
  legendSep: {
    color: '#444',
    fontSize: 14,
    margin: '0 2px',
  },
  legendItem: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 5,
    fontSize: 12,
    color: '#aaa',
    fontWeight: 600,
  },
  legendSwatch: {
    display: 'inline-block',
    width: 10,
    height: 10,
    borderRadius: 2,
    border: '1px solid rgba(255,255,255,0.15)',
  },
  menuContainer: {
    position: 'absolute',
    bottom: 40,
    left: 16,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: 8,
    zIndex: 15,
  },
  menuBtn: {
    width: 42,
    height: 42,
    borderRadius: '50%',
    border: '1px solid #555',
    background: 'rgba(10, 10, 20, 0.85)',
    color: '#ddd',
    fontSize: 20,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backdropFilter: 'blur(6px)',
    transition: 'all 0.2s',
    boxShadow: '0 2px 10px rgba(0,0,0,0.4)',
    fontFamily: 'system-ui, sans-serif',
  },
  menuPopup: {
    background: 'rgba(10, 10, 20, 0.92)',
    border: '1px solid #2a2a3d',
    borderRadius: 10,
    padding: '6px 0',
    backdropFilter: 'blur(8px)',
    boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
    marginBottom: 8,
    minWidth: 180,
  },
  menuItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    width: '100%',
    padding: '10px 16px',
    background: 'transparent',
    border: 'none',
    color: '#ccc',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'system-ui, sans-serif',
    letterSpacing: '0.02em',
    transition: 'background 0.15s',
    textAlign: 'left',
  },
  menuSvg: {
    width: 18,
    height: 18,
    flexShrink: 0,
    color: '#888',
  },
}
