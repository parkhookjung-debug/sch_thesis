import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ConfirmedCourseState } from '@/lib/confirmedCourseStorage'
import { clearConfirmedCourse } from '@/lib/confirmedCourseStorage'
import { saveRecommendPayloadForResult } from '@/lib/recommendSessionCache'
import { resolveTopCourseForDetail } from '@/lib/resolveTopCourse'
import { Button } from '@/components/ui/button'
import { MapPin } from 'lucide-react'

interface Props {
  confirmed: ConfirmedCourseState
}

export default function ConfirmedCourseHomeCard({ confirmed }: Props) {
  const navigate = useNavigate()
  const qs = confirmed.resultQueryString

  const top = useMemo(
    () => resolveTopCourseForDetail(confirmed.recommendPayload, confirmed.committedCourseAltId),
    [confirmed.recommendPayload, confirmed.committedCourseAltId],
  )

  if (!top) return null

  const stepsPreview = top.steps.slice(0, 3).map(s => s.name)
  const altQ =
    confirmed.committedCourseAltId != null
      ? `&altId=${encodeURIComponent(confirmed.committedCourseAltId)}`
      : ''

  return (
    <section className="mb-5 rounded-[1.35rem] border border-emerald-200/75 bg-white overflow-hidden shadow-[0_12px_44px_-20px_rgba(5,150,105,0.22)] ring-1 ring-emerald-100/85">
      <div className="bg-gradient-to-r from-emerald-700 to-emerald-600 px-4 py-2.5">
        <p className="text-[11px] font-semibold text-emerald-50/95 uppercase tracking-wide">
          내가 고른 오늘의 코스
        </p>
        <p className="text-sm font-bold text-white mt-0.5 leading-snug">{top.title}</p>
      </div>
      <div className="px-4 py-3 space-y-2 text-sm text-foreground/90">
        <ol className="space-y-1.5">
          {stepsPreview.map((name, i) => (
            <li key={`${name}-${i}`} className="flex gap-2 text-xs">
              <span className="font-bold text-primary w-5 shrink-0">{i + 1}</span>
              <span className="flex gap-1 min-w-0">
                <MapPin className="w-3.5 h-3.5 shrink-0 mt-0.5 text-primary/80" />
                <span className="leading-relaxed">{name}</span>
              </span>
            </li>
          ))}
        </ol>
        <p className="text-[11px] text-muted-foreground pt-1 border-t border-border/50">
          {[top.estimated_duration && `예상 ${top.estimated_duration}`, top.movement_burden, top.weather_fit]
            .filter(Boolean)
            .join(' · ')}
        </p>
        <div className="flex flex-col gap-2 pt-2">
          <Button
            type="button"
            className="w-full rounded-xl font-semibold"
            onClick={() => {
              saveRecommendPayloadForResult(qs, confirmed.recommendPayload)
              navigate(`/result/course?${qs}${altQ}`)
            }}
          >
            이 코스 이어서 보기
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="w-full rounded-xl font-semibold"
            onClick={() => {
              saveRecommendPayloadForResult(qs, confirmed.recommendPayload)
              navigate(`/result/edit?${qs}`, {
                state: {
                  committedSelectionAltId: confirmed.committedCourseAltId,
                },
              })
            }}
          >
            코스 수정하기
          </Button>
          <Button
            type="button"
            variant="outline"
            className="w-full rounded-xl font-medium"
            onClick={() => {
              clearConfirmedCourse()
            }}
          >
            다시 추천받기
          </Button>
        </div>
      </div>
    </section>
  )
}
