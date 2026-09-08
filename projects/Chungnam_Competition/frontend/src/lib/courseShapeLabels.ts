/** 서버 `course_shape_reason` / meta.plan_a_reason → 짧은 설명(디버그·투명성) */
export function courseShapeReasonNote(code: string | null | undefined): string {
  if (!code) return ''
  const m: Record<string, string> = {
    'culture-heavy': '문화·역사 둘러보기를 길게 잡는 동선이에요.',
    festival_focus: '행사·축제 후보가 있어 그 흐름을 반영했어요.',
    no_nearby_meal_candidates: '주변 식당·카페 후보가 적어 둘러보기 위주로 묶었어요.',
    meal_substituted_by_cafe: '식사 후보 대신 카페·가벼운 휴식으로 이어졌어요.',
    rain_short_indoor_cafe: '비 가능성이 있어 짧게 실내·카페 흐름을 우선했어요.',
    spot_chain_exception: '관광지만 연속된 예외 구성이에요. 중간에 식사를 넣기 좋아요.',
    fallback_ranking_only: '후보가 부족해 순위 기반으로 채웠어요.',
    night_time_shape: '심야·새벽에는 산책·야외 접근과 늦은 휴식 위주로 동선을 잡았어요.',
  }
  return m[code] || `구성 코드: ${code}`
}
