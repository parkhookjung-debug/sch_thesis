import { useEffect, useState } from 'react'

function currentTimeLabel(): string {
  const d = new Date()
  return `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function LiveStatusBar({ className = '' }: { className?: string }) {
  const [timeLabel, setTimeLabel] = useState(currentTimeLabel)

  useEffect(() => {
    const tick = () => setTimeLabel(currentTimeLabel())
    tick()
    const id = window.setInterval(tick, 30_000)
    return () => window.clearInterval(id)
  }, [])

  return (
    <div className={`ios-statusbar ${className}`.trim()}>
      <span>{timeLabel}</span>
      <span className="text-[12px]">▴  Wi-Fi  ▰</span>
    </div>
  )
}
