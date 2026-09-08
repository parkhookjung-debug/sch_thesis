import { useEffect, useRef } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { useRecommend } from '@/hooks/useRecommend'
import { tripFormFromSearchParams } from '@/lib/tripParams'
import { isCurrentRecommendPayload, loadRecommendPayloadForResult } from '@/lib/recommendSessionCache'
import type { RecommendResponse } from '@/types'

/**
 * /result* 에서 URL 쿼리 + navigate state.data 로 추천 페이로드를 맞춤.
 */
export function useRecommendFromRoute() {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const form = tripFormFromSearchParams(searchParams)
  const { data, loading, error, fetch, hydrate } = useRecommend()
  const fetchOnceRef = useRef(false)

  useEffect(() => {
    if (searchParams.get('mock') === '1') {
      hydrate(null)
      return
    }
    const rawNav = (location.state as { data?: RecommendResponse } | null)?.data
    const fromNav = isCurrentRecommendPayload(rawNav) ? rawNav : null
    const fromSession = loadRecommendPayloadForResult(searchParams)
    const inlined = fromNav ?? fromSession
    if (inlined) {
      hydrate(inlined)
      return
    }
    if (fetchOnceRef.current) return
    fetchOnceRef.current = true
    void fetch(form)
  }, [
    location.key,
    location.state,
    hydrate,
    fetch,
    form.city,
    form.tripDuration,
    form.companion,
    form.tripGoal,
    form.transport,
    form.adultCount,
    form.childCount,
    form.currentTime,
    form.currentDate,
    form.mealPreference,
    form.tourpassMode,
    form.tourpassTicketType,
    form.benefitPriority,
    form.passGoal,
    form.purchasedStatus,
    searchParams,
  ])

  return { form, data, loading, error, searchParams }
}
