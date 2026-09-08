import { useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useRecommendFromRoute } from '@/hooks/useRecommendFromRoute'
import { toResultQueryString } from '@/lib/tripParams'
import type { AlternativeCourse } from '@/types'
import { CONSUMER_APP_NAME } from '@/config/app'
import { Button } from '@/components/ui/button'
import { appImageSrc } from '@/lib/courseImageFallback'
import {
  MOCK_ALTERNATIVE_CONSUMER,
  alternativeToConsumer,
  mockConsumerAltToAlternative,
  altCourseToTopCourse,
  recommendWithTopCourse,
} from '@/lib/mapRecommendToConsumerCourse'
import type { ConsumerAlternativeCourse } from '@/lib/consumerCourseTypes'
import { Badge } from '@/components/consumer/Badge'
import { saveRecommendPayloadForResult } from '@/lib/recommendSessionCache'
import { LiveStatusBar } from '@/components/consumer/LiveStatusBar'

export default function MoreCoursesPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { form, data, loading, error } = useRecommendFromRoute()
  const qs = toResultQueryString(form)
  const mockMode = searchParams.get('mock') === '1'

  useEffect(() => {
    document.title = `${CONSUMER_APP_NAME} · 다른 코스`
  }, [])

  const rows = useMemo(() => {
    const api = mockMode ? [] : (data?.alternative_courses ?? []).map(a => ({
      kind: 'api' as const,
      api: a,
      card: alternativeToConsumer(a),
    }))
    const need = Math.max(0, 3 - api.length)
    const mockExtras = MOCK_ALTERNATIVE_CONSUMER.filter(
      m => !api.some(a => a.api.id === m.id),
    ).slice(0, need)
    const mockRows = mockExtras.map(m => ({ kind: 'mock' as const, mock: m, card: m }))
    return [...api, ...mockRows]
  }, [data, mockMode])

  function applyAlt(alt: AlternativeCourse) {
    if (!data) return
    const next = recommendWithTopCourse(data, altCourseToTopCourse(alt))
    saveRecommendPayloadForResult(qs, next)
    navigate(`/result?${qs}`, { replace: true })
  }

  function onPick(row: (typeof rows)[number]) {
    if (row.kind === 'api') {
      applyAlt(row.api)
      return
    }
    applyAlt(mockConsumerAltToAlternative(row.mock))
  }

  if (loading && !data && !mockMode) {
    return (
      <div className="consumer-shell items-center justify-center text-[#7b6a5c] font-medium">
        불러오는 중…
      </div>
    )
  }
  if ((error || !data) && !mockMode) {
    return (
      <div className="consumer-shell items-center justify-center px-6 text-[#3a2a20]">
        <p className="text-sm font-medium text-center">{error || '코스를 불러올 수 없어요'}</p>
        <Button type="button" className="mt-4 rounded-xl app-primary-button" onClick={() => navigate(`/result?${qs}`)}>
          돌아가기
        </Button>
      </div>
    )
  }

  return (
    <div className="consumer-shell pb-8">
      <header className="sticky top-0 z-30 border-b consumer-header-blur">
        <LiveStatusBar />
        <div className="flex items-center gap-2 px-3 pb-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex h-11 w-11 items-center justify-center rounded-xl hover:bg-white/90 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-[17px] font-extrabold flex-1 text-center pr-10">다른 코스 보기</h1>
        </div>
      </header>

      <div className="px-5 pt-4 space-y-4">
        {rows.map(row => {
          const c: ConsumerAlternativeCourse = row.card
          const img = appImageSrc(c.heroImage)
          return (
            <article key={c.id} className="consumer-card-elevated overflow-hidden p-0">
              <div className="relative aspect-[16/9] bg-[#f5ede2]">
                <img src={img} alt="" className="w-full h-full object-cover" />
                <span className="absolute left-3 top-3 rounded-full bg-[#fffaf2]/95 px-3 py-1 text-[12px] font-black text-[#9a4528]">
                  {c.typeLabel}
                </span>
              </div>
              <div className="p-4">
                <h2 className="text-[19px] font-black mt-1 leading-snug text-[#2b1b12]">{c.title}</h2>
                <div className="flex flex-wrap gap-2 mt-2">
                  {c.badges.map(b => (
                    <Badge key={b}>{b}</Badge>
                  ))}
                </div>
                <ol className="mt-3 space-y-1.5 text-[14px] font-semibold text-[#5f5146]">
                  {c.stepsPreview.map((s, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="grid h-5 w-5 place-items-center rounded-full bg-[#fff0e9] text-[11px] font-black text-[#c56642]">{i + 1}</span>
                      <span className="min-w-0">
                        <span className="text-[#c56642] font-bold text-[12px]">{s.role}</span>{' '}
                        {s.name}
                      </span>
                    </li>
                  ))}
                </ol>
                <Button
                  type="button"
                  className="w-full mt-4 h-12 rounded-xl font-extrabold app-primary-button border-0"
                  onClick={() => onPick(row)}
                >
                  이 코스로 보기
                </Button>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
