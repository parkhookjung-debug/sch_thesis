import { useState } from 'react'
import type { CourseContinuationResponse, NextPlace } from '@/types'
import { Button } from '@/components/ui/button'

export default function NextCoursePreview({
  title,
  loading,
  first,
  rest,
  fullPayload,
  onContinue,
}: {
  title: string
  loading: boolean
  first: NextPlace | null
  rest: NextPlace[]
  fullPayload: CourseContinuationResponse | null
  onContinue: () => void
}) {
  const [showAll, setShowAll] = useState(false)
  if (loading) {
    return (
      <section className="mt-7 rounded-2xl border border-dashed border-border/60 bg-white/30 px-4 py-4">
        <p className="text-xs text-muted-foreground">다음 동선을 불러오는 중…</p>
      </section>
    )
  }
  if (!first) {
    return null
  }

  const oneLine =
    first.recommendation_reason_one_line?.trim() ||
    (fullPayload?.next_scene?.headline
      || fullPayload?.next_step_headline
      || fullPayload?.next_stage?.title
      || '가볍게 이어가기 무난한 곳이에요.')

  return (
    <section className="mt-7 rounded-2xl border border-primary/15 bg-primary/5 overflow-hidden" aria-label="다음 코스">
      <div className="px-4 py-3.5">
        <p className="text-[11px] font-bold text-primary uppercase tracking-wider">
          {title}
        </p>
        <p className="text-sm font-extrabold text-foreground mt-1.5">1순위: {first.name}</p>
        <p className="text-sm text-foreground/85 mt-1.5 leading-relaxed">{oneLine}</p>
        {fullPayload?.meal_style?.label && (
          <p className="text-[11px] text-muted-foreground mt-1.5">
            {fullPayload.meal_style.label} 느낌을 살려볼 수 있어요.
          </p>
        )}
        <div className="flex flex-col sm:flex-row gap-2 mt-3">
          <Button
            type="button"
            size="sm"
            className="rounded-xl font-semibold"
            onClick={onContinue}
          >
            이어서 보기
          </Button>
          {rest.length > 0 && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="rounded-xl font-semibold"
              onClick={() => setShowAll(v => !v)}
            >
              {showAll ? '접기' : '다른 선택지도 보기'}
            </Button>
          )}
        </div>
        {showAll && rest.length > 0 && (
          <ol className="mt-3 space-y-1.5 pl-0 list-decimal pl-4 text-sm text-foreground/90">
            {rest.map(p => (
              <li key={p.name}>{p.name}</li>
            ))}
          </ol>
        )}
      </div>
    </section>
  )
}
