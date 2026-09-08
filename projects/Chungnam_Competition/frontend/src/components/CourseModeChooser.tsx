import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { Destination } from '@/types'

export type GuidedHint =
  | 'meal'
  | 'cafe'
  | 'quiet'
  | 'photo'
  | 'indoor'
  | 'kids'
  | 'custom'

const GUIDED_CHIPS: { key: GuidedHint; label: string }[] = [
  { key: 'meal', label: '식사' },
  { key: 'cafe', label: '카페' },
  { key: 'quiet', label: '조용한 곳' },
  { key: 'photo', label: '사진·전망' },
  { key: 'indoor', label: '실내' },
  { key: 'kids', label: '아이와 함께' },
]

interface Props {
  destination: Destination
  onAi: () => void
  onGuided: (hint: GuidedHint, customNote?: string) => void
  onCancel: () => void
}

export default function CourseModeChooser({ destination, onAi, onGuided, onCancel }: Props) {
  const [phase, setPhase] = useState<'pick_mode' | 'pick_direction'>('pick_mode')
  const [customOpen, setCustomOpen] = useState(false)
  const [customText, setCustomText] = useState('')

  return (
    <div className="mb-3 rounded-2xl border border-primary/25 bg-white/90 px-4 py-3 shadow-sm">
      <p className="text-xs font-bold text-primary mb-0.5">다음은 어떻게 정할까요?</p>
      <p className="text-[11px] text-muted-foreground mb-3">
        <span className="font-medium text-foreground">{destination.name}</span> 이후 — 자동은{' '}
        <span className="font-medium text-foreground">규칙 기반</span>이에요. 원하면 방향만 직접 고를 수도 있어요.
      </p>

      {phase === 'pick_mode' ? (
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            className="w-full rounded-xl font-semibold"
            onClick={() => {
              onAi()
            }}
          >
            규칙 기반 자동 추천
          </Button>
          <p className="text-[10px] text-muted-foreground -mt-1 mb-0.5 text-center">
            다음 장면·후보는 날씨·시간·의도 규칙으로 정해요.
          </p>
          <Button
            type="button"
            variant="outline"
            className="w-full rounded-xl font-semibold border-primary/40"
            onClick={() => setPhase('pick_direction')}
          >
            원하는 방향 직접 고르기
          </Button>
          <button
            type="button"
            className="text-[11px] text-muted-foreground hover:text-foreground pt-1"
            onClick={onCancel}
          >
            닫기
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-[11px] text-muted-foreground">먼저 흐름만 골라 주세요. (지도 검색만 하는 것보다 덜 헤매게 도와요.)</p>
          <div className="flex flex-wrap gap-1.5">
            {GUIDED_CHIPS.map(c => (
              <button
                key={c.key}
                type="button"
                className="text-[11px] font-semibold px-2.5 py-1.5 rounded-full bg-primary/10 text-primary border border-primary/15 hover:bg-primary/15"
                onClick={() => onGuided(c.key)}
              >
                {c.label}
              </button>
            ))}
          </div>
          {!customOpen ? (
            <button
              type="button"
              className="text-[11px] font-semibold text-primary underline-offset-2 hover:underline"
              onClick={() => setCustomOpen(true)}
            >
              직접 장소·메모 입력
            </button>
          ) : (
            <div className="space-y-2">
              <input
                placeholder="예: ○○카페 가고 싶어요"
                value={customText}
                onChange={e => setCustomText(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-xs ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  className="rounded-lg text-xs"
                  disabled={!customText.trim()}
                  onClick={() => onGuided('custom', customText.trim())}
                >
                  이대로 반영하고 후보 보기
                </Button>
                <Button type="button" size="sm" variant="ghost" className="text-xs" onClick={() => setCustomOpen(false)}>
                  취소
                </Button>
              </div>
            </div>
          )}
          <div className="flex justify-between pt-1">
            <button
              type="button"
              className="text-[11px] text-muted-foreground"
              onClick={() => {
                setPhase('pick_mode')
                setCustomOpen(false)
              }}
            >
              ← 이전
            </button>
            <button type="button" className="text-[11px] text-muted-foreground" onClick={onCancel}>
              닫기
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
