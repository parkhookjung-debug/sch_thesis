import { resolveTopCourseForDetail } from '@/lib/resolveTopCourse'
import type { RecommendResponse } from '@/types'

/**
 * 확정 코스가 대안이었을 때, top_course를 그 코스로 맞춘 스냅샷(재구성·일부 화면용).
 * 원본 alternative_courses 등은 유지합니다.
 */
export function recommendPayloadWithCommittedAsTop(
  payload: RecommendResponse,
  committedCourseAltId: string | null,
): RecommendResponse {
  const resolved = resolveTopCourseForDetail(payload, committedCourseAltId)
  if (!resolved) return payload
  return { ...payload, top_course: resolved }
}
