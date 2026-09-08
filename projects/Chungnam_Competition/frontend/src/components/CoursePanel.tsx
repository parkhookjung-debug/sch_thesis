import { useState } from 'react'
import { MapPin, Star, Clock, ChevronRight, ExternalLink, MessageSquare } from 'lucide-react'
import type { NextPlace } from '@/types'
import type { CourseStep, NextCategory } from '@/hooks/useCourse'
import type { TripDuration } from '@/hooks/useRecommend'

interface Props {
  chain: CourseStep[]
  onSelectCategory: (stepIdx: number, category: NextCategory) => void
  onSelectPlace: (stepIdx: number, place: NextPlace) => void
  onClose: () => void
  tripDuration?: TripDuration
}

const CATEGORY_BUTTONS: { key: NextCategory; label: string; emoji: string }[] = [
  { key: 'restaurant', label: '식당', emoji: '🍽️' },
  { key: 'cafe', label: '카페', emoji: '☕' },
  { key: 'attraction', label: '관광지', emoji: '🗺️' },
]

const STEP_ICONS = ['🌿', '➜', '📍', '🌙']

const TYPE_LABEL: Record<string, string> = {
  restaurant: '식당',
  korean_restaurant: '한식',
  chinese_restaurant: '중식',
  japanese_restaurant: '일식',
  cafe: '카페',
  coffee_shop: '카페',
  bakery: '베이커리',
  tourist_attraction: '관광',
  museum: '박물관',
  park: '공원',
  art_gallery: '미술관',
}

function getTypeLabel(types: string[]): string {
  for (const t of types) {
    if (TYPE_LABEL[t]) return TYPE_LABEL[t]
  }
  return '장소'
}

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLng = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2
  return R * 2 * Math.asin(Math.sqrt(a))
}

function CoursePayloadPanel({ step }: { step: CourseStep }) {
  if (!step.payload?.next_stage) return null

  const stageType = step.payload.next_stage.type ?? ''
  const isMealStage = stageType === 'meal'
  const split = Boolean(step.payload.meta?.indoor_transition_split)
  const showComfortPanels = isMealStage

  return (
    <div className="mb-3 rounded-xl bg-background/80 border border-border/50 p-3 text-sm">
      {(() => {
        const scene = step.payload.next_scene ?? step.payload.next_stage
        const sm = step.payload.scene_mode
        const wmn = step.payload.next_scene?.why_meal_now ?? []
        const hl =
          step.payload.next_step_headline ?? scene.headline ?? scene.title
        const gnotes = step.payload.guided_flow_notes ?? []
        return (
          <>
            <p className="text-[10px] font-bold text-primary tracking-wide">다음 단계 추천</p>
            <p className="text-sm font-extrabold text-foreground leading-snug mt-0.5">{hl}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{scene.title}</p>
            {gnotes.length > 0 && (
              <ul className="mt-2 text-[11px] text-teal-800/90 list-disc pl-4 space-y-0.5">
                {gnotes.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            )}
            <p className="text-[10px] font-bold text-primary mt-2">왜 이렇게 판단했나요?</p>
            <ul className="text-xs text-muted-foreground mt-1 list-disc pl-4 space-y-0.5">
              {(scene.why ?? []).slice(0, 3).map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
            {sm?.title ? (
              <div className="mt-2 pt-2 border-t border-border/30">
                <p className="text-[10px] font-bold text-primary">
                  {split ? '실내 전환 방식' : '다음 장면 방식'}
                </p>
                <p className="text-xs font-bold text-foreground mt-0.5 leading-snug">{sm.title}</p>
                <p className="text-[10px] font-bold text-primary mt-2">왜 이 방식인가요?</p>
                <ul className="text-xs text-muted-foreground mt-1 list-disc pl-4 space-y-0.5">
                  {(sm.why ?? []).slice(0, 3).map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {showComfortPanels && wmn.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/40">
                <p className="text-[11px] font-bold text-primary">왜 지금 식사인가</p>
                <ul className="text-xs text-muted-foreground mt-1 list-disc pl-4 space-y-0.5">
                  {wmn.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )
      })()}
      {showComfortPanels &&
        step.payload.meal_style?.label &&
        step.payload.meal_style.key !== 'none' &&
        step.payload.meal_style.key !== 'cafe_rest' && (
          <div className="mt-3 pt-3 border-t border-border/40">
            <p className="text-xs font-bold text-primary">
              {isMealStage ? '추천 식사 스타일' : '추천 실내 무드'}:{' '}
              <span className="text-foreground">{step.payload.meal_style.label}</span>
            </p>
            {step.payload.meal_style.secondary_key && (
              <p className="text-[10px] text-muted-foreground mt-1">
                보조 스타일:{' '}
                {step.payload.meal_style.secondary_label ?? step.payload.meal_style.secondary_key}
              </p>
            )}
            {(step.payload.meal_style.why?.length ?? 0) > 0 && (
              <>
                <p className="text-[11px] font-bold text-primary mt-2">
                  {isMealStage ? '왜 이 스타일인가' : '왜 이 무드인가'}
                </p>
                <ul className="text-xs text-muted-foreground mt-1 list-disc pl-4 space-y-0.5">
                  {(step.payload.meal_style.why ?? []).slice(0, 4).map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </>
            )}
            {step.payload.cuisine_bias && Object.keys(step.payload.cuisine_bias).length > 0 && (
              <details className="mt-2 text-[10px] text-muted-foreground">
                <summary className="cursor-pointer font-semibold text-primary">요리 편향(보조)</summary>
                <p className="mt-1 leading-relaxed">
                  한 {step.payload.cuisine_bias.korean?.toFixed(2) ?? '-'} · 중{' '}
                  {step.payload.cuisine_bias.chinese?.toFixed(2) ?? '-'} · 일{' '}
                  {step.payload.cuisine_bias.japanese?.toFixed(2) ?? '-'} · 서양{' '}
                  {step.payload.cuisine_bias.western?.toFixed(2) ?? '-'}
                </p>
              </details>
            )}
          </div>
        )}
      {step.payload.primary_recommendation?.name && (
        <div className="mt-3 pt-3 border-t border-border/40">
          <p className="text-[11px] font-bold text-primary mb-1">1순위 추천</p>
          <p className="text-sm font-bold text-foreground">{step.payload.primary_recommendation.name}</p>
          {step.payload.primary_recommendation.data_source_note ? (
            <p className="text-[10px] text-teal-600 mt-1">
              {step.payload.primary_recommendation.data_source_note}
            </p>
          ) : null}
          {step.payload.primary_recommendation.practical_info?.mobility_line && (
            <p className="text-[11px] text-muted-foreground mt-1">
              {step.payload.primary_recommendation.practical_info.mobility_line}
            </p>
          )}
          <details className="mt-1 text-[10px] text-muted-foreground">
            <summary className="cursor-pointer font-semibold text-primary">점수·세부 근거</summary>
            {step.payload.primary_recommendation.score != null && (
              <p className="mt-1">
                내부 참고 점수 {step.payload.primary_recommendation.score.toFixed(1)} / 100
              </p>
            )}
          </details>
          <p className="text-[11px] font-bold text-primary mt-2">
            {isMealStage ? '왜 이 식당인가' : '왜 이 장소인가'}
          </p>
          {step.payload.primary_recommendation.why?.map((w, i) => (
            <p key={i} className="text-xs text-muted-foreground mt-1 leading-relaxed">
              · {w}
            </p>
          ))}
          {!(step.payload.after_this && step.payload.after_this.length > 0) && (
            <>
              <p className="text-[11px] font-bold text-primary mt-2">
                {step.payload.primary_recommendation.after_this_title ?? '이후 이어가기'}
              </p>
              <ul className="text-xs text-muted-foreground mt-1 list-disc pl-4 space-y-0.5">
                {(step.payload.primary_recommendation.after_this ?? []).map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
      {step.payload.alternatives && step.payload.alternatives.length > 0 && (
        <details className="mt-2 pt-2 border-t border-border/30 text-xs">
          <summary className="cursor-pointer font-bold text-primary">다른 선택지 이름만 보기</summary>
          <ul className="text-muted-foreground mt-1 list-disc pl-4 space-y-0.5">
            {step.payload.alternatives.slice(0, 6).map((p, i) => (
              <li key={i}>{p.name}</li>
            ))}
          </ul>
        </details>
      )}
      {step.payload.after_this && step.payload.after_this.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border/40">
          <p className="text-[11px] font-bold text-primary">
            {stageType === 'meal' ? '식사 후 이어가기' : '이후 이어가기'}
          </p>
          <ul className="text-xs text-muted-foreground mt-1 list-disc pl-4 space-y-0.5">
            {step.payload.after_this.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
      {!step.payload.primary_recommendation && step.payload.meta?.fallback_note && (
        <p className="text-xs text-muted-foreground mt-2">{step.payload.meta.fallback_note}</p>
      )}
    </div>
  )
}

function NextPlaceCard({
  place: p,
  isSelected,
  isPrimary,
  originLat,
  originLng,
  onClick,
}: {
  place: NextPlace
  isSelected: boolean
  isPrimary: boolean
  originLat: number
  originLng: number
  onClick: () => void
}) {
  const [showReviews, setShowReviews] = useState(false)
  const typeLabel = getTypeLabel(p.types)
  const km = haversineKm(originLat, originLng, p.lat, p.lng)
  const walkMin = Math.round((km / 5) * 60)
  const carMin = Math.max(1, Math.round((km / 30) * 60))
  const reviews = p.reviews ?? []

  const naverUrl = `https://map.naver.com/p/search/${encodeURIComponent(p.name)}`
  const kakaoUrl = `https://map.kakao.com/link/search/${encodeURIComponent(p.name)}`
  const mapsUrl = p.google_maps?.trim()

  return (
    <div
      className={`bg-white rounded-xl overflow-hidden shadow-sm border transition-all ${
        isSelected
          ? 'border-primary ring-1 ring-primary'
          : isPrimary
            ? 'border-primary border-2'
            : 'border-border/40 hover:border-primary/40'
      }`}
    >
      <div
        role="button"
        tabIndex={0}
        className="flex gap-3 cursor-pointer"
        onClick={onClick}
        onKeyDown={e => e.key === 'Enter' && onClick()}
      >
        <div className="flex-shrink-0 w-20 h-20">
          {p.photo_url ? (
            <img
              src={p.photo_url}
              alt={p.name}
              loading="lazy"
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full bg-muted flex items-center justify-center text-2xl">📍</div>
          )}
        </div>

        <div className="flex-1 py-2.5 pr-3 min-w-0">
          <div className="flex items-start justify-between gap-1 mb-1">
            <div className="min-w-0">
              <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full mr-1">
                {typeLabel}
              </span>
              <span className="text-[13px] font-bold">{p.name}</span>
              {p.public_data_match || p.source_mix === 'merged' ? (
                <span className="block text-[9px] text-teal-600 font-medium mt-0.5">
                  {p.source_mix === 'merged' ? '공공데이터 + 지도 검색 보강' : '공공 관광 데이터 기반 후보'}
                </span>
              ) : null}
            </div>
            {p.open_now !== null && (
              <span
                className={`flex-shrink-0 text-[10px] font-semibold flex items-center gap-0.5 ${
                  p.open_now ? 'text-emerald-600' : 'text-rose-500'
                }`}
              >
                <Clock className="w-2.5 h-2.5" />
                {p.open_now ? '영업중' : '영업종료'}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1 mb-1">
            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
            <span className="text-xs font-bold">{p.rating.toFixed(1)}</span>
            <span className="text-[11px] text-muted-foreground">
              ({p.review_count.toLocaleString()}개)
            </span>
          </div>

          <div className="flex items-center gap-2 text-[10px] text-muted-foreground mb-1 flex-wrap">
            <span className="inline-flex items-center gap-0.5">
              <MapPin className="w-3 h-3 flex-shrink-0" />
              {km < 1 ? `${Math.round(km * 1000)}m` : `${km.toFixed(1)}km`}
            </span>
            <span>🚗 {carMin}분</span>
            <span>🚶 {walkMin}분</span>
          </div>

          {isSelected && (
            <span className="text-[10px] text-primary font-bold">✓ 선택됨</span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1 px-3 py-2 border-t border-border/30 bg-muted/20 flex-wrap">
        {reviews.length > 0 && (
          <button
            type="button"
            onClick={e => {
              e.stopPropagation()
              setShowReviews(v => !v)
            }}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground
                       px-2 py-1 rounded-lg hover:bg-muted transition-colors"
          >
            <MessageSquare className="w-3 h-3" />
            리뷰 {reviews.length}개
          </button>
        )}

        <div className="flex-1 min-w-[1px]" />

        <a
          href={naverUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
          className="text-[11px] px-2 py-1 rounded-lg bg-green-50 text-green-700
                     hover:bg-green-100 transition-colors font-medium"
        >
          N 네이버
        </a>
        <a
          href={kakaoUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
          className="text-[11px] px-2 py-1 rounded-lg bg-yellow-50 text-yellow-700
                     hover:bg-yellow-100 transition-colors font-medium"
        >
          K 카카오
        </a>
        {p.website ? (
          <a
            href={p.website}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="text-[11px] px-2 py-1 rounded-lg bg-blue-50 text-blue-700
                       hover:bg-blue-100 transition-colors font-medium inline-flex items-center gap-0.5"
          >
            <ExternalLink className="w-2.5 h-2.5" />
            홈페이지
          </a>
        ) : null}
        {mapsUrl ? (
          <a
            href={mapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="text-[11px] px-2 py-1 rounded-lg bg-slate-50 text-slate-700
                       hover:bg-slate-100 transition-colors font-medium"
          >
            지도
          </a>
        ) : null}
      </div>

      {showReviews && reviews.length > 0 && (
        <div className="px-3 pb-3 flex flex-col gap-2 border-t border-border/20">
          {reviews.map((r, i) => (
            <div key={i} className="pt-2">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[11px] font-semibold">{r.author}</span>
                <div className="flex">
                  {Array.from({ length: 5 }).map((_, s) => (
                    <Star
                      key={s}
                      className={`w-2.5 h-2.5 ${
                        s < r.rating ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-[10px] text-muted-foreground ml-auto">{r.relative}</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-3">{r.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function CoursePanel({
  chain,
  onSelectCategory,
  onSelectPlace,
  onClose,
  tripDuration = 'half-day',
}: Props) {
  if (chain.length === 0) return null

  const flowHint =
    tripDuration === '2h'
      ? '2시간 일정: 다음은 한 단계만 강하게 이어가요.'
      : tripDuration === 'full-day'
        ? '종일 일정: 쉼·오후·마무리까지 단계를 나눠 볼 수 있어요.'
        : '반나절: 쉬었다가 다음 장면까지 이어가기 좋아요.'

  return (
    <div className="mt-2 mb-4 rounded-2xl border border-primary/20 bg-primary/5 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-primary/10">
        <div className="flex items-center gap-2">
          <ChevronRight className="w-4 h-4 text-primary" />
          <span className="text-sm font-bold text-primary">코스 이어가기 · 다음 장면</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          닫기
        </button>
      </div>
      <p className="text-[10px] text-teal-900/90 px-4 py-2 bg-teal-50/80 border-b border-teal-100">{flowHint}</p>

      <div className="px-4 py-3 flex flex-col gap-4">
        {chain.map((step, stepIdx) => (
          <div key={stepIdx}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-base">{STEP_ICONS[stepIdx % STEP_ICONS.length] ?? '📍'}</span>
              <span className="text-xs font-bold text-foreground">
                {stepIdx + 1}단계 — {step.label}
              </span>
              {stepIdx > 0 && step.places.length > 0 && (
                <span className="text-[10px] text-muted-foreground">(선택한 장소 기준)</span>
              )}
            </div>

            {!step.selectedCategory ? (
              <div className="flex gap-2 mb-1">
                {CATEGORY_BUTTONS.map(({ key, label, emoji }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => onSelectCategory(stepIdx, key)}
                    className="flex-1 flex flex-col items-center gap-1 py-3 rounded-xl
                               bg-white border border-border/50 hover:border-primary/50
                               hover:bg-primary/5 transition-all text-sm font-medium"
                  >
                    <span className="text-xl">{emoji}</span>
                    <span>{label}</span>
                  </button>
                ))}
              </div>
            ) : (
              <>
                {step.selectedCategory && !step.selected && (
                  <div className="flex gap-1.5 mb-3 flex-wrap">
                    {CATEGORY_BUTTONS.map(({ key, label, emoji }) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => onSelectCategory(stepIdx, key)}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold
                                    transition-all border ${
                          step.selectedCategory === key
                            ? 'bg-primary text-white border-primary'
                            : 'bg-white border-border/50 hover:border-primary/40'
                        }`}
                      >
                        {emoji} {label}
                      </button>
                    ))}
                  </div>
                )}

                <CoursePayloadPanel step={step} />

                {step.loading ? (
                  <div className="flex flex-col gap-2">
                    {[1, 2].map(i => (
                      <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
                    ))}
                  </div>
                ) : step.places.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-2 pl-1">
                    {step.payload?.meta?.fallback_note || '근처 장소를 찾지 못했습니다.'}
                  </p>
                ) : (
                  <div className="flex flex-col gap-2">
                    <p className="text-[10px] font-semibold text-muted-foreground pl-1">
                      마음에 들면 그대로, 아니면 한 번에 바꿔 이어가기
                    </p>
                    {step.places[0] && (
                      <NextPlaceCard
                        key={`${step.places[0].name}-0`}
                        place={step.places[0]}
                        isSelected={step.selected?.name === step.places[0].name}
                        isPrimary
                        originLat={step.originLat}
                        originLng={step.originLng}
                        onClick={() => onSelectPlace(stepIdx, step.places[0])}
                      />
                    )}
                    {step.places.length > 1 && (
                      <details className="rounded-xl border border-border/40 bg-background/60">
                        <summary className="cursor-pointer text-[11px] font-bold text-primary px-3 py-2">
                          다른 선택지도 보기 ({step.places.length - 1}곳)
                        </summary>
                        <div className="flex flex-col gap-2 px-2 pb-2 pt-0">
                          {step.places.slice(1).map((p, i) => (
                            <NextPlaceCard
                              key={`${p.name}-${i + 1}`}
                              place={p}
                              isSelected={step.selected?.name === p.name}
                              isPrimary={false}
                              originLat={step.originLat}
                              originLng={step.originLng}
                              onClick={() => onSelectPlace(stepIdx, p)}
                            />
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                )}
              </>
            )}

            {stepIdx < chain.length - 1 && chain[stepIdx].selected && (
              <div className="flex items-center gap-1 mt-3 text-xs text-primary font-medium pl-1">
                <ChevronRight className="w-3.5 h-3.5" />
                {chain[stepIdx].selected!.name} 기준으로 다음 코스
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
