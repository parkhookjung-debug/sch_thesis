import type {
  CourseContinuationResponse,
  CourseStep,
  Destination,
  RecommendResponse,
  TopCourse,
} from '@/types'
import { reconfigureTagLabel, type ReconfigureTag } from '@/lib/reconfigureBias'
import { consumerStepLabel } from '@/lib/stepRoleLabels'

export interface CommitReconfigureOptions {
  /** 편집 기준이 되는 코스(미지정 시 data.top_course) */
  baseCourse?: TopCourse
  /** 편집한 코스가 원래 대안이었으면 목록에서 제거할 id */
  removeAlternativeId?: string | null
}

/**
 * /api/course 미리보기 결과를 선택한 코스에 한 단계 append 후, 그 결과를 top_course로 반영 + recommendations 보강.
 */
export function commitReconfigureIntoRecommend(
  data: RecommendResponse,
  result: CourseContinuationResponse,
  tag: ReconfigureTag,
  options?: CommitReconfigureOptions,
): RecommendResponse {
  const pick =
    result.next_places?.find(p => p.name === result.primary_recommendation?.name) ??
    result.next_places?.[0]
  const name = result.primary_recommendation?.name ?? pick?.name
  const top = options?.baseCourse ?? data.top_course
  if (!name || !top?.steps?.length) return data
  const order = top.steps.length + 1
  const hintLabel = reconfigureTagLabel(tag)
  const stepLabel =
    (result.next_stage?.title && result.next_stage.title.slice(0, 28)) ||
    `다음 코스 (${hintLabel})`

  const whyLines = result.primary_recommendation?.why ?? []
  const stageType = String(result.next_stage?.type ?? '')
  const stepRole =
    stageType === 'meal'
      ? 'meal'
      : stageType.includes('cafe')
        ? 'cafe_rest'
        : 'secondary_spot'

  const newStep: CourseStep = {
    order,
    step_label: stepLabel,
    step_role: stepRole,
    name,
    one_line:
      result.next_stage?.headline ||
      (whyLines[0] as string | undefined) ||
      `「${hintLabel}」흐름으로 이어진 코스예요.`,
    image: pick?.photo_url ?? undefined,
    address: pick?.address ?? result.primary_recommendation?.address ?? '',
    detail_intro: whyLines.filter(Boolean).join('\n'),
    detail_bullets: (result.alternatives ?? []).slice(0, 5).map(p => p.name),
    tag_labels: tag ? [`다시 짜기 · ${hintLabel}`] : ['다시 짜기'],
    rating: pick?.rating,
    review_count: pick?.review_count,
  }

  const newDest: Destination = {
    name: pick?.name ?? name,
    address: pick?.address ?? result.primary_recommendation?.address ?? '',
    tags: [],
    score: 0,
    weather_score: 0,
    distance_km: pick?.distance_from_prev_km ?? 0,
    copy: newStep.one_line,
    coords: pick ? { lat: pick.lat, lng: pick.lng } : undefined,
    image: pick?.photo_url ?? undefined,
    id: pick?.place_id,
    rating: pick?.rating,
    review_count: pick?.review_count,
  }

  const recommendations = [...(data.recommendations ?? [])]
  if (!recommendations.some(r => r.name === newDest.name)) recommendations.push(newDest)

  const pitchExtra = result.next_stage?.headline ? `\n${result.next_stage.headline}` : ''
  const removeId = options?.removeAlternativeId
  const alternative_courses =
    removeId && (data.alternative_courses?.length ?? 0) > 0
      ? (data.alternative_courses ?? []).filter(a => a.id !== removeId)
      : data.alternative_courses

  return {
    ...data,
    recommendations,
    alternative_courses,
    top_course: {
      ...top,
      steps: [...top.steps, newStep],
      hero_name: name,
      hero_image: pick?.photo_url ?? top.hero_image,
      pitch: `${top.pitch}${pitchExtra}`.slice(0, 900),
      reasons: [
        `「${hintLabel}」방향으로 다음 장소를 코스에 반영했어요.`,
        ...(top.reasons ?? []).slice(0, 2),
      ],
    },
  }
}

function stepRoleFromNextStage(stageType: string): string {
  const s = String(stageType || '')
  if (s === 'meal') return 'meal'
  if (s.includes('cafe')) return 'cafe_rest'
  return 'secondary_spot'
}

/**
 * 현재 코스에서 지정한 단계만 교체해 top_course·recommendations를 갱신.
 */
export function commitReplaceStepInRecommend(
  data: RecommendResponse,
  result: CourseContinuationResponse,
  stepIndexZeroBased: number,
  tag: ReconfigureTag,
  baseCourse: TopCourse,
  options?: CommitReconfigureOptions,
): RecommendResponse {
  const orig = baseCourse.steps[stepIndexZeroBased]
  if (!orig) return data

  const pick =
    result.next_places?.find(p => p.name === result.primary_recommendation?.name) ??
    result.next_places?.[0]
  const name = result.primary_recommendation?.name ?? pick?.name
  if (!name) return data

  const hintLabel = reconfigureTagLabel(tag)
  const preservedRole = (orig.step_role || '').trim()
  const stepRole = preservedRole || stepRoleFromNextStage(result.next_stage?.type ?? '')

  const whyLines = result.primary_recommendation?.why ?? []
  const newStep: CourseStep = {
    order: stepIndexZeroBased + 1,
    step_label: consumerStepLabel(stepRole),
    step_role: stepRole,
    name,
    one_line:
      result.next_stage?.headline ||
      (whyLines[0] as string | undefined) ||
      `「${hintLabel}」방향으로 이 단계를 바꿔 봤어요.`,
    image: pick?.photo_url ?? undefined,
    address: pick?.address ?? result.primary_recommendation?.address ?? '',
    detail_intro: whyLines.filter(Boolean).join('\n'),
    detail_bullets: (result.alternatives ?? []).slice(0, 5).map(p => p.name),
    tag_labels: tag ? [`단계 수정 · ${hintLabel}`] : ['단계 수정'],
    rating: pick?.rating,
    review_count: pick?.review_count,
  }

  const newDest: Destination = {
    name: pick?.name ?? name,
    address: pick?.address ?? result.primary_recommendation?.address ?? '',
    tags: [],
    score: 0,
    weather_score: 0,
    distance_km: pick?.distance_from_prev_km ?? 0,
    copy: newStep.one_line,
    coords: pick ? { lat: pick.lat, lng: pick.lng } : undefined,
    image: pick?.photo_url ?? undefined,
    id: pick?.place_id,
    rating: pick?.rating,
    review_count: pick?.review_count,
  }

  const recommendations = [...(data.recommendations ?? [])].filter(r => r.name !== orig.name)
  if (!recommendations.some(r => r.name === newDest.name)) recommendations.push(newDest)

  const newSteps = baseCourse.steps.map((s, i) => (i === stepIndexZeroBased ? newStep : s))
  const pitchExtra = result.next_stage?.headline ? `\n${result.next_stage.headline}` : ''
  const removeId = options?.removeAlternativeId
  const alternative_courses =
    removeId && (data.alternative_courses?.length ?? 0) > 0
      ? (data.alternative_courses ?? []).filter(a => a.id !== removeId)
      : data.alternative_courses

  const top = baseCourse
  const heroFirst = stepIndexZeroBased === 0

  return {
    ...data,
    recommendations,
    alternative_courses,
    top_course: {
      ...top,
      steps: newSteps,
      hero_name: heroFirst ? name : top.hero_name,
      hero_image: heroFirst ? (pick?.photo_url ?? top.hero_image) : top.hero_image,
      pitch: `${top.pitch}${pitchExtra}`.slice(0, 900),
      reasons: [
        `「${hintLabel}」방향으로 ${stepIndexZeroBased + 1}번째 단계만 바꿨어요.`,
        ...(top.reasons ?? []).slice(0, 2),
      ],
    },
  }
}

