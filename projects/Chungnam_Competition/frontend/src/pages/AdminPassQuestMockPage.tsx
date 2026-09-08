import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { APP_NAME } from '@/config/app'

type MockPayload = {
  total_events?: number
  by_event_type?: Record<string, number>
  sample_tail?: unknown[]
  note?: string
}

/** 발표용: 서버 메모리 로그 집계(재시작 시 초기화). 실제 과금·운영 대시보드는 미구현. */
export default function AdminPassQuestMockPage() {
  const [data, setData] = useState<MockPayload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    document.title = `${APP_NAME} · 운영 목업`
  }, [])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const res = await fetch('/api/admin/pass-quest-mock-stats')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = (await res.json()) as MockPayload
        if (!cancelled) setData(json)
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : '불러오기 실패')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const kpis = [
    { label: '패스퀘스트 조회 수', key: 'pass_quest_view' as const },
    { label: '선택(진행 확정)', key: 'pass_quest_select' as const },
    { label: '대안 전략 조회', key: 'pass_quest_alternative_view' as const },
    { label: '미션 교체 시도', key: 'pass_quest_mission_replace' as const },
  ]

  return (
    <div className="min-h-dvh bg-slate-50 text-slate-900 px-4 py-8 max-w-lg mx-auto">
      <div className="flex items-center justify-between gap-2 mb-6">
        <div>
          <h1 className="text-lg font-extrabold">운영자 지표 목업</h1>
          <p className="text-xs text-slate-600 mt-1 leading-relaxed">
            실시간 가맹 연동이 아닌, 클라이언트 이벤트 로그 샘플입니다. 향후 공식 연계·리포트 과금은
            별도 설계가 필요합니다.
          </p>
        </div>
        <Link to="/" className="text-xs font-semibold text-orange-600 shrink-0">
          홈
        </Link>
      </div>

      {err ? (
        <p className="text-sm text-destructive" role="alert">
          {err}
        </p>
      ) : null}

      <div className="grid grid-cols-2 gap-3">
        {kpis.map(k => (
          <div key={k.key} className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
            <p className="text-[10px] font-semibold text-slate-500">{k.label}</p>
            <p className="text-2xl font-black tabular-nums mt-1">
              {(data?.by_event_type?.[k.key] as number | undefined) ?? 0}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm text-xs text-slate-700 space-y-2">
        <p>
          <span className="font-semibold">총 이벤트:</span> {data?.total_events ?? 0}
        </p>
        <p className="text-slate-500 leading-relaxed">{data?.note}</p>
      </div>

      <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white/70 p-4 text-[11px] text-slate-600 leading-relaxed space-y-2">
        <p className="font-bold text-slate-800">향후 수익·실증 구조(참고)</p>
        <ul className="list-disc pl-4 space-y-1">
          <li>지자체·관광기관 실증형 운영 시나리오</li>
          <li>축제별 패스퀘스트 랜딩(콘텐츠 번들)</li>
          <li>지역상권 제휴 노출·캠페인(공식 데이터 전제)</li>
          <li>관광 인사이트 리포트(익명·집계)</li>
        </ul>
      </div>

      {data?.sample_tail && data.sample_tail.length > 0 ? (
        <details className="mt-6 text-[10px] text-slate-500">
          <summary className="cursor-pointer font-semibold text-slate-700">최근 로그 샘플</summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-xl bg-slate-900 text-slate-100 p-3">
            {JSON.stringify(data.sample_tail, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  )
}
