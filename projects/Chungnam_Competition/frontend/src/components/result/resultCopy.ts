import type { Destination, RecommendResponse } from '@/types'
import { SKY_MAP } from '@/lib/weather'

function firstLines(text: string, maxLines: number): string {
  const parts = text
    .split(/\n+/)
    .map(s => s.trim())
    .filter(Boolean)
  return parts.slice(0, maxLines).join('\n')
}

/** [A] 결론 한 줄 */
export function heroConclusion(
  d: Destination | null,
  _data: RecommendResponse | null,
): string {
  if (!d) return '오늘 조건에 맞는 코스를 골라봤어요.'
  return (d.decision_conclusion || '').trim() || '오늘 둘러보기 괜찮은 흐름이에요.'
}

/** [A] 보조 한 문장(피치/날씨) */
export function heroSupportingLine(
  d: Destination | null,
  data: RecommendResponse | null,
): string {
  if (data?.today_course_pitch?.trim()) {
    return firstLines(data.today_course_pitch.trim(), 2)
  }
  if (d?.why_today_narrative?.trim()) {
    const t = d.why_today_narrative.trim()
    return t.length > 90 ? t.slice(0, 88) + '…' : t
  }
  if (data?.weather) {
    const w = data.weather
    return `지금 ${w.temp}° · ${SKY_MAP[w.sky] ?? '하늘'} · 강수 ${w.precip_prob}%.`
  }
  if (d?.lead_weather_sentence?.trim()) {
    return d.lead_weather_sentence.trim()
  }
  return '지금 조건에 맞춰 첫 방문에 부담 없는 동선으로 잡아봤어요.'
}

export function takeThreeShortReasons(d: Destination | null): string[] {
  if (!d) {
    return [
      '조건이 잘 맞는 편이에요.',
      '이동·시간 흐름이 무리가 적은 편이에요.',
      '가볍게 둘러보기에 부담이 적은 곳이에요.',
    ]
  }
  const from =
    d.why_recommend_bullets?.length
      ? d.why_recommend_bullets
      : (d.concise_explanation_lines?.length
          ? d.concise_explanation_lines
          : (d.why ?? []))
  const seen = new Set<string>()
  const out: string[] = []
  for (const line of from) {
    const t = line.replace(/\s+/g, ' ').trim()
    if (!t || seen.has(t)) continue
    seen.add(t)
    out.push(t.length > 64 ? t.slice(0, 62) + '…' : t)
    if (out.length >= 3) break
  }
  const extra = [
    '이동·시간 흐름이 부담스럽지 않은 편이에요.',
    '첫 방문에도 정리해 보기 쉬운 편이에요.',
  ]
  for (const line of extra) {
    if (out.length >= 3) break
    if (seen.has(line)) continue
    seen.add(line)
    out.push(line)
  }
  return out.slice(0, 3)
}

export function displayTagsForCard(d: Destination): string[] {
  const t = d.enriched_tags?.length
    ? d.enriched_tags
    : d.tags
  return t.slice(0, 3).map(x => (x.startsWith('#') ? x : `#${x}`))
}
