import { useState, useEffect, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const POLL_INTERVAL_MS = 30_000

export function useHexData() {
  const [hexes, setHexes]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const timerRef              = useRef(null)

  async function fetchHexes() {
    try {
      const res = await fetch(`${API_URL}/hexes`)
      if (!res.ok) throw new Error(`API returned ${res.status}`)
      const data = await res.json()
      setHexes(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHexes()
    timerRef.current = setInterval(fetchHexes, POLL_INTERVAL_MS)
    return () => clearInterval(timerRef.current)
  }, [])

  return { hexes, loading, error }
}
