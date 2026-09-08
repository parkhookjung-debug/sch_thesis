import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Droplets, Wind, Eye } from 'lucide-react'
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
  /** 홈: 날씨 없이 짧은 안내만(로딩 스피너 대신) */
  inputMode?: boolean
  /** inputMode에서만 사용: 제목/부제 덮어쓰기 */
  titleOverride?: string
  subtitleOverride?: string
  /** 홈: TripConditionForm에 지역이 있을 때 상단 셀렉트 숨기기 */
  hideRegionPicker?: boolean
}

export default function WeatherHeader({
  city,
  weather,
  theme,
  onCityChange,
  inputMode = false,
  titleOverride,
  subtitleOverride,
  hideRegionPicker = false,
}: Props) {
  const cfg = THEME_CONFIG[theme]

  return (
    <header className={`bg-gradient-to-br ${cfg.gradient} text-white`}>
      <div className="max-w-2xl mx-auto px-5 pt-8 pb-6">

        {/* 상단 로고 + 도시 선택 */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest opacity-80 mb-1">
              충남 당일 코스 (날씨·의도 인지)
            </p>
            <h1 className="text-2xl font-bold leading-tight">
              {titleOverride ??
                `${city === '전체' ? '충남 전체' : city} 오늘의 동선`}
            </h1>
            <p className="text-[11px] opacity-90 mt-1.5 leading-snug max-w-[220px]">
              {subtitleOverride ??
                '오늘 어디 갈지·다음에 뭘 할지, 검색 시간 줄이는 당일 결정 도우미예요.'}
            </p>
          </div>
          {!hideRegionPicker && (
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
          )}
        </div>

        {/* 메인 날씨 표시 */}
        {weather ? (
          <>
            {weather.weather_fallback && (
              <div className="mb-4 rounded-xl bg-amber-500/25 border border-amber-200/40 px-3 py-2 text-[11px] leading-snug text-white">
                <strong>기상청 예보 연결 실패</strong> — 아래 기온·하늘·강수는{' '}
                <span className="opacity-90">고정 기본값</span>이고, 미세먼지는 에어코리아만 반영됐을 수 있습니다.
                {weather.weather_fallback_note && (
                  <span className="block mt-1 opacity-80 text-[10px] leading-relaxed">
                    {weather.weather_fallback_note}
                  </span>
                )}
              </div>
            )}
            {!weather.weather_fallback && weather.weather_source === 'vilagefcst' && weather.fcst_time_slot && (
              <p className="text-[10px] opacity-75 mb-3">
                단기예보 슬롯 {weather.fcst_time_slot} 기준 (격자별로 지역마다 다름)
              </p>
            )}
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
                label={
                  weather.pm25 != null && weather.pm25 !== undefined
                    ? `${DUST_MAP[weather.dust] ?? '보통'} · PM2.5 ${weather.pm25}`
                    : (DUST_MAP[weather.dust] ?? '보통')
                }
                prefix="대기"
                pill={cfg.pill}
              />
              <WeatherPill
                icon={<Eye className="w-3.5 h-3.5" />}
                label={SKY_MAP[weather.sky] ?? '알수없음'}
                pill={cfg.pill}
              />
            </div>
          </>
        ) : inputMode ? (
          <div className="flex items-start gap-3 py-2">
            <div className="text-4xl">🧭</div>
            <p className="text-sm opacity-90 leading-relaxed max-w-sm">
              지역·일정·동행을 골랐다가{' '}
              <span className="font-semibold">「코스 추천받기」</span>를 누르면, 오늘
              맞춤 날씨와 함께 한눈에 읽는 추천 화면으로 이동해요.
            </p>
          </div>
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
