import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { APP_NAME } from '@/config/app'

/** 메인 흐름 밖: 서비스·한계 안내(접기) */
export default function ServiceFooter() {
  const [open, setOpen] = useState(false)
  return (
    <footer className="mt-6 pt-4 border-t border-border/50 text-center max-w-2xl mx-auto px-4 pb-6">
      <p className="text-[10px] text-muted-foreground">
        © {APP_NAME} ·{' '}
        <button
          type="button"
          onClick={() => setOpen(o => !o)}
          className="font-medium text-foreground/70 inline-flex items-center gap-0.5"
        >
          서비스 안내
          <ChevronDown className={`w-3 h-3 inline transition ${open ? 'rotate-180' : ''}`} />
        </button>
      </p>
      {open && (
        <ul className="text-[10px] text-muted-foreground mt-3 text-left list-disc pl-4 space-y-1 max-w-sm mx-auto">
          <li>정보는 예보·공개 데이터·큐레이션을 조합하며, 실시간·입장·주차·요금을 보장하지 않습니다.</li>
          <li>투어패스 관련 문구는 “활용 가능성” 수준이며, 할인·무료를 보장하지 않습니다.</li>
        </ul>
      )}
    </footer>
  )
}
