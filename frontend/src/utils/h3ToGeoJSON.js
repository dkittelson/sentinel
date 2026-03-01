import { cellToBoundary } from 'h3-js'

/**
 * Convert an array of hex objects (each with h3_id + properties)
 * into a Mapbox-ready GeoJSON FeatureCollection.
 */
export function hexesToGeoJSON(hexes) {
  return {
    type: 'FeatureCollection',
    features: hexes.map(hex => {
      // cellToBoundary returns [lat, lng] pairs; Mapbox wants [lng, lat]
      const boundary = cellToBoundary(hex.h3_id, true) // true = GeoJSON order [lng, lat]
      return {
        type: 'Feature',
        properties: { ...hex },
        geometry: {
          type: 'Polygon',
          coordinates: [boundary],
        },
      }
    }),
  }
}
