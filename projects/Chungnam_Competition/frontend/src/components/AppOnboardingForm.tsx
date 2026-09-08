import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { DurationFullKind, TripFormState } from '@/lib/tripParams'
import {
  MapPin,
  Users,
  Car,
  Calendar,
  Ticket,
  Sun,
  CalendarDays,
  Bed,
  Luggage,
  Lightbulb,
} from 'lucide-react'
import type { ComponentType, ReactNode } from 'react'

interface Props {
  value: TripFormState
  onChange: (next: TripFormState) => void
  /** 앱 마법사: 지정 시 해당 단계 입력만 표시. 미지정 시 전체(한 화면) */
  wizardStep?: 0 | 1 | 2
}

function Block({
  icon: Icon,
  title,
  children,
}: {
  icon: ComponentType<{ className?: string }>
  title: string
  children: ReactNode
}) {
  return (
    <div className="rounded-[1.35rem] border border-stone-200/90 bg-white/90 p-5 shadow-[0_12px_40px_-16px_rgba(15,23,42,0.12)] ring-1 ring-white/60 backdrop-blur-sm">
      <div className="flex items-center gap-3 mb-4">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500/15 to-sky-500/15 text-stone-800 ring-1 ring-stone-200/80">
          <Icon className="h-5 w-5" />
        </span>
        <span className="text-base font-bold tracking-tight text-stone-900">{title}</span>
      </div>
      {children}
    </div>
  )
}

/**
 * 조건 입력 — `wizardStep`으로 앱식 분할 화면 지원
 */
export default function AppOnboardingForm({ value: f, onChange, wizardStep }: Props) {
  const patch = (p: Partial<TripFormState>) => onChange({ ...f, ...p })

  const setCompanion = (k: TripFormState['companion']) => {
    if (k === 'solo') {
      onChange({ ...f, companion: 'solo', adultCount: '1', childCount: '0' })
      return
    }
    const wasSolo = f.companion === 'solo'
    onChange({
      ...f,
      companion: k,
      adultCount: wasSolo && f.adultCount === '1' ? '2' : f.adultCount,
    })
  }

  const isSolo = f.companion === 'solo'
  const isWizard = wizardStep !== undefined
  const show = (n: 0 | 1 | 2) => !isWizard || wizardStep === n

  function regionSubline(city: string) {
    if (city === '전체') return '모든 시·군을 포함합니다'
    return `${city} 시·군 기준으로 후보를 맞춥니다`
  }

  function durationTileSelected(tile: '1d' | 'half' | '1n2d' | '2n3d') {
    if (tile === 'half') return f.tripDuration === 'half-day'
    if (tile === '1d') return f.tripDuration === 'full-day' && f.durationFullKind === '1d'
    if (tile === '1n2d') return f.tripDuration === 'full-day' && f.durationFullKind === '1n2d'
    return f.tripDuration === 'full-day' && f.durationFullKind === '2n3d'
  }

  function setDurationTile(tile: '1d' | 'half' | '1n2d' | '2n3d') {
    if (tile === 'half') {
      patch({ tripDuration: 'half-day', durationFullKind: '1d' })
      return
    }
    const kind: DurationFullKind = tile === '1d' ? '1d' : tile === '1n2d' ? '1n2d' : '2n3d'
    patch({ tripDuration: 'full-day', durationFullKind: kind })
  }

  return (
    <div className="space-y-5">
      {show(0) ? (
        <div className="space-y-2">
          <p className="text-[15px] font-extrabold text-stone-900 tracking-tight">1. 지역 선택</p>
          <Select value={f.city ?? undefined} onValueChange={v => patch({ city: v ?? '전체' })}>
            <SelectTrigger className="h-auto min-h-[5.25rem] w-full max-w-none rounded-2xl border border-stone-200 bg-white px-4 py-3.5 text-left shadow-[0_10px_36px_-14px_rgba(15,23,42,0.14)] ring-1 ring-stone-900/[0.03]">
              <div className="flex w-full min-w-0 flex-1 items-center gap-3 pr-1">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-orange-100 text-orange-600">
                  <MapPin className="h-5 w-5" strokeWidth={2.25} />
                </span>
                <div className="min-w-0 flex-1 text-left">
                  <SelectValue className="text-[16px] font-bold leading-tight text-stone-900 data-placeholder:text-stone-400" />
                  <p className="text-[13px] text-stone-500 mt-1 leading-snug">{regionSubline(f.city)}</p>
                </div>
              </div>
            </SelectTrigger>
            <SelectContent>
              {[
                '전체', '아산', '공주', '보령', '서산', '논산', '부여', '당진', '태안', '홍성',
                '천안', '금산', '서천', '예산', '청양',
              ].map(c => (
                <SelectItem key={c} value={c}>
                  {c === '전체' ? '충청남도 전체' : `충청남도 ${c}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      ) : null}

      {show(0) ? (
        <div className="space-y-3">
          <p className="text-[15px] font-extrabold text-stone-900 tracking-tight">2. 여행 기간 선택</p>
          <div className="grid grid-cols-2 gap-3">
            {(
              [
                ['1d', Sun, '1일'] as const,
                ['half', CalendarDays, '반나절'] as const,
                ['1n2d', Bed, '1박 2일'] as const,
                ['2n3d', Luggage, '2박 3일'] as const,
              ] as const
            ).map(([key, Icon, label]) => {
              const sel = durationTileSelected(key)
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setDurationTile(key)}
                  className={`flex min-h-[4.75rem] flex-col items-center justify-center gap-2 rounded-2xl border-2 px-3 py-3 text-[15px] font-bold transition active:scale-[0.98] ${
                    sel
                      ? 'border-orange-500 bg-gradient-to-b from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/35'
                      : 'border-stone-200 bg-white text-stone-700 shadow-sm hover:border-stone-300'
                  }`}
                >
                  <Icon className={`h-6 w-6 ${sel ? 'text-white' : 'text-orange-500'}`} strokeWidth={2} />
                  {label}
                </button>
              )
            })}
          </div>
          <div className="mt-4 flex gap-3 rounded-2xl border border-stone-200/90 bg-stone-100/80 px-4 py-3.5">
            <Lightbulb className="mt-0.5 h-5 w-5 shrink-0 text-orange-500" strokeWidth={2.25} />
            <div>
              <p className="text-sm font-bold text-stone-900 leading-snug">여행 기간에 맞는 최적의 코스를 추천해드려요</p>
              <p className="text-xs text-stone-600 mt-1.5 leading-relaxed">
                선택한 기간에 맞춰 이동 동선과 소요 시간을 고려합니다.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {show(1) ? (
      <Block icon={Users} title="누구랑·무엇을?">
        <div className="space-y-2.5">
          <div>
            <p className="text-xs text-stone-500 font-semibold mb-2 uppercase tracking-wide">동행</p>
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ['solo', '1인'],
                  ['couple', '커플'],
                  ['family', '가족'],
                  ['friends', '친구'],
                ] as const
              ).map(([k, label]) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setCompanion(k)}
                  className={`min-h-12 rounded-2xl px-5 text-[15px] font-bold border-2 transition ${
                    f.companion === k
                      ? 'border-orange-500 bg-orange-500/10 text-orange-950 shadow-sm'
                      : 'border-stone-200 bg-white text-stone-600 hover:border-stone-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs text-stone-500 font-semibold mb-2 uppercase tracking-wide">목적</p>
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ['healing', '힐링'],
                  ['photo', '사진'],
                  ['walking', '걷기'],
                  ['indoor', '실내'],
                  ['culture', '문화'],
                  ['kids', '키즈'],
                ] as const
              ).map(([k, label]) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => patch({ tripGoal: k })}
                  className={`min-h-11 rounded-2xl px-4 text-sm font-bold border-2 ${
                    f.tripGoal === k
                      ? 'border-violet-500 bg-violet-500/10 text-violet-950'
                      : 'border-stone-200 bg-white text-stone-600 hover:border-stone-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Block>
      ) : null}

      {show(0) ? (
      <div className="rounded-[1.35rem] border border-stone-200/90 bg-white p-5 shadow-[0_12px_40px_-16px_rgba(15,23,42,0.1)] ring-1 ring-white/60">
        <div className="flex items-center gap-3 mb-4">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500/12 to-sky-500/12 text-stone-800 ring-1 ring-stone-200/80">
            <Calendar className="h-5 w-5" />
          </span>
          <span className="text-base font-bold tracking-tight text-stone-900">3. 날짜·시간</span>
        </div>
        <div className="space-y-2.5">
          <div>
            <p className="text-xs text-stone-500 font-semibold mb-2">현재 시각</p>
            <input
              type="time"
              value={f.currentTime}
              onChange={e => patch({ currentTime: e.target.value })}
              className="h-14 w-full rounded-2xl border border-stone-200 px-4 text-[16px] font-semibold bg-white shadow-inner shadow-stone-900/5"
            />
          </div>
          <div>
            <p className="text-xs text-stone-500 font-semibold mb-2">방문 날짜</p>
            <input
              type="date"
              value={f.currentDate}
              onChange={e => patch({ currentDate: e.target.value })}
              className="h-14 w-full rounded-2xl border border-stone-200 px-4 text-[16px] font-semibold bg-white shadow-inner shadow-stone-900/5"
            />
          </div>
          <div>
            <p className="text-xs text-stone-500 font-semibold mb-2">식사 선호 (선택)</p>
            <Select
              value={f.mealPreference}
              onValueChange={v => patch({ mealPreference: v ?? 'none' })}
            >
              <SelectTrigger className="h-14 rounded-2xl text-[15px] font-semibold w-full border-stone-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">특별 없음</SelectItem>
                <SelectItem value="가볍게">가볍게 · 브런치</SelectItem>
                <SelectItem value="한식">한식 위주</SelectItem>
                <SelectItem value="해산물">해산물</SelectItem>
                <SelectItem value="빠르게">빠르게</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
      ) : null}

      {show(2) ? (
      <Block icon={Ticket} title="투어패스 활용 (선택)">
        <p className="text-sm text-stone-600 leading-relaxed mb-4">
          패스가 없어도 그대로 이용할 수 있어요. 켜면 활용 가능성·시간권 적합도를 참고한{' '}
          <strong className="text-stone-900">미션형 패스퀘스트</strong>로 결과가 보강됩니다.
        </p>
        <div className="flex items-center justify-between gap-4 mb-4 py-2">
          <span className="text-[17px] font-bold text-stone-900">투어패스 활용 모드</span>
          <button
            type="button"
            role="switch"
            aria-checked={f.tourpassMode}
            onClick={() => patch({ tourpassMode: !f.tourpassMode })}
            className={`relative h-10 w-16 shrink-0 rounded-full border-2 transition shadow-inner ${
              f.tourpassMode
                ? 'bg-gradient-to-r from-orange-500 to-rose-500 border-orange-400'
                : 'bg-stone-100 border-stone-200'
            }`}
          >
            <span
              className={`absolute top-1 h-7 w-7 rounded-full bg-white shadow-md transition-all ${
                f.tourpassMode ? 'left-[calc(100%-1.9rem)]' : 'left-1'
              }`}
            />
          </button>
        </div>

        <div className={f.tourpassMode ? 'space-y-3 opacity-100' : 'space-y-3 opacity-45 pointer-events-none'}>
          <div>
            <p className="text-xs text-stone-500 font-semibold mb-2">보유·구매 예정</p>
            <Select
              value={f.purchasedStatus}
              onValueChange={v => patch({ purchasedStatus: (v ?? 'not_planned') as typeof f.purchasedStatus })}
            >
              <SelectTrigger className="h-14 rounded-2xl text-[15px] font-semibold w-full border-stone-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="already_have">이미 보유</SelectItem>
                <SelectItem value="considering">구매 검토 중</SelectItem>
                <SelectItem value="not_planned">당장 계획 없음</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <p className="text-xs text-stone-500 font-semibold mb-2">시간권 유형</p>
            <Select
              value={f.tourpassTicketType}
              onValueChange={v => patch({ tourpassTicketType: (v ?? 'none') as typeof f.tourpassTicketType })}
            >
              <SelectTrigger className="h-14 rounded-2xl text-[15px] font-semibold w-full border-stone-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">해당 없음·미정</SelectItem>
                <SelectItem value="24h">24시간권</SelectItem>
                <SelectItem value="36h">36시간권</SelectItem>
                <SelectItem value="48h">48시간권</SelectItem>
                <SelectItem value="single">단일 시설형</SelectItem>
                <SelectItem value="theme">테마·지역 권종</SelectItem>
                <SelectItem value="undecided">아직 미정</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <p className="text-xs text-stone-500 font-semibold mb-2">혜택 중심 추천</p>
            <Select
              value={f.benefitPriority}
              onValueChange={v => patch({ benefitPriority: (v ?? 'none') as typeof f.benefitPriority })}
            >
              <SelectTrigger className="h-14 rounded-2xl text-[15px] font-semibold w-full border-stone-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">특별히 강조 안 함</SelectItem>
                <SelectItem value="balanced">균형</SelectItem>
                <SelectItem value="high">혜택 가능성 우선(보조)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <p className="text-xs text-stone-500 font-semibold mb-3">패스퀘스트 목표</p>
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ['rainy_day_safe', '비 대비'],
                  ['benefit_first', '혜택 우선'],
                  ['food_cafe_linked', '식당·카페'],
                  ['family_friendly', '가족'],
                  ['short_trip', '짧게'],
                  ['experience_focused', '체험·미식'],
                  ['festival_linked', '축제'],
                ] as const
              ).map(([k, label]) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => patch({ passGoal: k })}
                  className={`min-h-11 rounded-2xl px-4 text-sm font-bold border-2 ${
                    f.passGoal === k
                      ? 'border-orange-500 bg-orange-500/10 text-orange-950'
                      : 'border-stone-200 bg-white text-stone-600'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Block>
      ) : null}

      {show(2) ? (
      <Block icon={Car} title={isSolo ? '이동 수단' : '이동·인원'}>
        <div className={isSolo ? 'space-y-0' : 'grid grid-cols-2 gap-2'}>
          <div>
            {!isSolo && (
              <p className="text-xs text-stone-500 font-semibold mb-1.5">이동</p>
            )}
            <Select value={f.transport ?? undefined} onValueChange={v => patch({ transport: v ?? 'car' })}>
              <SelectTrigger className="h-14 rounded-2xl text-[15px] font-semibold w-full border-stone-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="car">자가용</SelectItem>
                <SelectItem value="public">대중교통</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {!isSolo && (
            <>
              <div>
                <p className="text-xs text-stone-500 font-semibold mb-1.5">성인</p>
                <Select value={f.adultCount ?? undefined} onValueChange={v => patch({ adultCount: v ?? '2' })}>
                  <SelectTrigger className="h-14 rounded-2xl text-[15px] font-semibold border-stone-200">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1명</SelectItem>
                    <SelectItem value="2">2명</SelectItem>
                    <SelectItem value="3">3명</SelectItem>
                    <SelectItem value="4">4명</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-2">
                <p className="text-xs text-stone-500 font-semibold mb-1.5">어린이</p>
                <div className="flex flex-wrap gap-1.5">
                  {(['0', '1', '2', '3'] as const).map(n => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => patch({ childCount: n })}
                      className={`h-12 min-w-12 rounded-xl text-sm font-bold ${
                        f.childCount === n
                          ? 'bg-stone-900 text-white shadow-md'
                          : 'bg-stone-100 text-stone-600'
                      }`}
                    >
                      {n}명
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </Block>
      ) : null}
    </div>
  )
}
