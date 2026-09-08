import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { Destination, RecommendResponse, Scores } from '@/types'
import { Button } from '@/components/ui/button'
import { TreePine, Camera, Building2 } from 'lucide-react'

const AXIS = [
  { key: 'outdoor' as const, label: '날씨·야외', icon: TreePine, color: 'bg-emerald-500' },
  { key: 'photo' as const, label: '사진', icon: Camera, color: 'bg-violet-500' },
  { key: 'indoor' as const, label: '실내', icon: Building2, color: 'bg-sky-500' },
]

function MiniScores({ scores, total }: { scores: Scores; total: number }) {
  return (
    <div className="rounded-xl border border-border/50 bg-white/60 p-3 text-left">
      <p className="text-[10px] text-muted-foreground mb-2">지역 {total}곳 기준</p>
      <div className="flex gap-2">
        {AXIS.map(({ key, label, icon: Icon, color }) => {
          const val = Math.round(scores[key] * 100)
          return (
            <div key={key} className="flex-1 min-w-0">
              <div className="flex items-center gap-0.5 text-[10px] text-muted-foreground mb-0.5">
                <Icon className="w-3 h-3 flex-shrink-0" />
                <span className="truncate">{label}</span>
              </div>
              <div className="h-1 rounded-full bg-muted overflow-hidden">
                <div
                  className={`h-full rounded-full ${color} transition-all`}
                  style={{ width: `${val}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function RecommendationDetailsCollapse({
  top,
  data,
}: {
  top: Destination | null
  data: RecommendResponse | null
}) {
  const [open, setOpen] = useState(false)
  if (!data) return null
  const d = top
  const score = d?.total_score_100 ?? (d ? Math.round(d.score * 100) : 0)
  return (
    <section className="mt-5">
      <Button
        type="button"
        variant="ghost"
        className="w-full h-auto py-2 px-0 text-xs font-semibold text-muted-foreground justify-between"
        onClick={() => setOpen(x => !x)}
      >
        <span>추천 근거 자세히 보기</span>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </Button>
      {open && (
        <div className="mt-1 space-y-3 pb-1">
          <MiniScores scores={data.scores} total={data.total_fetched} />
          {d && (
            <p className="text-[10px] text-muted-foreground">
              참고 총점(규칙) <span className="font-mono text-foreground">{score}</span>
            </p>
          )}
          {d?.score_axis_display && d.score_axis_display.length > 0 && (
            <ul className="text-[11px] text-muted-foreground space-y-1 pl-0 list-none">
              {d.score_axis_display.map(ax => (
                <li key={ax.key}>
                  {ax.label} <span className="text-foreground">{ax.earned}</span>/{ax.max}
                </li>
              ))}
            </ul>
          )}
          {d?.why_detailed && d.why_detailed.length > 0 && (
            <ul className="text-[11px] text-muted-foreground pl-3 list-disc space-y-0.5">
              {d.why_detailed.slice(0, 5).map(x => (
                <li key={x.slice(0, 40)}>{x}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}
