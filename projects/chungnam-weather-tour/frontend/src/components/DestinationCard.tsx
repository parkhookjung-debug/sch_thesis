import { useState } from 'react'
import { MapPin, Star, ChevronRight, MessageSquare, ExternalLink } from 'lucide-react'
import { getPlaceEmoji } from '@/lib/weather'
import { usePlaceReviews } from '@/hooks/usePlaceReviews'
import type { Destination, PlaceReview } from '@/types'

interface Props {
  destination: Destination
  rank: number
  onNextCourse?: (d: Destination) => void
  isSelected?: boolean
}

export default function DestinationCard({ destination: d, rank, onNextCourse, isSelected }: Props) {
  const isFeatured = rank === 1
  return isFeatured
    ? <FeaturedCard destination={d} onNextCourse={onNextCourse} isSelected={isSelected} />
    : <CompactCard destination={d} rank={rank} onNextCourse={onNextCourse} isSelected={isSelected} />
}

/* ── 리뷰 패널 (공통) ─────────────────────────────────────── */
function ReviewPanel({ name, lat, lng, address }: { name: string; lat: number; lng: number; address: string }) {
  const { data, loading, fetched, fetch } = usePlaceReviews()
  const [open, setOpen] = useState(false)

  function toggle() {
    if (!open && !fetched) fetch(name, lat, lng, address)
    setOpen(v => !v)
  }

  const naverUrl = `https://map.naver.com/p/search/${encodeURIComponent(name)}`
  const kakaoUrl = `https://map.kakao.com/link/search/${encodeURIComponent(name)}`

  return (
    <div className="border-t border-white/20 mt-3 pt-3">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={toggle}
          className="flex items-center gap-1.5 bg-white/20 hover:bg-white/30 backdrop-blur-sm
                     border border-white/30 text-white text-xs font-semibold
                     px-3 py-1.5 rounded-full transition-colors"
        >
          <MessageSquare className="w-3 h-3" />
          {open ? '리뷰 닫기' : '리뷰 보기'}
        </button>
        <a href={naverUrl} target="_blank" rel="noopener noreferrer"
           className="flex items-center gap-1 bg-green-500/80 hover:bg-green-500 text-white
                      text-xs font-semibold px-3 py-1.5 rounded-full transition-colors">
          N 네이버
        </a>
        <a href={kakaoUrl} target="_blank" rel="noopener noreferrer"
           className="flex items-center gap-1 bg-yellow-400/90 hover:bg-yellow-400 text-yellow-900
                      text-xs font-semibold px-3 py-1.5 rounded-full transition-colors">
          K 카카오
        </a>
        {data?.website && (
          <a href={data.website} target="_blank" rel="noopener noreferrer"
             className="flex items-center gap-1 bg-white/20 hover:bg-white/30 text-white
                        text-xs px-3 py-1.5 rounded-full transition-colors">
            <ExternalLink className="w-3 h-3" />홈페이지
          </a>
        )}
      </div>

      {open && (
        <div className="mt-3">
          {loading ? (
            <div className="space-y-2">
              {[1, 2].map(i => <div key={i} className="h-12 rounded-lg bg-white/10 animate-pulse" />)}
            </div>
          ) : !data || data.reviews.length === 0 ? (
            <p className="text-xs text-white/60">등록된 리뷰가 없습니다.</p>
          ) : (
            <div className="space-y-3">
              {data.rating > 0 && (
                <div className="flex items-center gap-1.5">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  <span className="text-sm font-bold text-white">{data.rating.toFixed(1)}</span>
                  <span className="text-xs text-white/60">({data.review_count.toLocaleString()}개 리뷰)</span>
                </div>
              )}
              {data.reviews.map((r, i) => (
                <ReviewItem key={i} review={r} dark />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ReviewItem({ review: r, dark }: { review: PlaceReview; dark?: boolean }) {
  const textColor = dark ? 'text-white/80' : 'text-muted-foreground'
  const subColor  = dark ? 'text-white/50' : 'text-muted-foreground/70'
  return (
    <div className={`text-xs ${dark ? 'border-white/10' : 'border-border/20'} border-t pt-2 first:border-t-0 first:pt-0`}>
      <div className="flex items-center gap-1.5 mb-1">
        <span className={`font-semibold ${dark ? 'text-white' : 'text-foreground'}`}>{r.author}</span>
        <div className="flex">
          {Array.from({ length: 5 }).map((_, s) => (
            <Star key={s} className={`w-2.5 h-2.5 ${s < r.rating
              ? 'fill-amber-400 text-amber-400'
              : dark ? 'text-white/20' : 'text-muted-foreground/30'}`}
            />
          ))}
        </div>
        <span className={`ml-auto ${subColor}`}>{r.relative}</span>
      </div>
      <p className={`leading-relaxed line-clamp-3 ${textColor}`}>{r.text}</p>
    </div>
  )
}

/* ── 1위: 큰 히어로 카드 ─────────────────────────────────────────── */
function FeaturedCard({
  destination: d, onNextCourse, isSelected,
}: {
  destination: Destination
  onNextCourse?: (d: Destination) => void
  isSelected?: boolean
}) {
  const [imgError, setImgError] = useState(false)
  const emoji = getPlaceEmoji(d.tags)
  const score = Math.round(d.score * 100)
  const lat = d.coords?.lat ?? 0
  const lng = d.coords?.lng ?? 0

  return (
    <div className={`relative rounded-3xl overflow-hidden shadow-lg mb-2 transition-all ${
      isSelected ? 'ring-2 ring-primary' : 'active:scale-[0.99]'
    }`}>
      {d.image && !imgError ? (
        <img src={d.image} alt={d.name} loading="lazy"
          onError={() => setImgError(true)} className="w-full h-64 object-cover" />
      ) : (
        <div className="w-full h-64 bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-7xl">
          {emoji}
        </div>
      )}

      <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />

      <div className="absolute top-4 left-4 flex items-center gap-1 bg-amber-400 text-amber-900 text-xs font-bold px-2.5 py-1 rounded-full">
        <Star className="w-3 h-3 fill-current" />오늘의 1위
      </div>
      <div className="absolute top-4 right-4 bg-white/20 backdrop-blur-sm border border-white/30 text-white text-sm font-bold px-3 py-1 rounded-full">
        {score}점
      </div>

      <div className="absolute bottom-0 left-0 right-0 p-5 text-white">
        <div className="flex flex-wrap gap-1.5 mb-2">
          {d.tags.slice(0, 3).map(tag => (
            <span key={tag} className="text-[10px] bg-white/20 backdrop-blur-sm border border-white/20 px-2 py-0.5 rounded-full">
              #{tag}
            </span>
          ))}
        </div>
        <h2 className="text-xl font-bold leading-tight mb-1">{d.name}</h2>
        <div className="flex items-center gap-1 text-xs opacity-80 mb-2">
          <MapPin className="w-3 h-3" />{d.address}
        </div>
        <p className="text-xs opacity-75 leading-relaxed line-clamp-2 mb-3">{d.copy}</p>

        <div className="flex items-center gap-2 mb-2">
          {onNextCourse && (
            <button
              onClick={() => onNextCourse(d)}
              className="flex items-center gap-1.5 bg-white/20 hover:bg-white/30 backdrop-blur-sm
                         border border-white/30 text-white text-xs font-semibold
                         px-3 py-1.5 rounded-full transition-colors"
            >
              <ChevronRight className="w-3.5 h-3.5" />다음 코스 추천
            </button>
          )}
        </div>

        {lat !== 0 && <ReviewPanel name={d.name} lat={lat} lng={lng} address={d.address} />}
      </div>
    </div>
  )
}

/* ── 2위~: 가로형 컴팩트 카드 ────────────────────────────────────── */
function CompactCard({
  destination: d, rank, onNextCourse, isSelected,
}: {
  destination: Destination
  rank: number
  onNextCourse?: (d: Destination) => void
  isSelected?: boolean
}) {
  const [imgError, setImgError] = useState(false)
  const [showReview, setShowReview] = useState(false)
  const { data, loading, fetched, fetch } = usePlaceReviews()
  const emoji = getPlaceEmoji(d.tags)
  const score = Math.round(d.score * 100)
  const lat = d.coords?.lat ?? 0
  const lng = d.coords?.lng ?? 0

  const naverUrl = `https://map.naver.com/p/search/${encodeURIComponent(d.name)}`
  const kakaoUrl = `https://map.kakao.com/link/search/${encodeURIComponent(d.name)}`

  function toggleReview() {
    if (!showReview && !fetched) fetch(d.name, lat, lng, d.address)
    setShowReview(v => !v)
  }

  return (
    <div className={`bg-white rounded-2xl shadow-sm overflow-hidden transition-all border ${
      isSelected ? 'border-primary ring-1 ring-primary' : 'border-border/50 active:scale-[0.99]'
    }`}>
      <div className="flex gap-3">
        {/* 썸네일 */}
        <div className="relative flex-shrink-0 w-28 h-28">
          {d.image && !imgError ? (
            <img src={d.image} alt={d.name} loading="lazy"
              onError={() => setImgError(true)} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-muted to-background flex items-center justify-center text-3xl">
              {emoji}
            </div>
          )}
          <div className="absolute top-1.5 left-1.5 bg-black/60 text-white text-[10px] font-bold w-5 h-5 rounded-full flex items-center justify-center">
            {rank}
          </div>
        </div>

        {/* 내용 */}
        <div className="flex-1 py-3 pr-3 min-w-0">
          <div className="flex items-start justify-between gap-1 mb-1">
            <h3 className="text-[15px] font-bold leading-snug line-clamp-1">{d.name}</h3>
            <span className="flex-shrink-0 text-[11px] font-bold text-primary">{score}점</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground mb-2">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="line-clamp-1">{d.address}</span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex flex-wrap gap-1">
              {d.tags.slice(0, 2).map(tag => (
                <span key={tag} className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                  #{tag}
                </span>
              ))}
            </div>
            {onNextCourse && (
              <button onClick={() => onNextCourse(d)}
                className="flex items-center gap-0.5 text-[11px] text-primary font-semibold hover:underline flex-shrink-0">
                다음 코스<ChevronRight className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 액션 바 */}
      {lat !== 0 && (
        <div className="flex items-center gap-1 px-3 py-2 border-t border-border/30 bg-muted/20">
          <button onClick={toggleReview}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded-lg hover:bg-muted transition-colors">
            <MessageSquare className="w-3 h-3" />
            {showReview ? '리뷰 닫기' : '리뷰 보기'}
          </button>
          <div className="flex-1" />
          <a href={naverUrl} target="_blank" rel="noopener noreferrer"
             className="text-[11px] px-2 py-1 rounded-lg bg-green-50 text-green-700 hover:bg-green-100 transition-colors font-medium">
            N 네이버
          </a>
          <a href={kakaoUrl} target="_blank" rel="noopener noreferrer"
             className="text-[11px] px-2 py-1 rounded-lg bg-yellow-50 text-yellow-700 hover:bg-yellow-100 transition-colors font-medium">
            K 카카오
          </a>
        </div>
      )}

      {/* 리뷰 패널 */}
      {showReview && (
        <div className="px-4 pb-3 border-t border-border/20">
          {loading ? (
            <div className="space-y-2 pt-3">
              {[1, 2].map(i => <div key={i} className="h-12 rounded-lg bg-muted animate-pulse" />)}
            </div>
          ) : !data || data.reviews.length === 0 ? (
            <p className="text-xs text-muted-foreground pt-3">등록된 리뷰가 없습니다.</p>
          ) : (
            <div className="pt-2 space-y-0">
              {data.rating > 0 && (
                <div className="flex items-center gap-1.5 py-2">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  <span className="text-sm font-bold">{data.rating.toFixed(1)}</span>
                  <span className="text-xs text-muted-foreground">({data.review_count.toLocaleString()}개)</span>
                </div>
              )}
              {data.reviews.map((r, i) => <ReviewItem key={i} review={r} />)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
