import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Loader2, MapPin } from 'lucide-react'
import type { CourseContinuationResponse, RecommendResponse } from '@/types'
import { buildCourseUrl, fetchCoursePayload } from '@/lib/courseClient'
import { commitReplaceStepInRecommend } from '@/lib/commitReconfigureCourse'
import { mergeSyncedPassQuest } from '@/lib/passQuestSync'
import { reconfigureContextForTag, type ReconfigureTag } from '@/lib/reconfigureBias'
import {
  categoryForPlaceName,
  coordsForPlaceName,
  FALLBACK_COORDS,
  rowForPlaceName,
} from '@/lib/recommendGeo'
import { toResultQueryString, tripFormFromSearchParams } from '@/lib/tripParams'
import { Button } from '@/components/ui/button'
import ServiceFooter from '@/components/ServiceFooter'
import { CONSUMER_APP_NAME } from '@/config/app'
import { loadConfirmedCourse, saveConfirmedCourse } from '@/lib/confirmedCourseStorage'
import { resolveTopCourseForDetail } from '@/lib/resolveTopCourse'
import { consumerStepLabel, clientTimeBand } from '@/lib/stepRoleLabels'
import { loadRecommendPayloadForResult, saveRecommendPayloadForResult } from '@/lib/recommendSessionCache'

const HINTS: { label: string; value: Exclude<ReconfigureTag, ''> }[] = [
  { label: '더 실내 중심', value: 'indoor' },
  { label: '더 맛집 중심', value: 'meal' },
  { label: '더 카페·휴식', value: 'cafe' },
  { label: '더 사진 중심', value: 'photo' },
  { label: '더 이동 짧게', value: 'compact' },
  { label: '투어패스 후보 우선', value: 'tourpass' },
  { label: '아이 동반', value: 'kids' },
]

export type ReconfigureLocationState = {
  data: RecommendResponse
  committedSelectionAltId?: string | null
}

type Phase = 'select-step' | 'direction' | 'preview'

export default function ReconfigureCoursePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const form = useMemo(() => tripFormFromSearchParams(searchParams), [searchParams])
  const qs = toResultQueryString(form)

  const navState = location.state as ReconfigureLocationState | null
  const spKey = searchParams.toString()
  const dataFromSession = useMemo(
    () => (navState?.data ? null : loadRecommendPayloadForResult(searchParams)),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- searchParams identity; spKey로 URL 변화만 추적
    [navState?.data, spKey],
  )
  const data = navState?.data ?? dataFromSession
  const baselineRef = useRef<RecommendResponse | null>(null)
  if (data && baselineRef.current === null) {
    baselineRef.current = JSON.parse(JSON.stringify(data)) as RecommendResponse
  }

  const storage = loadConfirmedCourse()
  const committedAltId = useMemo(() => {
    if (navState?.committedSelectionAltId !== undefined) {
      return navState.committedSelectionAltId
    }
    if (storage?.resultQueryString === qs) {
      return storage.committedCourseAltId
    }
    return null
  }, [navState?.committedSelectionAltId, storage?.committedCourseAltId, storage?.resultQueryString, qs])

  const courseToEdit = useMemo(
    () => (data ? resolveTopCourseForDetail(data, committedAltId) : undefined),
    [data, committedAltId],
  )

  const passMode = Boolean(data?.pass_quest?.enabled)
  const stepWord = passMode ? '미션' : '단계'

  const [phase, setPhase] = useState<Phase>('select-step')
  const [selectedStepIndex, setSelectedStepIndex] = useState<number | null>(null)
  const [hint, setHint] = useState<ReconfigureTag>('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [result, setResult] = useState<CourseContinuationResponse | null>(null)

  useEffect(() => {
    if (!courseToEdit?.steps?.length) return
    setSelectedStepIndex(i => {
      if (i != null && i < courseToEdit.steps.length) return i
      return 0
    })
  }, [courseToEdit])

  useEffect(() => {
    const titles: Record<Phase, string> = {
      'select-step': `${CONSUMER_APP_NAME} · 단계 선택`,
      direction: `${CONSUMER_APP_NAME} · 바꿀 방향`,
      preview: `${CONSUMER_APP_NAME} · 확인`,
    }
    document.title = titles[phase]
  }, [phase, stepWord])

  useEffect(() => {
    if (!data || !courseToEdit?.steps?.length) {
      navigate(`/?${qs}`, { replace: true })
    }
  }, [data, courseToEdit, navigate, qs])

  if (!data || !courseToEdit?.steps?.length) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-slate-950 text-slate-400 text-sm">
        이동 중…
      </div>
    )
  }

  const editingCourse = courseToEdit
  const tripData = data

  const hour = new Date().getHours()
  const timeBand = clientTimeBand(hour)

  async function runReplaceFetch(stepIdx: number) {
    const step = editingCourse.steps[stepIdx]
    if (!step) return
    setErr(null)
    setLoading(true)
    if (phase !== 'preview') setResult(null)
    try {
      const coords = coordsForPlaceName(tripData, step.name) ?? FALLBACK_COORDS
      const category = categoryForPlaceName(tripData, step.name)
      const row = rowForPlaceName(tripData, step.name)
      const biasCtx = reconfigureContextForTag(hint)
      const stepRole = String(step.step_role || 'secondary_spot')
      const ctx = {
        weather: tripData.weather,
        duration: form.tripDuration,
        companion: form.companion,
        trip_goal: form.tripGoal,
        transport: form.transport,
        adult_count: form.adultCount,
        child_count: form.childCount,
        coursePath: 'ai' as const,
        spotName: step.name,
        spotId: row?.id,
        mlNextSceneAssist: true,
        replaceStep: true,
        stepIndex: stepIdx,
        stepRole,
        timeBand,
        courseIdForEdit: editingCourse.course_id ?? editingCourse.id,
        ...biasCtx,
      }
      if (import.meta.env.DEV) {
        const url = buildCourseUrl(coords.lat, coords.lng, category, hour, ctx)
        // eslint-disable-next-line no-console
        console.debug('[reconfigure step]', url)
      }
      const payload = await fetchCoursePayload(coords.lat, coords.lng, category, hour, ctx)
      setResult(payload)
      setPhase('preview')
    } catch (e) {
      setErr(e instanceof Error ? e.message : '요청에 실패했어요.')
    } finally {
      setLoading(false)
    }
  }

  function handleHeaderBack() {
    if (phase === 'preview') {
      setResult(null)
      setPhase('direction')
      return
    }
    if (phase === 'direction') {
      setPhase('select-step')
      return
    }
    saveRecommendPayloadForResult(qs, tripData)
    navigate(`/result?${qs}`)
  }

  async function reflectPreview() {
    if (!result || selectedStepIndex == null) return
    const removeId =
      storage?.resultQueryString === qs && storage.committedCourseAltId
        ? storage.committedCourseAltId
        : null
    let merged = commitReplaceStepInRecommend(tripData, result, selectedStepIndex, hint, editingCourse, {
      removeAlternativeId: removeId,
    })
    if (tripData.pass_quest?.enabled) {
      setErr(null)
      try {
        merged = await mergeSyncedPassQuest(merged, form)
      } catch (e) {
        setErr(e instanceof Error ? e.message : '패스퀘스트 점수를 다시 맞추지 못했어요.')
        return
      }
    }
    const ok = saveConfirmedCourse({
      resultQueryString: qs,
      committedCourseAltId: null,
      recommendPayload: merged,
    })
    if (!ok) {
      setErr('반영 내용을 저장하지 못했어요. 잠시 후 다시 시도해 주세요.')
      return
    }
    saveRecommendPayloadForResult(qs, merged)
    navigate(`/result?${qs}`)
  }

  const headerTitle =
    phase === 'select-step'
      ? passMode
        ? '미션 수정'
        : '코스 수정하기'
      : phase === 'direction'
        ? '수정 방향'
        : '미리보기'

  const selectedStep =
    selectedStepIndex != null ? editingCourse.steps[selectedStepIndex] : null

  return (
    <div className="consumer-shell">
      <div className="pt-[max(0.35rem,env(safe-area-inset-top))] pl-1 pr-3 h-[3.25rem] flex items-center justify-between border-b consumer-header-blur">
        <button
          type="button"
          onClick={handleHeaderBack}
          className="inline-flex items-center gap-1 text-[15px] font-bold text-stone-800 pl-2 py-2"
        >
          <ArrowLeft className="w-5 h-5" />
          뒤로
        </button>
        <span className="text-[15px] font-extrabold text-stone-900">{headerTitle}</span>
        <span className="w-10" />
      </div>

      <div className="flex-1 px-4 py-5 pb-28">
        {phase === 'select-step' && (
          <>
            <h2 className="text-base font-bold text-foreground">어떤 {stepWord}를 수정할까요?</h2>
            <p className="text-sm text-foreground/80 mt-2 leading-relaxed">
              바꾸고 싶은 장소가 있는 {stepWord}만 골라 주세요. 코스 전체가 아니라 그 {stepWord}만 다시
              추천받아요.
            </p>
            <div className="mt-5 space-y-3">
              {editingCourse.steps.map((s, idx) => {
                const selected = idx === selectedStepIndex
                const roleL = consumerStepLabel(s.step_role)
                return (
                  <button
                    key={`${s.order}-${s.name}-${idx}`}
                    type="button"
                    onClick={() => setSelectedStepIndex(idx)}
                    className={`w-full text-left rounded-2xl border p-4 transition shadow-sm ${
                      selected
                        ? 'border-primary bg-primary/5 ring-2 ring-primary/25'
                        : 'border-border/50 bg-white'
                    }`}
                  >
                    <p className="text-[11px] font-semibold text-primary">
                      {idx + 1}번째 {stepWord} · {roleL}
                    </p>
                    <p className="text-sm font-bold text-foreground mt-1 leading-snug">{s.name}</p>
                    {s.one_line ? (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{s.one_line}</p>
                    ) : null}
                  </button>
                )
              })}
            </div>
            <Button
              type="button"
              className="w-full mt-6 rounded-2xl font-semibold"
              disabled={selectedStepIndex == null}
              onClick={() => setPhase('direction')}
            >
              다음
            </Button>
          </>
        )}

        {phase === 'direction' && selectedStep != null && selectedStepIndex != null && (
          <>
            <h2 className="text-base font-bold text-foreground">어떤 방향으로 바꿔볼까요?</h2>
            <p className="text-sm text-foreground/80 mt-2 leading-relaxed">
              수정할 {stepWord}:{' '}
              <strong className="text-foreground">
                {selectedStepIndex + 1}번째 · {consumerStepLabel(selectedStep.step_role)} ·{' '}
                {selectedStep.name}
              </strong>
            </p>

            <p className="text-xs font-semibold text-muted-foreground mt-5 mb-2">방향 선택</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setHint('')}
                className={`text-xs font-medium px-3 py-2 rounded-full border transition ${
                  hint === ''
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white text-foreground/80 border-border/60'
                }`}
              >
                지금 흐름에 맡기기
              </button>
              {HINTS.map(h => (
                <button
                  key={h.value}
                  type="button"
                  onClick={() => setHint(h.value)}
                  className={`text-xs font-medium px-3 py-2 rounded-full border transition ${
                    hint === h.value
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-white text-foreground/80 border-border/60'
                  }`}
                >
                  {h.label}
                </button>
              ))}
            </div>

            <Button
              type="button"
              className="w-full mt-6 rounded-2xl font-semibold"
              disabled={loading}
              onClick={() => void runReplaceFetch(selectedStepIndex)}
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  후보를 불러오는 중…
                </span>
              ) : (
                '다시 추천받기'
              )}
            </Button>
          </>
        )}

        {err && (
          <p className="text-sm text-destructive mt-4" role="alert">
            {err}
          </p>
        )}

        {phase === 'preview' && result && selectedStep != null && selectedStepIndex != null && (
          <div className="space-y-4 rounded-2xl border border-border/40 bg-white p-4 shadow-sm">
            <div>
              <p className="text-[10px] font-bold text-primary/90 uppercase tracking-wide">
                이렇게 다시 추천했어요
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {selectedStepIndex + 1}단계 교체 · {consumerStepLabel(selectedStep.step_role)}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-bold text-primary/90 uppercase tracking-wide">
                이어갈 흐름
              </p>
              <p className="text-base font-bold text-foreground mt-0.5">{result.next_stage?.title}</p>
              {result.next_stage?.headline ? (
                <p className="text-sm text-foreground/75 mt-1">{result.next_stage.headline}</p>
              ) : null}
            </div>
            {result.primary_recommendation?.name && (
              <div className="rounded-xl border border-border/50 bg-zinc-50/80 px-3 py-3">
                <p className="text-[10px] font-semibold text-muted-foreground">새로 제안한 장소</p>
                <p className="text-sm font-bold text-foreground mt-1">
                  {result.primary_recommendation.name}
                </p>
                {result.primary_recommendation.address ? (
                  <p className="text-xs text-muted-foreground mt-1 flex gap-1">
                    <MapPin className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    {result.primary_recommendation.address}
                  </p>
                ) : null}
              </div>
            )}
            {result.alternatives && result.alternatives.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2">함께 볼 만한 후보</p>
                <ul className="space-y-2">
                  {result.alternatives.slice(0, 5).map(p => (
                    <li key={`${p.name}-${p.lat}`} className="text-xs flex gap-1.5 text-foreground/90">
                      <MapPin className="w-3.5 h-3.5 shrink-0 text-primary/80" />
                      {p.name}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex flex-col gap-2 pt-2">
              <Button
                type="button"
                className="w-full rounded-2xl font-semibold"
                onClick={() => void reflectPreview()}
              >
                이 변경 반영하기
              </Button>
              <Button
                type="button"
                variant="secondary"
                className="w-full rounded-2xl font-semibold"
                disabled={loading}
                onClick={() => {
                  setResult(null)
                  setPhase('direction')
                }}
              >
                다시 수정하기
              </Button>
              <Button
                type="button"
                variant="outline"
                className="w-full rounded-2xl font-semibold"
                disabled={loading}
                onClick={() => void runReplaceFetch(selectedStepIndex)}
              >
                다시 추천받기
              </Button>
              <Button
                type="button"
                variant="outline"
                className="w-full rounded-2xl font-semibold"
                onClick={() => {
                  const baseline = baselineRef.current ?? tripData
                  saveRecommendPayloadForResult(qs, baseline)
                  navigate(`/result?${qs}`)
                }}
              >
                원래 코스로 돌아가기
              </Button>
            </div>
          </div>
        )}

        <div className="mt-10">
          <ServiceFooter />
        </div>
      </div>
    </div>
  )
}
