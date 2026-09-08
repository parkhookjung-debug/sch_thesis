import type { CourseContinuationResponse, Weather } from '@/types'
import { readFetchErrorMessage } from '@/lib/apiErrorMessage'
import type { TripDuration } from '@/hooks/useRecommend'

/** useCourse / 결과 페이지 공통: /api/course 요청 URL */
export interface CourseFetchContext {
  spotId?: string
  spotName?: string
  weather?: Weather | null
  coursePath?: 'ai' | 'guided'
  userNextHint?: string
  userCustomNote?: string
  /** 결과 화면 「이 코스 기준으로 다시 짜기」에서만 true — 서버 next_scene 보조 분기 */
  mlNextSceneAssist?: boolean
  desiredNextScene?: string
  desiredCourseStyle?: string
  familyBias?: number
  scenicBias?: number
  indoorBias?: number
  mealBias?: number
  cafeBias?: number
  duration?: TripDuration
  companion?: string
  trip_goal?: string
  transport?: string
  adult_count?: string
  child_count?: string
  /** 재구성 UX: 수정 대상 식별(서버 로깅·분석·향후 분기용) */
  reconfigureTarget?: string
  selectedCourseType?: string
  courseIdForEdit?: string
  /** 단계 교체 모드 */
  replaceStep?: boolean
  stepIndex?: number
  stepRole?: string
  timeBand?: string
}

export function buildCourseUrl(
  lat: number,
  lng: number,
  category: string,
  hour: number,
  ctx?: CourseFetchContext,
): string {
  const p = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    category,
    hour: String(hour),
  })
  if (ctx?.spotId) p.set('spot_id', ctx.spotId)
  if (ctx?.spotName) p.set('spot_name', ctx.spotName)
  if (ctx?.duration) p.set('duration', ctx.duration)
  if (ctx?.companion) p.set('companion', ctx.companion)
  if (ctx?.trip_goal) p.set('trip_goal', ctx.trip_goal)
  if (ctx?.transport) p.set('transport', ctx.transport)
  if (ctx?.adult_count) p.set('adult_count', ctx.adult_count)
  if (ctx?.child_count) p.set('child_count', ctx.child_count)
  if (ctx?.weather) {
    p.set('precip_prob', String(ctx.weather.precip_prob))
    p.set('dust', String(ctx.weather.dust))
    p.set('temp', String(ctx.weather.temp))
    p.set('sky', String(ctx.weather.sky))
  }
  if (ctx?.coursePath) p.set('course_path', ctx.coursePath)
  if (ctx?.userNextHint) p.set('user_next_hint', ctx.userNextHint)
  if (ctx?.userCustomNote) p.set('user_custom_note', ctx.userCustomNote)
  if (ctx?.mlNextSceneAssist) p.set('ml_next_scene_assist', 'true')
  if (ctx?.desiredNextScene) p.set('desired_next_scene', ctx.desiredNextScene)
  if (ctx?.desiredCourseStyle) p.set('desired_course_style', ctx.desiredCourseStyle)
  if (ctx?.familyBias != null && ctx.familyBias > 0) p.set('family_bias', String(ctx.familyBias))
  if (ctx?.scenicBias != null && ctx.scenicBias > 0) p.set('scenic_bias', String(ctx.scenicBias))
  if (ctx?.indoorBias != null && ctx.indoorBias > 0) p.set('indoor_bias', String(ctx.indoorBias))
  if (ctx?.mealBias != null && ctx.mealBias > 0) p.set('meal_bias', String(ctx.mealBias))
  if (ctx?.cafeBias != null && ctx.cafeBias > 0) p.set('cafe_bias', String(ctx.cafeBias))
  if (ctx?.reconfigureTarget) p.set('reconfigure_target', ctx.reconfigureTarget)
  if (ctx?.selectedCourseType) p.set('selected_course_type', ctx.selectedCourseType)
  if (ctx?.courseIdForEdit) p.set('course_id', ctx.courseIdForEdit)
  if (ctx?.replaceStep) p.set('replace_step', 'true')
  if (ctx?.stepIndex != null) p.set('step_index', String(ctx.stepIndex))
  if (ctx?.stepRole) p.set('step_role', ctx.stepRole)
  if (ctx?.timeBand) p.set('time_band', ctx.timeBand)
  return `/api/course?${p.toString()}`
}

export async function fetchCoursePayload(
  lat: number,
  lng: number,
  category: string,
  hour: number,
  ctx?: CourseFetchContext,
): Promise<CourseContinuationResponse> {
  const res = await window.fetch(buildCourseUrl(lat, lng, category, hour, ctx))
  if (!res.ok) {
    throw new Error(await readFetchErrorMessage(res, `코스 API 오류 (${res.status})`))
  }
  return (await res.json()) as CourseContinuationResponse
}
