import { TreePine, Camera, Building2 } from 'lucide-react'
import type { Scores } from '@/types'

interface Props {
  scores: Scores
  total: number
}

const ITEMS = [
  { key: 'outdoor' as const, label: '야외 적합', icon: TreePine,   color: 'bg-emerald-500' },
  { key: 'photo'   as const, label: '사진 지수', icon: Camera,     color: 'bg-violet-500'  },
  { key: 'indoor'  as const, label: '실내 적합', icon: Building2,  color: 'bg-sky-500'     },
]

export default function ScoreBar({ scores, total }: Props) {
  return (
    <div className="bg-white/80 backdrop-blur-md border-b border-border shadow-sm">
      <div className="max-w-2xl mx-auto px-5 py-3">
        <div className="flex gap-4">
          {ITEMS.map(({ key, label, icon: Icon, color }) => {
            const val = Math.round(scores[key] * 100)
            return (
              <div key={key} className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1 text-[11px] text-muted-foreground font-medium">
                    <Icon className="w-3 h-3" />
                    {label}
                  </div>
                  <span className="text-[11px] font-bold text-foreground">{val}</span>
                </div>
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded-full ${color} transition-all duration-700`}
                    style={{ width: `${val}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
        <p className="text-[10px] text-muted-foreground text-right mt-2">
          {total}곳 분석
        </p>
      </div>
    </div>
  )
}
