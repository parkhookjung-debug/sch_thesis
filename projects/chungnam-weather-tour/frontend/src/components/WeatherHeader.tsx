import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Thermometer, Droplets, Wind, Eye } from 'lucide-react'
import { SKY_MAP, DUST_MAP, type WeatherTheme } from '@/lib/weather'
import type { Weather } from '@/types'

const CITIES = [
  '전체', '아산', '공주', '보령', '서산', '논산',
  '부여', '당진', '태안', '홍성', '천안', '금산',
  '서천', '예산', '청양',
]

const THEME_CONFIG: Record<WeatherTheme, {
  gradient: string
  emoji: string
  pill: string
}> = {
  sunny: {
    gradient: 'from-amber-400 via-orange-400 to-yellow-300',
    emoji: '☀️',
    pill: 'bg-white/25 hover:bg-white/35',
  },
  cloudy: {
    gradient: 'from-slate-500 via-slate-400 to-blue-300',
    emoji: '⛅',
    pill: 'bg-white/20 hover:bg-white/30',
  },
  rainy: {
    gradient: 'from-blue-700 via-blue-500 to-cyan-400',
    emoji: '🌧️',
    pill: 'bg-white/20 hover:bg-white/30',
  },
}

interface Props {
  city: string
  weather: Weather | null
  theme: WeatherTheme
  onCityChange: (city: string | null) => void
}

export default function WeatherHeader({ city, weather, theme, onCityChange }: Props) {
  const cfg = THEME_CONFIG[theme]

  return (
    <header className={`bg-gradient-to-br ${cfg.gradient} text-white`}>
      <div className="max-w-2xl mx-auto px-5 pt-8 pb-6">

        {/* 상단 로고 + 도시 선택 */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest opacity-80 mb-1">
              충남 날씨 관광
            </p>
            <h1 className="text-2xl font-bold leading-tight">
              {city === '전체' ? '충남 전체' : city}의 오늘
            </h1>
          </div>
          <Select value={city} onValueChange={onCityChange}>
            <SelectTrigger
              className={`w-28 ${cfg.pill} border-white/30 text-white text-sm rounded-full
                          focus:ring-0 focus:ring-offset-0 transition-colors`}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CITIES.map(c => (
                <SelectItem key={c} value={c}>
                  {c === '전체' ? '🗺 충남 전체' : c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 메인 날씨 표시 */}
        {weather ? (
          <>
            <div className="flex items-end gap-4 mb-5">
              <span className="text-7xl leading-none drop-shadow-sm">{cfg.emoji}</span>
              <div>
                <div className="text-6xl font-bold leading-none">{weather.temp}°</div>
                <div className="text-sm opacity-80 mt-1">
                  {SKY_MAP[weather.sky] ?? '알수없음'}
                </div>
              </div>
            </div>

            {/* 날씨 세부 정보 pills */}
            <div className="flex flex-wrap gap-2">
              <WeatherPill
                icon={<Droplets className="w-3.5 h-3.5" />}
                label={`강수 ${weather.precip_prob}%`}
                pill={cfg.pill}
              />
              <WeatherPill
                icon={<Wind className="w-3.5 h-3.5" />}
                label={DUST_MAP[weather.dust] ?? '보통'}
                prefix="미세먼지"
                pill={cfg.pill}
              />
              <WeatherPill
                icon={<Eye className="w-3.5 h-3.5" />}
                label={SKY_MAP[weather.sky] ?? '알수없음'}
                pill={cfg.pill}
              />
              <WeatherPill
                icon={<Thermometer className="w-3.5 h-3.5" />}
                label={`체감 ${weather.temp}°`}
                pill={cfg.pill}
              />
            </div>
          </>
        ) : (
          <div className="flex items-center gap-3 py-4 opacity-70">
            <div className="text-5xl animate-pulse">🌤️</div>
            <p className="text-sm">날씨 정보 불러오는 중...</p>
          </div>
        )}
      </div>
    </header>
  )
}

function WeatherPill({
  icon, label, prefix, pill,
}: {
  icon: React.ReactNode
  label: string
  prefix?: string
  pill: string
}) {
  return (
    <div className={`flex items-center gap-1.5 ${pill} backdrop-blur-sm
                     border border-white/20 rounded-full px-3 py-1.5 text-xs font-medium transition-colors`}>
      {icon}
      {prefix && <span className="opacity-70">{prefix}</span>}
      <span>{label}</span>
    </div>
  )
}
