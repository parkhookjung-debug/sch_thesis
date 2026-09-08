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
  /** API 루트 `today_course_pitch` — 1위 카드에만 전달 */
  todayCoursePitch?: string | null
}

export default function DestinationCard({ destination: d, rank, onNextCourse, isSelected, todayCoursePitch }: Props) {
  const isFeatured = rank === 1
  return isFeatured
    ? <FeaturedCard destination={d} onNextCourse={onNextCourse} isSelected={isSelected} todayCoursePitch={todayCoursePitch} />
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
        {data?.website ? (
          <a href={data.website} target="_blank" rel="noopener noreferrer"
             className="flex items-center gap-1 bg-white/20 hover:bg-white/30 text-white
                        text-xs px-3 py-1.5 rounded-full transition-colors">
            <ExternalLink className="w-3 h-3" />홈페이지
          </a>
        ) : null}
        {data?.google_maps ? (
          <a href={data.google_maps} target="_blank" rel="noopener noreferrer"
             className="flex items-center gap-1 bg-white/20 hover:bg-white/30 text-white
                        text-xs px-3 py-1.5 rounded-full transition-colors">
            <ExternalLink className="w-3 h-3" />Google 지도
          </a>
        ) : null}
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
              <p className="text-[11px] font-semibold text-white/85">
                Google 리뷰 · 평점 높은 순 {data.reviews.length}개
                {data.review_count > data.reviews.length
                  ? ` (전체 ${data.review_count.toLocaleString()}건 중)`
                  : null}
              </p>
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
      <p className={`leading-relaxed line-clamp-5 ${textColor}`}>{r.text}</p>
    </div>
  )
}

/* ── 1위: 큰 히어로 카드 ─────────────────────────────────────────── */
function FeaturedCard({
  destination: d,
  onNextCourse,
  isSelected,
  todayCoursePitch,
}: {
  destination: Destination
  onNextCourse?: (d: Destination) => void
  isSelected?: boolean
  todayCoursePitch?: string | null
}) {
  const [imgError, setImgError] = useState(false)
  const emoji = getPlaceEmoji(d.tags)
  const score = d.total_score_100 ?? Math.round(d.score * 100)
  const lat = d.coords?.lat ?? 0
  const lng = d.coords?.lng ?? 0
  const axes = d.score_axis_display ?? []
  const bullets = d.why_recommend_bullets?.length
    ? d.why_recommend_bullets
    : (d.concise_explanation_lines ?? d.why ?? []).slice(0, 3)
  const pi = d.practical_info
  const conclusion = d.decision_conclusion ?? '오늘 가기 좋아요'
  const sum1 = d.place_identity_summary?.trim() || d.place_identity?.trim() || d.lead_weather_sentence || ''
  const sum2 = d.why_today_narrative?.trim() || d.lead_place_sentence || ''
  const expectPts = (d.expectation_points && d.expectation_points.length > 0)
    ? d.expectation_points
    : (d.expectation_bullets && d.expectation_bullets.length > 0)
      ? d.expectation_bullets
      : []

  return (
    <div className={`relative rounded-3xl shadow-lg mb-2 transition-all ${
      isSelected ? 'ring-2 ring-primary' : 'active:scale-[0.99]'
    }`}>
      <div className="relative h-64 rounded-t-3xl overflow-hidden">
        {d.image && !imgError ? (
          <img src={d.image} alt={d.name} loading="lazy"
            onError={() => setImgError(true)} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-7xl">
            {emoji}
          </div>
        )}

        <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent pointer-events-none" />

        <div className="absolute top-4 left-4 flex items-center gap-1 bg-amber-400 text-amber-900 text-xs font-bold px-2.5 py-1 rounded-full">
          <Star className="w-3 h-3 fill-current" />오늘의 1위
        </div>
        <div className="absolute top-4 right-4 bg-white/20 backdrop-blur-sm border border-white/30 text-white text-sm font-bold px-3 py-1 rounded-full">
          {score}점
        </div>
      </div>

      <div className="relative z-10 rounded-b-3xl bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 px-5 py-4 text-white -mt-12 pt-14">
        <div className="flex flex-wrap gap-1.5 mb-2">
          {d.tags.slice(0, 3).map(tag => (
            <span key={tag} className="text-[10px] bg-white/20 backdrop-blur-sm border border-white/20 px-2 py-0.5 rounded-full">
              #{tag}
            </span>
          ))}
        </div>
        <h2 className="text-xl font-bold leading-tight mb-1">{d.name}</h2>
        <p className="text-[11px] font-semibold text-emerald-200 mb-1.5">{conclusion}</p>
        <div className="flex items-center gap-1 text-xs opacity-80 mb-2">
          <MapPin className="w-3 h-3" />
          {d.address}
        </div>
        {sum1 ? (
          <p className="text-[10px] opacity-95 leading-snug mb-1 font-medium">{sum1}</p>
        ) : null}
        {todayCoursePitch && todayCoursePitch.trim() ? (
          <p className="text-[10px] opacity-90 leading-relaxed mb-2 whitespace-pre-line border-l-2 border-white/35 pl-2.5">
            {todayCoursePitch.trim()}
          </p>
        ) : null}
        {sum2 ? (
          <p className="text-[10px] opacity-88 leading-snug mb-2">{sum2}</p>
        ) : null}
        {pi?.mobility_line_distance || pi?.mobility_line_drive ? (
          <div className="text-[10px] opacity-75 leading-snug mb-2 space-y-0.5">
            {pi.mobility_line_distance ? <p>{pi.mobility_line_distance}</p> : null}
            {pi.mobility_line_drive ? <p>{pi.mobility_line_drive}</p> : null}
          </div>
        ) : pi?.mobility_line ? (
          <p className="text-[10px] opacity-75 leading-snug mb-2">{pi.mobility_line}</p>
        ) : null}
        {pi?.duration_fit_line ? (
          <p className="text-[10px] opacity-80 leading-snug mb-2">{pi.duration_fit_line}</p>
        ) : null}
        <p className="text-[10px] font-bold opacity-95 mb-1">왜 추천했나요?</p>
        <ul className="text-[10px] opacity-88 leading-snug mb-2 pl-3 list-disc space-y-0.5">
          {bullets.slice(0, 3).map(line => (
            <li key={line.slice(0, 48)}>{line}</li>
          ))}
        </ul>
        {expectPts.length > 0 ? (
          <>
            <p className="text-[10px] font-bold opacity-95 mb-1">기대해도 좋은 점</p>
            <ul className="text-[10px] opacity-88 leading-snug mb-2 pl-3 list-disc space-y-0.5">
              {expectPts.slice(0, 3).map(line => (
                <li key={line.slice(0, 48)}>{line}</li>
              ))}
            </ul>
          </>
        ) : null}
        {(d.story_summary || d.emotional_copy) && (d.storytelling_match_confidence ?? 0) >= 0.35 ? (
          <p className="text-[10px] opacity-75 italic leading-snug mb-2 border-l-2 border-white/40 pl-2">
            {d.emotional_copy?.trim() || d.story_summary?.trim()}
          </p>
        ) : !sum1 && d.copy ? (
          <p className="text-[10px] opacity-70 line-clamp-2 mb-2">{d.copy}</p>
        ) : null}
        {(d.why_detailed && d.why_detailed.length > 0) || axes.length > 0 ? (
          <details className="text-[10px] opacity-85 mb-2">
            <summary className="cursor-pointer font-semibold">추천 근거 자세히 보기</summary>
            <p className="mt-1.5 text-[9px] opacity-70">내부 참고 점수 {score} · 세부 축</p>
            {axes.length > 0 ? (
              <ul className="mt-1 space-y-0.5">
                {axes.map(ax => (
                  <li key={ax.key}>
                    {ax.label} {ax.earned}/{ax.max}
                  </li>
                ))}
              </ul>
            ) : null}
            {d.why_detailed && d.why_detailed.length > 0 ? (
              <ul className="mt-1 pl-3 list-disc space-y-0.5">
                {d.why_detailed.map(x => (
                  <li key={x.slice(0, 32)}>{x}</li>
                ))}
              </ul>
            ) : null}
          </details>
        ) : null}
        {d.caution_lines && d.caution_lines.length > 0 ? (
          <div className="text-[9px] opacity-70 leading-snug mb-2 space-y-0.5">
            <p className="font-semibold opacity-85">출발 전 확인</p>
            {d.caution_lines.slice(0, 2).map(c => (
              <p key={c.slice(0, 40)}>· {c}</p>
            ))}
          </div>
        ) : null}

        {onNextCourse && (
          <button
            type="button"
            onClick={() => onNextCourse(d)}
            className="flex items-center gap-1.5 bg-white/20 hover:bg-white/30 backdrop-blur-sm
                       border border-white/30 text-white text-xs font-semibold
                       px-3 py-1.5 rounded-full transition-colors mb-2"
          >
            <ChevronRight className="w-3.5 h-3.5" />
            코스 이어가기
          </button>
        )}

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
  const score = d.total_score_100 ?? Math.round(d.score * 100)
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

        <div className="flex-1 py-3 pr-3 min-w-0">
          <div className="flex items-start justify-between gap-1 mb-0.5">
            <h3 className="text-[15px] font-bold leading-snug line-clamp-1">{d.name}</h3>
            <span className="flex-shrink-0 text-[11px] font-bold text-primary">{score}점</span>
          </div>
          {d.decision_conclusion ? (
            <p className="text-[10px] font-semibold text-teal-600 mb-1">{d.decision_conclusion}</p>
          ) : null}
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground mb-2">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="line-clamp-1">{d.address}</span>
          </div>
          {(d.story_summary || d.emotional_copy) && (d.storytelling_match_confidence ?? 0) >= 0.35 ? (
            <p className="text-[10px] text-primary/80 italic leading-snug line-clamp-2 mb-1">
              {d.emotional_copy?.trim() || d.story_summary?.trim()}
            </p>
          ) : null}
          {(d.lead_weather_sentence || d.concise_explanation_lines?.[0]) && (
            <p className="text-[10px] text-muted-foreground leading-snug line-clamp-2 mb-1">
              {d.lead_weather_sentence ?? d.concise_explanation_lines?.[0]}
            </p>
          )}
          {(d.lead_place_sentence || d.concise_explanation_lines?.[1]) && (
            <p className="text-[10px] text-muted-foreground leading-snug line-clamp-2 mb-2">
              {d.lead_place_sentence ?? d.concise_explanation_lines?.[1]}
            </p>
          )}
          <div className="flex items-center justify-between">
            <div className="flex flex-wrap gap-1">
              {d.tags.slice(0, 2).map(tag => (
                <span
                  key={tag}
                  className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full"
                >
                  #{tag}
                </span>
              ))}
            </div>
            {onNextCourse && (
              <button
                type="button"
                onClick={() => onNextCourse(d)}
                className="flex items-center gap-0.5 text-[11px] text-primary font-semibold
                           hover:underline flex-shrink-0"
              >
                코스 이어가기
                <ChevronRight className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
      </div>

      {lat !== 0 && (
        <div className="flex items-center gap-1 px-3 py-2 border-t border-border/30 bg-muted/20">
          <button
            type="button"
            onClick={toggleReview}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded-lg hover:bg-muted transition-colors"
          >
            <MessageSquare className="w-3 h-3" />
            {showReview ? '리뷰 닫기' : '리뷰 보기'}
          </button>
          <div className="flex-1" />
          <a
            href={naverUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] px-2 py-1 rounded-lg bg-green-50 text-green-700 hover:bg-green-100 transition-colors font-medium"
          >
            N 네이버
          </a>
          <a
            href={kakaoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] px-2 py-1 rounded-lg bg-yellow-50 text-yellow-700 hover:bg-yellow-100 transition-colors font-medium"
          >
            K 카카오
          </a>
          {data?.google_maps ? (
            <a
              href={data.google_maps}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[11px] px-2 py-1 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors font-medium inline-flex items-center gap-0.5"
            >
              <ExternalLink className="w-2.5 h-2.5" />
              Google
            </a>
          ) : null}
        </div>
      )}

      {showReview && (
        <div className="px-4 pb-3 border-t border-border/20">
          {loading ? (
            <div className="space-y-2 pt-3">
              {[1, 2].map(i => (
                <div key={i} className="h-12 rounded-lg bg-muted animate-pulse" />
              ))}
            </div>
          ) : !data || data.reviews.length === 0 ? (
            <p className="text-xs text-muted-foreground pt-3">등록된 리뷰가 없습니다.</p>
          ) : (
            <div className="pt-2 space-y-0">
              <p className="text-[11px] font-semibold text-foreground/90 pb-1">
                Google 리뷰 · 평점 높은 순 {data.reviews.length}개
                {data.review_count > data.reviews.length
                  ? ` (전체 ${data.review_count.toLocaleString()}건 중)`
                  : null}
              </p>
              {data.rating > 0 && (
                <div className="flex items-center gap-1.5 py-2">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  <span className="text-sm font-bold">{data.rating.toFixed(1)}</span>
                  <span className="text-xs text-muted-foreground">
                    ({data.review_count.toLocaleString()}개)
                  </span>
                </div>
              )}
              {data.reviews.map((r, i) => (
                <ReviewItem key={i} review={r} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
