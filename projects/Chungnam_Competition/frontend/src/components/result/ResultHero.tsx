import { heroConclusion, heroSupportingLine } from './resultCopy'
import type { Destination, RecommendResponse } from '@/types'

export default function ResultHero({
  top,
  data,
}: {
  top: Destination | null
  data: RecommendResponse | null
}) {
  const c = heroConclusion(top, data)
  const s = heroSupportingLine(top, data)
  return (
    <header className="text-center mb-6 pt-1">
      <h1 className="text-[1.35rem] font-extrabold text-foreground leading-snug tracking-tight">
        {c}
      </h1>
      <p className="text-sm text-muted-foreground mt-2 max-w-md mx-auto leading-relaxed whitespace-pre-line">
        {s}
      </p>
    </header>
  )
}
