import { useState, useEffect } from 'react'

const BEIRUT_FALLBACK = { lng: 35.5, lat: 33.9 }

export function useUserLocation() {
  const [location, setLocation] = useState(null)
  const [ready, setReady]       = useState(false)

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocation(BEIRUT_FALLBACK)
      setReady(true)
      return
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        setLocation({ lng: pos.coords.longitude, lat: pos.coords.latitude })
        setReady(true)
      },
      () => {
        // Permission denied or unavailable — fall back to Beirut
        setLocation(BEIRUT_FALLBACK)
        setReady(true)
      },
      { timeout: 5000 }
    )
  }, [])

  return { location, ready }
}
