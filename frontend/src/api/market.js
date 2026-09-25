const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

async function getJson(path, signal) {
  let response
  try {
    response = await fetch(`${apiBase}${path}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('Could not connect to the market service. Check your connection and retry.')
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.error?.message || 'Market data is temporarily unavailable.')
  }
  return payload?.data
}

export function fetchMarketCommodities(signal) {
  return getJson('/api/market/commodities', signal)
}

export function fetchMarketPrices({ commodityId, state, district }, signal) {
  const params = new URLSearchParams({ commodity_id: commodityId, state, limit: '100' })
  if (district) params.set('district', district)
  return getJson(`/api/market/prices?${params}`, signal)
}

export function fetchMarketHistory({ commodityId, mandiId, days }, signal) {
  const params = new URLSearchParams({ commodity_id: commodityId, days: String(days) })
  if (mandiId) params.set('mandi_id', mandiId)
  return getJson(`/api/market/history?${params}`, signal)
}

export function distanceKm(latitudeA, longitudeA, latitudeB, longitudeB) {
  const radians = (degrees) => degrees * Math.PI / 180
  const latitudeDelta = radians(latitudeB - latitudeA)
  const longitudeDelta = radians(longitudeB - longitudeA)
  const haversine = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(radians(latitudeA)) * Math.cos(radians(latitudeB))
      * Math.sin(longitudeDelta / 2) ** 2
  return 6371.0088 * 2 * Math.asin(Math.sqrt(Math.min(1, haversine)))
}
