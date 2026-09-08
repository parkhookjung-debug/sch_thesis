import { useState, useCallback, useRef } from 'react'

import type { CourseContinuationResponse, NextPlace, Weather } from '@/types'
import type { TripDuration } from '@/hooks/useRecommend'
import {
  fetchCoursePayload,
  type CourseFetchContext,
} from '@/lib/courseClient'

export type { CourseFetchContext } from '@/lib/courseClient'

export type NextCategory = 'restaurant' | 'cafe' | 'attraction'

export interface CourseStep {
  label: string
  originName: string
  originLat: number
  originLng: number
  selectedCategory: NextCategory | null
  places: NextPlace[]
  payload?: CourseContinuationResponse | null
  selected: NextPlace | null
  loading: boolean
}

/** 일정 길이별 최대 코스 단계 수(첫 화면 포함): 2h→2, 반나절→3, 종일→4 */
export function maxCourseStepsForDuration(d: TripDuration): number {
  if (d === '2h') return 2
  if (d === 'full-day') return 4
  return 3
}

function continuationLabels(d: TripDuration): string[] {
  if (d === '2h') return ['다음 한 곳']
  if (d === 'full-day') return ['점심·휴식', '오후 장면', '저녁·마무리']
  return ['쉬었다 가기', '마무리 동선']
}

export function useCourse() {
  const [chain, setChain] = useState<CourseStep[]>([])
  const lastWeatherRef = useRef<Weather | null>(null)
  const lastDurationRef = useRef<TripDuration>('half-day')
  const lastIntentRef = useRef({
    companion: 'solo',
    trip_goal: 'healing',
    transport: 'car',
    adult_count: '2',
    child_count: '0',
  })

  const fetchFirst = useCallback(
    (lat: number, lng: number, originName: string, ctx?: CourseFetchContext) => {
      lastWeatherRef.current = ctx?.weather ?? null
      lastDurationRef.current = ctx?.duration ?? 'half-day'
      lastIntentRef.current = {
        companion: ctx?.companion ?? 'solo',
        trip_goal: ctx?.trip_goal ?? 'healing',
        transport: ctx?.transport ?? 'car',
        adult_count: ctx?.adult_count ?? '2',
        child_count: ctx?.child_count ?? '0',
      }

      setChain([
        {
          label: '코스 이어가기',
          originName,
          originLat: lat,
          originLng: lng,
          selectedCategory: null,
          places: [],
          payload: null,
          selected: null,
          loading: false,
        },
      ])
    },
    [],
  )

  const selectCategory = useCallback(async (stepIdx: number, category: NextCategory) => {
    let step: CourseStep | undefined
    setChain(prev => {
      step = prev[stepIdx]
      if (!step) return prev
      return prev.map((s, i) =>
        i === stepIdx ? { ...s, selectedCategory: category, loading: true, places: [] } : s,
      )
    })
    if (!step) return

    try {
      const hour = new Date().getHours()
      const data = await fetchCoursePayload(step.originLat, step.originLng, category, hour, {
        spotName: step.originName,
        weather: lastWeatherRef.current ?? undefined,
        duration: lastDurationRef.current,
        companion: lastIntentRef.current.companion,
        trip_goal: lastIntentRef.current.trip_goal,
        transport: lastIntentRef.current.transport,
        adult_count: lastIntentRef.current.adult_count,
        child_count: lastIntentRef.current.child_count,
      })
      setChain(prev =>
        prev.map((s, i) =>
          i === stepIdx
            ? { ...s, places: data.next_places ?? [], payload: data, loading: false }
            : s,
        ),
      )
    } catch {
      setChain(prev => prev.map((s, i) => (i === stepIdx ? { ...s, loading: false } : s)))
    }
  }, [])

  const selectPlace = useCallback((stepIdx: number, place: NextPlace) => {
    setChain(prev => {
      const updated = prev.map((s, i) => (i === stepIdx ? { ...s, selected: place } : s))
      const maxSteps = maxCourseStepsForDuration(lastDurationRef.current)
      if (stepIdx + 1 >= maxSteps) return updated

      const labels = continuationLabels(lastDurationRef.current)
      const lbl = labels[stepIdx] ?? `다음 코스 ${stepIdx + 2}`

      const next: CourseStep = {
        label: lbl,
        originName: place.name,
        originLat: place.lat,
        originLng: place.lng,
        selectedCategory: null,
        places: [],
        payload: null,
        selected: null,
        loading: false,
      }
      return [...updated.slice(0, stepIdx + 1), next]
    })
  }, [])

  const clear = useCallback(() => setChain([]), [])

  return { chain, fetchFirst, selectCategory, selectPlace, clear }
}
