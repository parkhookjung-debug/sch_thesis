/** 서버 step_role → 소비자용 짧은 라벨 */
export function consumerStepLabel(role: string | null | undefined): string {
  const r = String(role || '').trim().toLowerCase()
  const m: Record<string, string> = {
    main_spot: '메인 장소',
    meal: '식사',
    cafe_rest: '카페/마무리',
    secondary_spot: '보조 장소',
    finish: '마무리',
    night_walk: '야간 산책',
    late_night_rest: '쉬어가기',
  }
  return m[r] || '둘러보기'
}

export function clientTimeBand(hour: number): string {
  const h = hour % 24
  if (h >= 20 || h < 2) return 'night_late'
  if (h >= 2 && h < 6) return 'dawn'
  if (h >= 9 && h < 11) return 'morning'
  if (h >= 11 && h < 13) return 'lunch'
  if (h >= 13 && h < 17) return 'afternoon'
  if (h >= 17 && h < 20) return 'evening'
  return 'early'
}
