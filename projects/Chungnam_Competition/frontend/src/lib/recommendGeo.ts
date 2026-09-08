import type { RecommendResponse } from '@/types'

function normName(name: string): string {
  return name.replace(/\s+/g, ' ').trim()
}

/** 추천 목록에서 장소명 정확 일치 좌표 */
export function coordsForPlaceName(
  data: RecommendResponse,
  name: string,
): { lat: number; lng: number } | null {
  const norm = normName(name)
  const row = data.recommendations?.find(r => normName(r.name || '') === norm)
  const c = row?.coords
  if (c && typeof c.lat === 'number' && typeof c.lng === 'number') return { lat: c.lat, lng: c.lng }
  return null
}

function coordsFromTopCourseExact(
  data: RecommendResponse,
  name: string,
): { lat: number; lng: number } | null {
  const n = normName(name)
  const steps = data.top_course?.steps || []
  for (const s of steps) {
    if (normName(s.name || '') !== n) continue
    if (s.lat != null && s.lng != null && !Number.isNaN(s.lat) && !Number.isNaN(s.lng)) {
      return { lat: s.lat, lng: s.lng }
    }
  }
  return null
}

export type ReviewLookupCoordsSource = 'step' | 'payload' | 'fallback'

/** 리뷰 API용 좌표 — 스텝 좌표 → 코스 단계 정확 일치 → 추천 목록 정확 일치 → 광역 폴백 */
export function resolveReviewLookupCoords(
  recommendData: RecommendResponse | null | undefined,
  step: { name: string; lat?: number | null; lng?: number | null },
): { lat: number; lng: number; source: ReviewLookupCoordsSource } {
  const lat = step.lat
  const lng = step.lng
  if (lat != null && lng != null && !Number.isNaN(lat) && !Number.isNaN(lng)) {
    return { lat, lng, source: 'step' }
  }
  if (recommendData) {
    const fromTop = coordsFromTopCourseExact(recommendData, step.name)
    if (fromTop) return { ...fromTop, source: 'payload' }
    const fromRec = coordsForPlaceName(recommendData, step.name)
    if (fromRec) return { ...fromRec, source: 'payload' }
  }
  return { ...FALLBACK_COORDS, source: 'fallback' }
}

export function categoryForPlaceName(data: RecommendResponse, name: string): string {
  const row = data.recommendations?.find(r => r.name === name)
  const cat = row?.category
  if (cat === 'indoor' || cat === 'outdoor') return cat
  return 'outdoor'
}

export function rowForPlaceName(data: RecommendResponse, name: string) {
  return data.recommendations?.find(r => r.name === name)
}

/** 좌표를 못 찾을 때(희귀) — 아산 시청 인근 기본값 */
export const FALLBACK_COORDS = { lat: 36.7898, lng: 127.0022 }
