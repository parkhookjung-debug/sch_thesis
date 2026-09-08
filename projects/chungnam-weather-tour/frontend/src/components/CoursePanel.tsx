import { useState } from 'react'
import { MapPin, Star, Clock, ChevronRight, ExternalLink, MessageSquare } from 'lucide-react'
import type { NextPlace } from '@/types'
import type { CourseStep, NextCategory } from '@/hooks/useCourse'

interface Props {
  chain: CourseStep[]
  onSelectCategory: (stepIdx: number, category: NextCategory) => void
  onSelectPlace: (stepIdx: number, place: NextPlace) => void
  onClose: () => void
}

const CATEGORY_BUTTONS: { key: NextCategory; label: string; emoji: string }[] = [
  { key: 'restaurant', label: '식당',   emoji: '🍽️' },
  { key: 'cafe',       label: '카페',   emoji: '☕' },
  { key: 'attraction', label: '관광지', emoji: '🗺️' },
]

const TYPE_LABEL: Record<string, string> = {
  restaurant: '식당', korean_restaurant: '한식', chinese_restaurant: '중식',
  japanese_restaurant: '일식', cafe: '카페', coffee_shop: '카페',
  bakery: '베이커리', tourist_attraction: '관광', museum: '박물관',
  park: '공원', art_gallery: '미술관',
}

function getTypeLabel(types: string[]): string {
  for (const t of types) if (TYPE_LABEL[t]) return TYPE_LABEL[t]
  return '장소'
}

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.asin(Math.sqrt(a))
}

export default function CoursePanel({ chain, onSelectCategory, onSelectPlace, onClose }: Props) {
  if (chain.length === 0) return null

  return (
    <div className="mt-2 mb-4 rounded-2xl border border-primary/20 bg-primary/5 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-primary/10">
        <div className="flex items-center gap-2">
          <ChevronRight className="w-4 h-4 text-primary" />
          <span className="text-sm font-bold text-primary">코스 추천</span>
        </div>
        <button onClick={onClose} className="text-xs text-muted-foreground hover:text-foreground">
          닫기
        </button>
      </div>

      <div className="px-4 py-3 flex flex-col gap-5">
        {chain.map((step, stepIdx) => (
          <StepSection
            key={stepIdx}
            step={step}
            stepIdx={stepIdx}
            onSelectCategory={onSelectCategory}
            onSelectPlace={onSelectPlace}
          />
        ))}
      </div>
    </div>
  )
}

function StepSection({
  step, stepIdx, onSelectCategory, onSelectPlace,
}: {
  step: CourseStep
  stepIdx: number
  onSelectCategory: (i: number, c: NextCategory) => void
  onSelectPlace: (i: number, p: NextPlace) => void
}) {
  return (
    <div>
      {/* 단계 헤더 */}
      <p className="text-xs font-bold text-foreground mb-2">
        {stepIdx + 2}번 코스
        {step.selected && (
          <span className="font-normal text-muted-foreground ml-1">
            — {step.selected.name} 선택됨 ✓
          </span>
        )}
      </p>

      {/* 카테고리 선택 버튼 */}
      {!step.selectedCategory && (
        <div className="flex gap-2 mb-3">
          {CATEGORY_BUTTONS.map(({ key, label, emoji }) => (
            <button
              key={key}
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
      )}

      {/* 다른 카테고리 선택 버튼 (선택 후) */}
      {step.selectedCategory && !step.selected && (
        <div className="flex gap-1.5 mb-3">
          {CATEGORY_BUTTONS.map(({ key, label, emoji }) => (
            <button
              key={key}
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

      {/* 로딩 */}
      {step.loading && (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      )}

      {/* 장소 목록 */}
      {!step.loading && step.selectedCategory && step.places.length === 0 && (
        <p className="text-sm text-muted-foreground py-2">근처 장소를 찾지 못했습니다.</p>
      )}
      {!step.loading && step.places.length > 0 && (
        <div className="flex flex-col gap-2">
          {step.places.map((p, i) => (
            <NextPlaceCard
              key={i}
              place={p}
              isSelected={step.selected?.name === p.name}
              originLat={step.originLat}
              originLng={step.originLng}
              onClick={() => onSelectPlace(stepIdx, p)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function NextPlaceCard({
  place: p, isSelected, originLat, originLng, onClick,
}: {
  place: NextPlace
  isSelected: boolean
  originLat: number
  originLng: number
  onClick: () => void
}) {
  const [showReviews, setShowReviews] = useState(false)
  const typeLabel = getTypeLabel(p.types)
  const km = haversineKm(originLat, originLng, p.lat, p.lng)
  const walkMin = Math.round(km / 5 * 60)
  const carMin = Math.max(1, Math.round(km / 30 * 60))

  const naverUrl = `https://map.naver.com/p/search/${encodeURIComponent(p.name)}`
  const kakaoUrl = `https://map.kakao.com/link/search/${encodeURIComponent(p.name)}`

  return (
    <div className={`bg-white rounded-xl overflow-hidden shadow-sm border transition-all ${
      isSelected ? 'border-primary ring-1 ring-primary' : 'border-border/40'
    }`}>
      {/* 메인 카드 행 */}
      <div className="flex gap-3 cursor-pointer" onClick={onClick}>
        {/* 썸네일 */}
        <div className="flex-shrink-0 w-20 h-24">
          {p.photo_url ? (
            <img src={p.photo_url} alt={p.name} loading="lazy" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-muted flex items-center justify-center text-2xl">🍽️</div>
          )}
        </div>

        {/* 정보 */}
        <div className="flex-1 py-2.5 pr-2 min-w-0">
          <div className="flex items-start justify-between gap-1 mb-1">
            <div className="min-w-0">
              <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full mr-1">
                {typeLabel}
              </span>
              <span className="text-[13px] font-bold">{p.name}</span>
            </div>
            {p.open_now !== null && (
              <span className={`flex-shrink-0 text-[10px] font-semibold flex items-center gap-0.5 ${
                p.open_now ? 'text-emerald-600' : 'text-rose-500'
              }`}>
                <Clock className="w-2.5 h-2.5" />
                {p.open_now ? '영업중' : '영업종료'}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1 mb-1">
            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
            <span className="text-xs font-bold">{p.rating.toFixed(1)}</span>
            <span className="text-[11px] text-muted-foreground">({p.review_count.toLocaleString()}개)</span>
          </div>

          {/* 거리 + 이동시간 */}
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground mb-1">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span>{km < 1 ? `${Math.round(km * 1000)}m` : `${km.toFixed(1)}km`}</span>
            <span>🚗 {carMin}분</span>
            <span>🚶 {walkMin}분</span>
          </div>

          {isSelected && (
            <span className="text-[10px] text-primary font-bold">✓ 선택됨</span>
          )}
        </div>
      </div>

      {/* 하단 액션 바 */}
      <div className="flex items-center gap-1 px-3 py-2 border-t border-border/30 bg-muted/20">
        {/* 리뷰 토글 */}
        {p.reviews.length > 0 && (
          <button
            onClick={() => setShowReviews(v => !v)}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground
                       px-2 py-1 rounded-lg hover:bg-muted transition-colors"
          >
            <MessageSquare className="w-3 h-3" />
            리뷰 {p.reviews.length}개
          </button>
        )}

        <div className="flex-1" />

        {/* 지도 링크 */}
        <a href={naverUrl} target="_blank" rel="noopener noreferrer"
           onClick={e => e.stopPropagation()}
           className="text-[11px] px-2 py-1 rounded-lg bg-green-50 text-green-700
                      hover:bg-green-100 transition-colors font-medium">
          N 네이버
        </a>
        <a href={kakaoUrl} target="_blank" rel="noopener noreferrer"
           onClick={e => e.stopPropagation()}
           className="text-[11px] px-2 py-1 rounded-lg bg-yellow-50 text-yellow-700
                      hover:bg-yellow-100 transition-colors font-medium">
          K 카카오
        </a>
        {p.website && (
          <a href={p.website} target="_blank" rel="noopener noreferrer"
             onClick={e => e.stopPropagation()}
             className="text-[11px] px-2 py-1 rounded-lg bg-blue-50 text-blue-700
                        hover:bg-blue-100 transition-colors font-medium flex items-center gap-0.5">
            <ExternalLink className="w-2.5 h-2.5" />
            홈페이지
          </a>
        )}
      </div>

      {/* 리뷰 패널 */}
      {showReviews && p.reviews.length > 0 && (
        <div className="px-3 pb-3 flex flex-col gap-2 border-t border-border/20">
          {p.reviews.map((r, i) => (
            <div key={i} className="pt-2">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[11px] font-semibold">{r.author}</span>
                <div className="flex">
                  {Array.from({ length: 5 }).map((_, s) => (
                    <Star key={s}
                      className={`w-2.5 h-2.5 ${s < r.rating ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground'}`}
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
