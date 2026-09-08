import type {
  AlternativeCourse,
  CourseStep,
  Destination,
  RecommendResponse,
  TopCourse,
} from '@/types'

/** API에 steps가 없을 때만 쓰는 나들이 동선 스타일 라벨(약식) */
function stepLabelsFlow(n: number): string[] {
  if (n <= 1) return ['메인 장소']
  if (n === 2) return ['메인 장소', '식사하기 좋은 곳']
  if (n === 3) return ['메인 장소', '식사하기 좋은 곳', '카페·마무리']
  return Array.from({ length: n }, (_, i) => {
    if (i === 0) return '메인 장소'
    if (i === n - 1) return '카페·마무리'
    return '이어서 둘러보기'
  })
}

function mergeBullets(row: Destination): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  const keys = [
    'expectation_bullets',
    'expectation_points',
    'why_recommend_bullets',
    'concise_explanation_lines',
  ] as const
  for (const k of keys) {
    const v = row[k]
    if (Array.isArray(v)) {
      for (const x of v) {
        const s = String(x).trim()
        if (s && !seen.has(s)) {
          seen.add(s)
          out.push(s)
        }
      }
    }
  }
  return out.slice(0, 8)
}

function introFromRow(row: Destination): string {
  for (const k of [
    'copy',
    'recommendation_summary',
    'place_identity_summary',
    'lead_place_sentence',
    'story_summary',
  ] as const) {
    const s = String(row[k] ?? '').trim()
    if (s.length > 24) return s.slice(0, 900)
  }
  const w = row.why_today_narrative
  if (typeof w === 'string' && w.trim()) return w.trim().slice(0, 900)
  return ''
}

export function topCourseFromAlternative(alt: AlternativeCourse, data: RecommendResponse): TopCourse {
  if (alt.steps && alt.steps.length > 0) {
    return {
      id: alt.id,
      course_id: alt.course_id ?? alt.id,
      title: alt.title,
      pitch: alt.pitch ?? alt.one_liner ?? '',
      reasons_title: alt.reasons_title ?? '이 코스는',
      reasons: alt.reasons?.length ? alt.reasons : [alt.one_liner || '같은 조건에서 다른 코스를 제안했어요.'],
      reason_tags: alt.reason_tags,
      steps: alt.steps,
      hero_image: alt.hero_image ?? null,
      hero_name: alt.hero_name ?? alt.steps[0]?.name ?? alt.title,
      estimated_duration: alt.estimated_duration,
      movement_burden: alt.movement_burden,
      weather_fit: alt.weather_fit,
    }
  }
  const recs = data.recommendations ?? []
  const names = alt.place_names
  const labels = stepLabelsFlow(names.length)
  const steps: CourseStep[] = names.map((name, i) => {
    const row = recs.find(r => r.name === name)
    const oneLine =
      row?.place_identity_summary ||
      row?.decision_conclusion ||
      row?.lead_place_sentence ||
      `${name} 둘러보기`
    const line = typeof oneLine === 'string' ? oneLine : String(oneLine)
    return {
      order: i + 1,
      step_label: labels[i] ?? `${i + 1}번`,
      name,
      one_line: line.slice(0, 88),
      image: row?.image,
      address: row?.address,
      detail_intro: row ? introFromRow(row) : '',
      detail_bullets: row ? mergeBullets(row) : [],
      tag_labels: [...(row?.enriched_tags ?? row?.tags ?? [])].slice(0, 8).map(String),
      rating: row?.rating && row.rating > 0 ? row.rating : null,
      review_count: row?.review_count ?? 0,
    }
  })
  const hero = recs.find(r => r.name === names[0])
  return {
    id: alt.id,
    title: alt.title,
    pitch: alt.one_liner || '',
    reasons_title: '이 코스는',
    reasons: [alt.one_liner || '같은 조건에서 다른 동선을 제안한 코스예요.'],
    steps,
    hero_image: hero?.image ?? null,
    hero_name: names[0] || alt.title,
  }
}

/** altId 없음·main → API top_course; 그 외 alternative_courses 매칭 */
export function resolveTopCourseForDetail(
  data: RecommendResponse,
  altId: string | null,
): TopCourse | undefined {
  if (!altId || altId === 'main') {
    return data.top_course
  }
  const alts = data.alternative_courses ?? []
  const alt =
    alts.find(a => a.id === altId) ??
    (altId === 'plan_b' ? alts.find(a => a.id === 'course_weather_alt') : undefined)
  if (!alt) return data.top_course
  return topCourseFromAlternative(alt, data)
}
