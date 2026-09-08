import { useState, useCallback } from 'react'
import type { RecommendResponse } from '@/types'
import { readFetchErrorMessage } from '@/lib/apiErrorMessage'
import type { TripFormState } from '@/lib/tripParams'
import { toRecommendQuery } from '@/lib/tripParams'

export type { TripDuration, RecommendFetchOptions } from '@/lib/tripParams'

export function useRecommend() {
  const [data, setData] = useState<RecommendResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const hydrate = useCallback((payload: RecommendResponse | null) => {
    setData(payload)
    setError(null)
    setLoading(false)
  }, [])

  const fetch = useCallback(async (form: TripFormState) => {
    setLoading(true)
    setError(null)
    try {
      const res = await window.fetch(`/api/recommend?${toRecommendQuery(form)}`)
      if (!res.ok) {
        throw new Error(await readFetchErrorMessage(res, `서버 오류 (${res.status})`))
      }
      const json: RecommendResponse = await res.json()
      setData(json)
    } catch (e) {
      setError(e instanceof Error ? e.message : '알 수 없는 오류')
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, fetch, hydrate }
}
