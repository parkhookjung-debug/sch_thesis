import { useState, useCallback } from 'react'
import type { PlaceReview } from '@/types'

interface ReviewData {
  rating: number
  review_count: number
  reviews: PlaceReview[]
  website: string
  google_maps: string
  open_now: boolean | null
}

export function usePlaceReviews() {
  const [data, setData] = useState<ReviewData | null>(null)
  const [loading, setLoading] = useState(false)
  const [fetched, setFetched] = useState(false)

  const fetch = useCallback(async (name: string, lat: number, lng: number, address = '') => {
    if (fetched) return
    setLoading(true)
    try {
      const res = await window.fetch(
        `/api/place-reviews?name=${encodeURIComponent(name)}&lat=${lat}&lng=${lng}&address=${encodeURIComponent(address)}`
      )
      const json = await res.json()
      setData(json?.reviews ? json : null)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
      setFetched(true)
    }
  }, [fetched])

  const reset = useCallback(() => {
    setData(null)
    setFetched(false)
  }, [])

  return { data, loading, fetched, fetch, reset }
}
