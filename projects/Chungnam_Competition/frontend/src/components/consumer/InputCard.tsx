import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function InputCard({
  title,
  children,
  className,
}: {
  title: string
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={cn(
        'space-y-3',
        className,
      )}
    >
      <h2 className="text-[14px] font-extrabold text-[#3a2a20] tracking-tight">{title}</h2>
      {children}
    </section>
  )
}
