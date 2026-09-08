export type WeatherTheme = 'sunny' | 'cloudy' | 'rainy'

export function getTheme(sky: number, precipProb: number): WeatherTheme {
  if (precipProb >= 60) return 'rainy'
  if (sky === 1) return 'sunny'
  return 'cloudy'
}

export const SKY_MAP: Record<number, string> = {
  1: '맑음 ☀️',
  3: '구름많음 ⛅',
  4: '흐림 ☁️',
}

export const DUST_MAP: Record<number, string> = {
  1: '좋음',
  2: '보통',
  3: '나쁨 😷',
  4: '매우나쁨 🚫',
}

export const PLACE_EMOJI: Record<string, string> = {
  자연: '🌿', 산책: '🚶', 역사: '🏯', 해변: '🏖️',
  온천: '♨️', 캠핑: '⛺', 사진맛집: '📸', 축제: '🎉',
  맛집: '🍽️', 레저: '🎯', 전시: '🖼️', 카페: '☕',
}

export function getPlaceEmoji(tags: string[]): string {
  for (const t of tags) if (PLACE_EMOJI[t]) return PLACE_EMOJI[t]
  return '📍'
}

export const THEME_CLASSES: Record<WeatherTheme, string> = {
  sunny:  'bg-amber-50',
  cloudy: 'bg-slate-100',
  rainy:  'bg-blue-50',
}

export const THEME_ACCENT: Record<WeatherTheme, string> = {
  sunny:  'bg-amber-500',
  cloudy: 'bg-slate-500',
  rainy:  'bg-blue-600',
}
