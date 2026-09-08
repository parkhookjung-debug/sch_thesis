import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full bg-[#f5ede2] px-3 py-1 text-[12px] font-bold text-[#6f6257] ring-1 ring-[#eadfce]',
        className,
      )}
    >
      {children}
    </span>
  )
}
