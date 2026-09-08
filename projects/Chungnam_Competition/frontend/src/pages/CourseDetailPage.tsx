import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Check, Clock, Cloud } from 'lucide-react'
import { useRecommendFromRoute } from '@/hooks/useRecommendFromRoute'
import { toResultQueryString } from '@/lib/tripParams'
import { resolveTopCourseForDetail } from '@/lib/resolveTopCourse'
import { getTheme } from '@/lib/weather'
import { APP_NAME } from '@/config/app'
import CourseStepDetailCards from '@/components/CourseStepDetailCards'
import ServiceFooter from '@/components/ServiceFooter'
import { Button } from '@/components/ui/button'
import { altIdToCommittedKey, saveConfirmedCourse } from '@/lib/confirmedCourseStorage'
import { saveRecommendPayloadForResult } from '@/lib/recommendSessionCache'

function formatFcstTimeSlot(raw: string | null | undefined): string | null {
  if (!raw) return null
  const t = String(raw).replace(/\D/g, '')
  if (t.length === 4) return `${t.slice(0, 2)}:${t.slice(2)}`
  return raw
}

export default function CourseDetailPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { form, data, loading, error } = useRecommendFromRoute()
  const altId = searchParams.get('altId')
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (error) {
      document.title = `${APP_NAME} · 오류`
      return
    }
    if (loading && !data) {
      document.title = `${APP_NAME} · 코스 설명`
      return
    }
    if (data) {
      document.title = `${APP_NAME} · 코스 자세히`
    }
  }, [error, data, loading])

  const qs = toResultQueryString(form)

  if (loading && !data) {
    return (
      <div className="min-h-dvh flex flex-col bg-slate-900 text-slate-400 text-sm items-center justify-center px-6">
        코스 설명을 불러오는 중…
      </div>
    )
  }
  if (error) {
    return (
      <div className="min-h-dvh flex flex-col items-center justify-center px-6 text-destructive text-sm">
        {error}
        <Link to={`/?${qs}`} className="mt-4 text-foreground underline">
          홈으로
        </Link>
      </div>
    )
  }
  if (!data) return null

  const top = resolveTopCourseForDetail(data, altId)
  if (!top) {
    return (
      <div className="min-h-dvh flex flex-col items-center justify-center px-6 text-sm text-muted-foreground">
        코스 정보가 없어요.
        <button
          type="button"
          className="mt-4 text-primary font-semibold"
          onClick={() => {
            saveRecommendPayloadForResult(qs, data)
            navigate(`/result?${qs}`)
          }}
        >
          추천 화면으로
        </button>
      </div>
    )
  }

  const theme = getTheme(data.weather.sky, data.weather.precip_prob)
  const areaTint =
    theme === 'rainy'
      ? 'from-slate-200 to-slate-100'
      : theme === 'cloudy'
        ? 'from-zinc-200 to-zinc-50'
        : 'from-amber-100/90 to-amber-50/50'
  const timeStr = now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
  const fcstLabel = formatFcstTimeSlot(data.weather.fcst_time_slot)
  const weatherLine = [
    '단기예보',
    fcstLabel && `기준 ${fcstLabel}`,
    data.weather.sky_text,
    `${data.weather.temp}°`,
    `강수 ${data.weather.precip_prob}%`,
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="min-h-dvh flex flex-col bg-slate-950 text-white max-w-lg mx-auto w-full overflow-x-hidden">
      <div className="pt-[max(0.35rem,env(safe-area-inset-top))] pl-1 pr-3 h-[3.15rem] flex items-center justify-between border-b border-white/10">
        <button
          type="button"
          onClick={() => {
            saveRecommendPayloadForResult(qs, data)
            navigate(`/result?${qs}`)
          }}
          className="inline-flex items-center gap-0.5 text-sm font-medium text-white/90 pl-1 py-2 pr-1"
        >
          <ArrowLeft className="w-4 h-4" />
          뒤로
        </button>
        <span className="text-sm font-bold tracking-tight text-white/95">코스 자세히</span>
        <span className="text-xs tabular-nums text-white/70 font-medium flex items-center gap-0.5">
          <Clock className="w-3.5 h-3.5 opacity-80" />
          {timeStr}
        </span>
      </div>
      <div className="px-4 py-2.5 border-b border-white/5 bg-slate-900/80">
        <p className="text-xs text-slate-300/95 leading-relaxed flex gap-1.5">
          <Cloud className="w-3.5 h-3.5 shrink-0 mt-0.5 text-sky-300/90" />
          {weatherLine}
        </p>
      </div>

      <div className={`flex-1 text-foreground bg-zinc-50 rounded-t-2xl border-t border-white/10`}>
        <div className={`px-4 pt-4 pb-2 bg-gradient-to-b ${areaTint} rounded-t-2xl border-b border-black/[0.04]`}>
          {top.hero_image ? (
            <div className="aspect-[16/9] w-full rounded-2xl overflow-hidden bg-zinc-100 mb-3">
              <img src={top.hero_image} alt="" className="w-full h-full object-cover" />
            </div>
          ) : null}
          <p className="text-xs font-semibold text-primary">{top.title}</p>
          <h1 className="text-xl font-bold text-foreground leading-tight mt-0.5">{top.hero_name}</h1>
          {top.pitch ? (
            <p className="text-sm text-foreground/80 mt-2 leading-relaxed whitespace-pre-wrap">{top.pitch}</p>
          ) : null}
        </div>

        <div className="px-4 py-4">
          <p className="text-sm font-semibold text-foreground mb-2">{top.reasons_title}</p>
          <ul className="space-y-2 mb-6">
            {top.reasons.map((r, i) => (
              <li key={i} className="text-sm text-foreground/85 flex gap-2.5 pl-1">
                <Check className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                <span className="leading-relaxed">{r}</span>
              </li>
            ))}
          </ul>

          <p className="text-xs font-semibold text-muted-foreground mb-2">오늘의 동선</p>
          <ol className="space-y-0 border-l-2 border-primary/25 pl-3 ml-0.5 mb-6">
            {top.steps.map((s) => (
              <li key={s.order} className="pb-4 last:pb-0 relative -left-0.5 pl-0">
                <div className="absolute -left-[1.1rem] top-0.5 w-3.5 h-3.5 rounded-full bg-primary text-[10px] text-primary-foreground font-bold flex items-center justify-center">
                  {s.order}
                </div>
                <p className="text-xs font-bold text-primary/90">{s.step_label}</p>
                <p className="text-base font-bold text-foreground leading-snug">{s.name}</p>
                {s.one_line ? (
                  <p className="text-xs text-muted-foreground mt-0.5">{s.one_line}</p>
                ) : null}
              </li>
            ))}
          </ol>

          <div className="pt-4 border-t border-border/40">
            <p className="text-sm font-bold text-foreground">장소별 소개·추천 포인트</p>
            <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed">
              큐레이션·규칙 기반 소개입니다. 평점·리뷰 건수는 Google Places 값이 있으면 표시합니다.
            </p>
            <CourseStepDetailCards steps={top.steps} />
          </div>

          <div className="mt-5 rounded-2xl bg-amber-50/80 border border-amber-100/80 px-3 py-2.5 text-xs text-foreground/85">
            방문 전 운영시간을 확인해 주세요. 일부 정보는 실제와 다를 수 있어요.
          </div>

          <div className="mt-4 flex flex-col gap-2">
            <Button
              type="button"
              className="w-full rounded-2xl font-semibold"
              onClick={() => {
                const key = altIdToCommittedKey(altId)
                const ok = saveConfirmedCourse({
                  resultQueryString: qs,
                  committedCourseAltId: key,
                  recommendPayload: data,
                })
                if (!ok) {
                  window.alert('선택을 저장하지 못했어요. 잠시 후 다시 시도해 주세요.')
                  return
                }
                navigate(`/?${qs}`)
              }}
            >
              이 코스로 진행할게요
            </Button>
            <Button
              type="button"
              variant="outline"
              className="w-full rounded-2xl bg-white font-semibold"
              onClick={() => {
                saveRecommendPayloadForResult(qs, data)
                navigate(`/result/more?${qs}`)
              }}
            >
              다른 코스도 볼까요?
            </Button>
          </div>
        </div>

        <div className="px-4 pb-8">
          <ServiceFooter />
        </div>
      </div>
    </div>
  )
}
