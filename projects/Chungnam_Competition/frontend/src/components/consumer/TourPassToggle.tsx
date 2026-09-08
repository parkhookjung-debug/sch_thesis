import { HelpCircle } from 'lucide-react'

export function TourPassToggle({
  enabled,
  onChange,
}: {
  enabled: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div className="rounded-2xl border border-[#eadfce] bg-[#fffdf8] p-4 shadow-[0_10px_28px_-24px_rgba(80,48,28,0.35)]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="text-[15px] font-extrabold text-[#2b1b12]">투어패스 사용</p>
            <button
              type="button"
              className="text-[#a89889] hover:text-[#6f6257]"
              title="패스 혜택은 현장·공지 기준이에요. 앱 표시는 참고용입니다."
              aria-label="도움말"
            >
              <HelpCircle className="w-4 h-4" />
            </button>
          </div>
          <p className="text-[12px] text-[#7b6a5c] mt-1 font-medium leading-snug">
            {enabled
              ? '투어패스 혜택 가능 코스를 우선 추천'
              : '일반 추천'}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          onClick={() => onChange(!enabled)}
          className={`relative mt-0.5 h-10 w-[3.25rem] shrink-0 rounded-full border-2 transition ${
            enabled
              ? 'bg-[#f28c6b] border-[#f28c6b]'
              : 'bg-[#e9e1d6] border-[#d8cbbd]'
          }`}
        >
          <span
            className={`absolute top-0.5 h-7 w-7 rounded-full bg-white shadow transition-all ${
              enabled ? 'left-[calc(100%-1.85rem)]' : 'left-0.5'
            }`}
          />
        </button>
      </div>
    </div>
  )
}
