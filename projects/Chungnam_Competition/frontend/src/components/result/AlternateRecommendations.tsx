import { useState } from 'react'
import { MapPin, ChevronRight } from 'lucide-react'
import { getPlaceEmoji } from '@/lib/weather'
import type { Destination } from '@/types'

function MiniRow({ d, rank }: { d: Destination; rank: number }) {
  return (
    <div className="flex gap-3 py-2.5 border-b border-border/30 last:border-0">
      <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center text-lg flex-shrink-0">
        {getPlaceEmoji(d.tags)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-1.5">
          <span className="text-[10px] font-bold text-muted-foreground">{rank}.</span>
          <h4 className="text-sm font-bold line-clamp-1">{d.name}</h4>
        </div>
        {d.decision_conclusion && (
          <p className="text-[10px] font-medium text-teal-700/90 mt-0.5 line-clamp-1">
            {d.decision_conclusion}
          </p>
        )}
        <p className="text-[10px] text-muted-foreground flex items-center gap-0.5 mt-0.5">
          <MapPin className="w-2.5 h-2.5 flex-shrink-0" />
          <span className="line-clamp-1">{d.address}</span>
        </p>
      </div>
    </div>
  )
}

export default function AlternateRecommendations({
  list,
  expanded,
  onExpandedChange,
}: {
  list: Destination[]
  /** 부모(메인 CTA)에서 열기 */
  expanded?: boolean
  onExpandedChange?: (v: boolean) => void
}) {
  const [inner, setInner] = useState(false)
  const open = expanded !== undefined ? expanded : inner
  const set = onExpandedChange ?? setInner
  if (list.length === 0) return null
  return (
    <section className="mt-6" id="alternates">
      <button
        type="button"
        onClick={() => set(!open)}
        className="w-full flex items-center justify-between text-left py-2 text-sm font-bold text-foreground"
      >
        <span>다른 추천 (2위~)</span>
        <ChevronRight
          className={`w-4 h-4 transition-transform ${open ? 'rotate-90' : ''}`}
        />
      </button>
      {open && (
        <div className="rounded-2xl border border-border/40 bg-white/60 mt-1 px-3">
          {list.map((d, i) => (
            <MiniRow key={d.name} d={d} rank={i + 2} />
          ))}
        </div>
      )}
    </section>
  )
}
