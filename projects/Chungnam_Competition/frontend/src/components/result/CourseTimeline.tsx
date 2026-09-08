import type { TripDuration } from '@/hooks/useRecommend'

function stepsFor(
  duration: TripDuration,
  mainLabel: string,
): { label: string; hint?: string }[] {
  const main = mainLabel || '추천 메인'
  if (duration === '2h') {
    return [
      { label: main, hint: '메인에서 여유롭게' },
      { label: '가벼운 휴식(카페/간단 식사)', hint: '부담 없이 마무리' },
    ]
  }
  if (duration === 'full-day') {
    return [
      { label: main, hint: '느지막히 둘러봐도 좋아요' },
      { label: '점심·휴식' },
      { label: '오후 2차 볼거리' },
      { label: '저녁·카페로 가볍게 정리' },
    ]
  }
  return [
    { label: main, hint: '핵심에 집중해 천천히' },
    { label: '점심 식사' },
    { label: '카페·짧은 마무리' },
  ]
}

export default function CourseTimeline({
  duration,
  mainPlaceName,
}: {
  duration: TripDuration
  mainPlaceName: string
}) {
  const mainShort =
    mainPlaceName.length > 10 ? mainPlaceName.slice(0, 9) + '…' : mainPlaceName
  const items = stepsFor(duration, `「${mainShort}」`)
  return (
    <section className="mt-6" aria-label="오늘의 코스 흐름">
      <h3 className="text-sm font-bold text-foreground mb-3">오늘의 코스 흐름</h3>
      <ol className="space-y-0 border-l-2 border-primary/25 pl-4">
        {items.map((s, i) => (
          <li key={i} className="pb-4 last:pb-0 relative">
            <span
              className="absolute -left-[21px] top-0.5 w-4 h-4 rounded-full bg-primary text-primary-foreground text-[10px] font-bold flex items-center justify-center"
            >
              {i + 1}
            </span>
            <p className="text-sm font-semibold text-foreground leading-snug">{s.label}</p>
            {s.hint ? (
              <p className="text-[11px] text-muted-foreground mt-0.5">{s.hint}</p>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  )
}
