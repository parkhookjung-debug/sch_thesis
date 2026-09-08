import { Button } from '@/components/ui/button'
import type { ReactNode, FormEvent } from 'react'

export function BottomCTA({
  children,
  disabled,
  onClick,
}: {
  children: ReactNode
  disabled?: boolean
  onClick?: (e: FormEvent) => void
}) {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 max-w-lg mx-auto consumer-dock border-t px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <Button
        type="button"
        disabled={disabled}
        onClick={e => onClick?.(e)}
        className="w-full h-14 rounded-xl text-[16px] font-extrabold app-primary-button border-0"
      >
        {children}
      </Button>
    </div>
  )
}
