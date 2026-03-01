import { useState, useEffect, useRef, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Hook for backtest mode: fetches hex data for a specific historical date
 * and supports auto-play through a date range.
 */
export function useBacktest() {
  const [active, setActive]       = useState(false)
  const [playing, setPlaying]     = useState(false)
  const [hexes, setHexes]         = useState([])
  const [loading, setLoading]     = useState(false)
  const [currentDate, setCurrentDate] = useState(null)
  const [dateRange, setDateRange] = useState(null)
  const [speed, setSpeed]         = useState(500) // ms between frames
  const timerRef                  = useRef(null)

  // Fetch available date range on mount
  useEffect(() => {
    fetch(`${API_URL}/backtest/date-range`)
      .then(r => r.json())
      .then(data => {
        setDateRange(data)
        // Default to Oct 1, 2023 (pre-escalation demo start)
        setCurrentDate('2023-10-01')
      })
      .catch(err => console.error('Failed to fetch date range:', err))
  }, [])

  // Fetch hexes for a specific date
  const fetchDate = useCallback(async (date) => {
    if (!date) return
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/hexes/backtest?date=${date}`)
      if (!res.ok) throw new Error(`API ${res.status}`)
      const data = await res.json()
      setHexes(data)
      setCurrentDate(date)
    } catch (err) {
      console.error('Backtest fetch failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-play: advance one day at a time
  useEffect(() => {
    if (!playing || !active) {
      clearInterval(timerRef.current)
      return
    }

    timerRef.current = setInterval(() => {
      setCurrentDate(prev => {
        if (!prev || !dateRange) return prev
        const next = new Date(prev)
        next.setDate(next.getDate() + 1)
        const nextStr = next.toISOString().slice(0, 10)

        if (nextStr > dateRange.max_date) {
          setPlaying(false)
          return prev
        }
        fetchDate(nextStr)
        return nextStr
      })
    }, speed)

    return () => clearInterval(timerRef.current)
  }, [playing, active, speed, dateRange, fetchDate])

  // Enter backtest mode  
  const enter = useCallback((startDate) => {
    setActive(true)
    setPlaying(false)
    const date = startDate || '2023-10-01'
    setCurrentDate(date)
    fetchDate(date)
  }, [fetchDate])

  // Exit backtest mode
  const exit = useCallback(() => {
    setActive(false)
    setPlaying(false)
    setHexes([])
    setCurrentDate(null)
    clearInterval(timerRef.current)
  }, [])

  const play  = useCallback(() => setPlaying(true), [])
  const pause = useCallback(() => setPlaying(false), [])

  const goToDate = useCallback((date) => {
    setPlaying(false)
    fetchDate(date)
  }, [fetchDate])

  return {
    active,
    playing,
    hexes,
    loading,
    currentDate,
    dateRange,
    speed,
    setSpeed,
    enter,
    exit,
    play,
    pause,
    goToDate,
  }
}
