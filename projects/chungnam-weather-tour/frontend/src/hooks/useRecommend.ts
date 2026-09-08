import { useState, useCallback } from 'react'
import type { RecommendResponse } from '@/types'

export function useRecommend() {
  const [data, setData] = useState<RecommendResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async (city: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await window.fetch(`/api/recommend?city=${encodeURIComponent(city)}&top_n=40`)
      if (!res.ok) throw new Error(`서버 오류 (${res.status})`)
      const json: RecommendResponse = await res.json()
      setData(json)
    } catch (e) {
      setError(e instanceof Error ? e.message : '알 수 없는 오류')
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, fetch }
}
