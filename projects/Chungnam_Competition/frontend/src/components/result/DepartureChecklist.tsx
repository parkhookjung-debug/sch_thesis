import { useState } from 'react'
import type { Destination } from '@/types'
import { ChevronDown, ChevronUp } from 'lucide-react'

const DEFAULTS = [
  '운영 시간·입장가능 시각',
  '휴무(정기) 여부',
  '혼잡·주차·요금은 현장 확인',
]

export default function DepartureChecklist({ d }: { d: Destination | null }) {
  const [open, setOpen] = useState(false)
  const extra = d?.caution_lines?.length ? d.caution_lines : []

  return (
    <section
      className="mt-6 rounded-2xl border border-border/50 bg-white/50 px-4 py-3.5"
      id="departure-check"
    >
      <h3 className="text-sm font-bold text-foreground mb-2">출발 전 확인</h3>
      <ul className="text-sm text-foreground/90 space-y-1.5 list-disc pl-4">
        {DEFAULTS.map(x => (
          <li key={x}>{x}</li>
        ))}
      </ul>
      {extra.length > 0 && (
        <div className="mt-2">
          <button
            type="button"
            onClick={() => setOpen(v => !v)}
            className="text-xs font-semibold text-primary flex items-center gap-1"
          >
            {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            서버에서 읽은 추가 주의
          </button>
          {open ? (
            <ul className="text-xs text-muted-foreground mt-2 pl-1 space-y-1 list-disc pl-4">
              {extra.slice(0, 4).map(x => (
                <li key={x.slice(0, 40)}>{x}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </section>
  )
}
