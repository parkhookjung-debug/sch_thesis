import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { TripFormState } from '@/lib/tripParams'
import type { TripDuration } from '@/hooks/useRecommend'

interface Props {
  value: TripFormState
  onChange: (next: TripFormState) => void
}

export default function TripConditionForm({ value: f, onChange }: Props) {
  const patch = (p: Partial<TripFormState>) => onChange({ ...f, ...p })

  return (
    <div className="space-y-4">
      <div>
        <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest mb-2">
          지역
        </p>
        <Select
          value={f.city ?? undefined}
          onValueChange={v => patch({ city: v ?? '전체' })}
        >
          <SelectTrigger className="h-10 rounded-2xl w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[
              '전체', '아산', '공주', '보령', '서산', '논산',
              '부여', '당진', '태안', '홍성', '천안', '금산',
              '서천', '예산', '청양',
            ].map(c => (
              <SelectItem key={c} value={c}>
                {c === '전체' ? '충남 전체' : c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest mb-2">
          일정
        </p>
        <div className="flex flex-wrap gap-2">
          {(
            [
              ['2h', '2시간'],
              ['half-day', '반나절'],
              ['full-day', '종일'],
            ] as const
          ).map(([v, label]) => (
            <button
              key={v}
              type="button"
              onClick={() =>
                patch({
                  tripDuration: v as TripDuration,
                  durationFullKind: '1d',
                })
              }
              className={`text-xs font-semibold px-3 py-2 rounded-full border transition-colors ${
                f.tripDuration === v
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border/60 bg-white/70 text-muted-foreground hover:border-primary/40'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Select
          value={f.companion ?? undefined}
          onValueChange={v => patch({ companion: v ?? 'solo' })}
        >
          <SelectTrigger className="h-10 rounded-2xl text-xs">
            <SelectValue placeholder="동행" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="solo">1인</SelectItem>
            <SelectItem value="couple">커플</SelectItem>
            <SelectItem value="family">가족</SelectItem>
            <SelectItem value="friends">친구</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={f.tripGoal ?? undefined}
          onValueChange={v => patch({ tripGoal: v ?? 'healing' })}
        >
          <SelectTrigger className="h-10 rounded-2xl text-xs">
            <SelectValue placeholder="목적" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="healing">힐링</SelectItem>
            <SelectItem value="photo">사진</SelectItem>
            <SelectItem value="walking">걷기</SelectItem>
            <SelectItem value="indoor">실내</SelectItem>
            <SelectItem value="culture">문화</SelectItem>
            <SelectItem value="kids">키즈</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={f.transport ?? undefined}
          onValueChange={v => patch({ transport: v ?? 'car' })}
        >
          <SelectTrigger className="h-10 rounded-2xl text-xs">
            <SelectValue placeholder="이동" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="car">자가용</SelectItem>
            <SelectItem value="public">대중교통</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={f.adultCount ?? undefined}
          onValueChange={v => patch({ adultCount: v ?? '2' })}
        >
          <SelectTrigger className="h-10 rounded-2xl text-xs col-span-1">
            <SelectValue placeholder="성인" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">성인 1</SelectItem>
            <SelectItem value="2">성인 2</SelectItem>
            <SelectItem value="3">성인 3</SelectItem>
            <SelectItem value="4">성인 4</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={f.childCount ?? undefined}
          onValueChange={v => patch({ childCount: v ?? '0' })}
        >
          <SelectTrigger className="h-10 rounded-2xl text-xs">
            <SelectValue placeholder="아이" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="0">아이 0</SelectItem>
            <SelectItem value="1">아이 1</SelectItem>
            <SelectItem value="2">아이 2</SelectItem>
            <SelectItem value="3">아이 3</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
