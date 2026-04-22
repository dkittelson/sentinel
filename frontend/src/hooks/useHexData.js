import { useState, useEffect, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const POLL_INTERVAL_MS = 30_000
const TIMEOUT_MS = 7_000   // show "delayed" message after 7s with no data

export function useHexData() {
  const [hexes, setHexes]               = useState([])
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState(null)
  const [lastFetchedAt, setLastFetchedAt] = useState(null)
  const [timedOut, setTimedOut]         = useState(false)
  const timerRef                        = useRef(null)
  const timeoutRef                      = useRef(null)

  async function fetchHexes() {
    try {
      const res = await fetch(`${API_URL}/hexes`)
      if (!res.ok) throw new Error(`API returned ${res.status}`)
      const data = await res.json()
      setHexes(data)
      setLastFetchedAt(new Date())
      setTimedOut(false)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      clearTimeout(timeoutRef.current)
    }
  }

  useEffect(() => {
    // If first fetch takes too long, surface a "delayed" state
    timeoutRef.current = setTimeout(() => {
      setTimedOut(true)
      setLoading(false)
    }, TIMEOUT_MS)

    fetchHexes()
    timerRef.current = setInterval(fetchHexes, POLL_INTERVAL_MS)
    return () => {
      clearInterval(timerRef.current)
      clearTimeout(timeoutRef.current)
    }
  }, [])

  return { hexes, loading, error, lastFetchedAt, timedOut }
}
