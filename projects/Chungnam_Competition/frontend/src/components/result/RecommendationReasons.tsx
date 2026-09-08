import { takeThreeShortReasons } from './resultCopy'
import type { Destination } from '@/types'

export default function RecommendationReasons({ d }: { d: Destination | null }) {
  const list = takeThreeShortReasons(d)
  return (
    <section className="mt-6" aria-label="왜 추천했나요">
      <h3 className="text-sm font-bold text-foreground mb-2">왜 추천했나요?</h3>
      <ul className="space-y-2 pl-0 list-none">
        {list.map((line, i) => (
          <li
            key={i}
            className="text-sm text-foreground/90 pl-3 border-l-[3px] border-primary/35 leading-relaxed"
          >
            {line}
          </li>
        ))}
      </ul>
    </section>
  )
}
