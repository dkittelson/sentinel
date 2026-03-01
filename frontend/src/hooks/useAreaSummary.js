import { useState, useEffect, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const DEBOUNCE_MS = 1800   // wait 1.8s after pan stops before fetching

export function useAreaSummary(bounds) {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    if (!bounds) return

    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const { centerLat, centerLon, radiusKm } = bounds
        const url = `${API_URL}/area-summary?lat=${centerLat}&lon=${centerLon}&radius_km=${radiusKm}`
        const res = await fetch(url)
        if (!res.ok) throw new Error('API error')
        const data = await res.json()
        setSummary(data)
      } catch {
        setSummary(null)
      } finally {
        setLoading(false)
      }
    }, DEBOUNCE_MS)

    return () => clearTimeout(timerRef.current)
  }, [bounds?.centerLat, bounds?.centerLon, bounds?.radiusKm])

  return { summary, loading }
}
