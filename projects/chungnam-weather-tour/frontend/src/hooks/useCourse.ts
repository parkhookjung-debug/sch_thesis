import { useState, useCallback } from 'react'
import type { NextPlace } from '@/types'

export type NextCategory = 'restaurant' | 'cafe' | 'attraction'

export interface CourseStep {
  originName: string
  originLat: number
  originLng: number
  selectedCategory: NextCategory | null   // null = 아직 선택 안 함
  places: NextPlace[]
  selected: NextPlace | null
  loading: boolean
}

async function fetchPlaces(
  lat: number, lng: number, category: string
): Promise<NextPlace[]> {
  const hour = new Date().getHours()
  const res = await window.fetch(
    `/api/course?lat=${lat}&lng=${lng}&category=${encodeURIComponent(category)}&hour=${hour}`
  )
  const data = await res.json()
  return data.next_places ?? []
}

export function useCourse() {
  const [chain, setChain] = useState<CourseStep[]>([])

  // 메인 장소 "다음 코스" 클릭 → 1단계 추가 (카테고리 선택 대기)
  const fetchFirst = useCallback((lat: number, lng: number, originName: string) => {
    setChain([{
      originName,
      originLat: lat,
      originLng: lng,
      selectedCategory: null,
      places: [],
      selected: null,
      loading: false,
    }])
  }, [])

  // 카테고리 선택 → 해당 카테고리 장소 fetch
  const selectCategory = useCallback(async (stepIdx: number, category: NextCategory) => {
    setChain(prev => prev.map((s, i) =>
      i === stepIdx ? { ...s, selectedCategory: category, loading: true, places: [] } : s
    ))
    const step = chain[stepIdx]
    try {
      const places = await fetchPlaces(step.originLat, step.originLng, category)
      setChain(prev => prev.map((s, i) =>
        i === stepIdx ? { ...s, places, loading: false } : s
      ))
    } catch {
      setChain(prev => prev.map((s, i) =>
        i === stepIdx ? { ...s, loading: false } : s
      ))
    }
  }, [chain])

  // 장소 선택 → 다음 단계 추가 (카테고리 선택 대기)
  const selectPlace = useCallback((stepIdx: number, place: NextPlace) => {
    setChain(prev => {
      const updated = prev.map((s, i) =>
        i === stepIdx ? { ...s, selected: place } : s
      )
      // 이미 다음 단계가 있으면 교체, 없으면 추가
      const next: CourseStep = {
        originName: place.name,
        originLat: place.lat,
        originLng: place.lng,
        selectedCategory: null,
        places: [],
        selected: null,
        loading: false,
      }
      return [...updated.slice(0, stepIdx + 1), next]
    })
  }, [])

  const clear = useCallback(() => setChain([]), [])

  return { chain, fetchFirst, selectCategory, selectPlace, clear }
}
