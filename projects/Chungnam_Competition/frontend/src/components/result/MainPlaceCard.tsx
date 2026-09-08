import { useState } from 'react'
import { MapPin, Star } from 'lucide-react'
import { getPlaceEmoji } from '@/lib/weather'
import { displayTagsForCard } from './resultCopy'
import type { Destination } from '@/types'
import { Button } from '@/components/ui/button'

export default function MainPlaceCard({
  d,
  onPrimary,
  onSecondary,
  primaryLabel = '이 코스로 갈래요',
  secondaryLabel = '다른 추천 보기',
}: {
  d: Destination
  onPrimary: () => void
  onSecondary: () => void
  primaryLabel?: string
  secondaryLabel?: string
}) {
  const [imgError, setImgError] = useState(false)
  const emoji = getPlaceEmoji(d.tags)
  const pi = d.practical_info
  const oneLine = (() => {
    if (d.place_identity_summary?.trim()) return d.place_identity_summary.trim()
    if (d.place_identity?.trim()) return d.place_identity.trim()
    if (d.recommendation_summary) return d.recommendation_summary
    if (d.copy) return d.copy.length > 80 ? d.copy.slice(0, 80) + '…' : d.copy
    return '오늘 흐름에 잘 맞는 곳이에요.'
  })()
  const tagLine = displayTagsForCard(d)
  const distLine = [pi?.mobility_line_distance, pi?.mobility_line_drive]
    .filter(Boolean)
    .join(' · ') || (pi?.mobility_line ?? '')

  return (
    <section
      id="main-place"
      className="rounded-3xl overflow-hidden shadow-lg border border-border/40 bg-card"
    >
      <div className="relative h-48 sm:h-56 w-full">
        {d.image && !imgError ? (
          <img
            src={d.image}
            alt=""
            className="w-full h-full object-cover"
            loading="eager"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-6xl">
            {emoji}
          </div>
        )}
        <div className="absolute top-3 left-3 flex items-center gap-1 bg-amber-400 text-amber-950 text-[11px] font-bold px-2.5 py-1 rounded-full">
          <Star className="w-3 h-3 fill-current" />
          오늘의 1위
        </div>
      </div>
      <div className="p-4 sm:p-5">
        <h2 className="text-lg font-bold text-foreground leading-tight mb-1">{d.name}</h2>
        <p className="text-sm text-muted-foreground leading-relaxed mb-3">{oneLine}</p>
        <div className="flex flex-wrap gap-1.5 mb-3">
          {tagLine.map(t => (
            <span
              key={t}
              className="text-[11px] font-medium bg-primary/8 text-primary px-2.5 py-0.5 rounded-full"
            >
              {t}
            </span>
          ))}
        </div>
        {distLine ? (
          <div className="flex items-start gap-1.5 text-xs text-muted-foreground mb-4">
            <MapPin className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <span>{distLine}</span>
          </div>
        ) : null}
        <div className="flex flex-col sm:flex-row gap-2">
          <Button
            type="button"
            className="rounded-2xl font-semibold flex-1"
            onClick={onPrimary}
          >
            {primaryLabel}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="rounded-2xl font-semibold flex-1 bg-background"
            onClick={onSecondary}
          >
            {secondaryLabel}
          </Button>
        </div>
      </div>
    </section>
  )
}
