import { MapPin } from 'lucide-react'
import CourseStepGoogleReviews from '@/components/CourseStepGoogleReviews'
import type { CourseStep } from '@/types'

interface Props {
  steps: CourseStep[]
}

export default function CourseStepDetailCards({ steps }: Props) {
  return (
    <div className="mt-3 space-y-3">
      {steps.map((s) => {
        const intro = (s.detail_intro ?? '').trim()
        const bullets = s.detail_bullets ?? []
        const tags = s.tag_labels ?? []
        const hasBody = intro.length > 0 || bullets.length > 0 || tags.length > 0
        return (
          <div
            key={`${s.order}-${s.name}`}
            className="rounded-2xl border border-border/50 bg-zinc-50/80 px-3 py-3 text-left"
          >
            <p className="text-[10px] font-bold text-primary/90">{s.step_label}</p>
            <p className="text-sm font-bold text-foreground mt-0.5">{s.name}</p>
            {s.address ? (
              <p className="text-[10px] text-muted-foreground mt-1 flex items-start gap-1">
                <MapPin className="w-3 h-3 shrink-0 mt-0.5" />
                {s.address}
              </p>
            ) : null}
            {(s.review_count ?? 0) > 0 || (s.rating ?? 0) > 0 ? (
              <p className="text-[11px] text-foreground/80 mt-2 font-medium">
                Google Places · 평점 {(s.rating ?? 0).toFixed(1)} · 리뷰{' '}
                {(s.review_count ?? 0).toLocaleString()}건
              </p>
            ) : null}
            <CourseStepGoogleReviews step={s} />
            {!hasBody ? (
              <p className="text-xs text-muted-foreground mt-2">
                이 구간은 요약만 있어요. 현장에서 분위기를 확인해 보세요.
              </p>
            ) : (
              <>
                {tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {tags.map((t) => (
                      <span
                        key={t}
                        className="text-[10px] bg-white border border-border/60 text-foreground/80 px-2 py-0.5 rounded-full"
                      >
                        #{t}
                      </span>
                    ))}
                  </div>
                )}
                {intro ? (
                  <p className="text-xs text-foreground/85 mt-2 leading-relaxed whitespace-pre-wrap">
                    {intro}
                  </p>
                ) : null}
                {bullets.length > 0 && (
                  <ul className="mt-2 space-y-1.5 text-xs text-foreground/80">
                    {bullets.map((b, j) => (
                      <li key={j} className="pl-1 flex gap-2">
                        <span className="text-primary shrink-0">·</span>
                        <span className="leading-relaxed">{b}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}
