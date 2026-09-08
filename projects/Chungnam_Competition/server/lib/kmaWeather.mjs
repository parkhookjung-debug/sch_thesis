/**
 * 기상청 단기예보(getVilageFcst) — Python lib/weather.py 와 동일 파라미터·격자·슬롯 선택.
 * Node fetch TLS 스택 사용 (Windows 등에서 Python requests 와 동작이 다를 수 있음).
 */

import { airQualityForCity } from './airQuality.mjs'

export const GRID_COORDS = {
  아산: { nx: 67, ny: 100 },
  천안: { nx: 63, ny: 110 },
  공주: { nx: 63, ny: 96 },
  보령: { nx: 54, ny: 91 },
  서산: { nx: 51, ny: 103 },
  논산: { nx: 62, ny: 92 },
  계룡: { nx: 65, ny: 95 },
  당진: { nx: 54, ny: 105 },
  태안: { nx: 48, ny: 100 },
  홍성: { nx: 55, ny: 98 },
  부여: { nx: 60, ny: 91 },
  금산: { nx: 69, ny: 88 },
  서천: { nx: 55, ny: 87 },
  예산: { nx: 58, ny: 99 },
  청양: { nx: 59, ny: 94 },
}

const CITY_ANCHORS_DEG = {
  아산: [36.7898, 127.0022],
  천안: [36.8151, 127.1139],
  공주: [36.4556, 127.124],
  보령: [36.3333, 126.6128],
  서산: [36.7817, 126.4529],
  논산: [36.1872, 127.0987],
  계룡: [36.2758, 127.2386],
  당진: [36.8897, 126.6459],
  태안: [36.7528, 126.2983],
  홍성: [36.6009, 126.665],
  부여: [36.2758, 126.9108],
  금산: [36.1088, 127.4889],
  서천: [36.0786, 126.6919],
  예산: [36.6807, 126.8449],
  청양: [36.4462, 126.8018],
}

function haversineKm(lat1, lng1, lat2, lng2) {
  const r = 6371
  const p1 = (lat1 * Math.PI) / 180
  const p2 = (lat2 * Math.PI) / 180
  const dphi = ((lat2 - lat1) * Math.PI) / 180
  const dlmb = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dphi / 2) ** 2 +
    Math.cos(p1) * Math.cos(p2) * Math.sin(dlmb / 2) ** 2
  return 2 * r * Math.asin(Math.min(1, Math.sqrt(a)))
}

function nearestAnchorCity(lat, lng) {
  let best = '아산'
  let bestD = 1e9
  for (const [city, coord] of Object.entries(CITY_ANCHORS_DEG)) {
    if (!GRID_COORDS[city]) continue
    const d = haversineKm(lat, lng, coord[0], coord[1])
    if (d < bestD) {
      bestD = d
      best = city
    }
  }
  return best
}

export function resolveForecastAnchorCity(city, userLat, userLng) {
  if (userLat != null && userLng != null) {
    try {
      const la = Number(userLat)
      const ln = Number(userLng)
      if (Number.isFinite(la) && Number.isFinite(ln)) {
        return [nearestAnchorCity(la, ln), 'gps_nearest']
      }
    } catch {
      /* fallthrough */
    }
  }
  const c = String(city || '').trim()
  if (c && c !== '전체' && GRID_COORDS[c]) return [c, 'selected_city']
  return ['아산', 'default_city']
}

export function getBaseTime() {
  let now = new Date()
  const baseHours = [2, 5, 8, 11, 14, 17, 20, 23]
  let hour = now.getHours()
  const filtered = baseHours.filter((h) => h <= hour)
  let baseHour = filtered.length ? Math.max(...filtered) : 23

  if (baseHour > hour) {
    now = new Date(now.getTime() - 86400000)
    baseHour = 23
  }

  const pad = (n) => String(n).padStart(2, '0')
  const baseDate = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`
  const baseTime = `${pad(baseHour)}00`
  return [baseDate, baseTime]
}

function forecastFromItems(items, nowHour) {
  const byTime = {}
  for (const item of items || []) {
    const ft = item.fcstTime
    const cat = item.category
    if (!ft || !cat) continue
    if (!byTime[ft]) byTime[ft] = {}
    byTime[ft][cat] = item.fcstValue ?? ''
  }
  const keys = Object.keys(byTime)
  if (!keys.length) return [{}, null]

  const target = nowHour * 100
  function timeKey(ft) {
    const n = parseInt(String(ft), 10)
    return Number.isFinite(n) ? n : 0
  }

  let bestFt = keys[0]
  let bestDiff = Infinity
  for (const ft of keys) {
    const diff = Math.abs(timeKey(ft) - target)
    if (diff < bestDiff) {
      bestDiff = diff
      bestFt = ft
    }
  }
  return [byTime[bestFt] || {}, bestFt]
}

function stripKey(raw) {
  if (raw == null || raw === '') return null
  let s = String(raw).trim().replace(/^["']|["']$/g, '')
  if (!s) return null
  return s.includes('%') ? decodeURIComponent(s) : s
}

function weatherForecastUrl() {
  const full = process.env.WEATHER_FORECAST_URL?.trim()
  if (full) return full.replace(/\/$/, '')
  const root =
    process.env.WEATHER_BASE_URL?.trim() ||
    'https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0'
  return `${root.replace(/\/$/, '')}/getVilageFcst`
}

export function sanitizeFallbackNote(reason) {
  if (!reason) return ''
  let r = String(reason).trim()
  const low = r.toLowerCase().replace(/\s/g, '')
  if (
    low.includes('certificate_verify_failed') ||
    low.includes('sslcertverificationerror') ||
    (low.includes('ssl') && low.includes('certificate')) ||
    low.includes('certificateverifyfailed')
  ) {
    return (
      'HTTPS 인증서 검증 실패로 기상청 단기예보를 받지 못했습니다. ' +
      '관리: Node/OS 신뢰 저장소·회사망 프록시·NODE_EXTRA_CA_CERTS를 점검하세요.'
    )
  }
  if (/\b403\b/.test(r) || r.includes('Forbidden')) {
    return (
      '공공데이터포털(data.go.kr)에서 「기상청_단기예보」(VilageFcstInfoService) 활용신청·호출 IP를 확인하세요.'
    )
  }
  const fu = low.indexOf('for url:')
  if (fu >= 0) r = r.slice(0, fu).trim() + ' (요청 URL·인증키는 보안상 생략)'
  r = r.replace(/serviceKey=[^&\s]+/gi, 'serviceKey=***')
  r = r.replace(/https?:\/\/[^\s]+/g, '[URL 생략]')
  return r.slice(0, 400)
}

function fallbackWeather(airCity, reason) {
  const now = new Date()
  return {
    temp: 20.0,
    precip_prob: 0.0,
    sky: 1,
    hour: now.getHours(),
    city: airCity,
    base_date: `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`,
    base_time: '0500',
    fcst_time_slot: null,
    dust: 1,
    pm25: null,
    pm10: null,
    air_source: null,
    weather_fallback: true,
    weather_fallback_note: sanitizeFallbackNote(reason),
    weather_source: 'fallback',
  }
}

async function mergeAir(out, airCity) {
  const air = await airQualityForCity(airCity)
  if (!air) return out
  out.dust = air.dust
  out.pm25 = air.pm25
  out.pm10 = air.pm10
  out.air_source = `에어코리아 ${air.sido_name} 측정소 ${air.stations_used}개 기준 (${air.grade_basis})`
  return out
}

function numFromForecast(forecast, cat, defaultVal) {
  const raw = forecast[cat]
  if (raw == null || raw === '') return defaultVal
  const n = Number(raw)
  return Number.isFinite(n) ? n : defaultVal
}

/**
 * Python fetch_weather 와 동일 형태의 dict 반환 (JSON 직렬화 가능).
 */
export async function fetchWeatherFull(city = '아산', userLat = null, userLng = null) {
  const [gridCity, anchorReason] = resolveForecastAnchorCity(city, userLat, userLng)
  const airCity =
    anchorReason === 'gps_nearest'
      ? gridCity
      : String(city || '').trim() && String(city).trim() !== '전체'
        ? String(city).trim()
        : gridCity

  const key = stripKey(process.env.WEATHER_API_KEY)
  if (!key) {
    const out = fallbackWeather(airCity, 'WEATHER_API_KEY가 설정되지 않았습니다.')
    out.forecast_anchor_city = gridCity
    out.forecast_anchor_reason = anchorReason
    return await mergeAir(out, airCity)
  }

  const coords = GRID_COORDS[gridCity]
  const [baseDate, baseTime] = getBaseTime()
  const nowHour = new Date().getHours()

  const params = new URLSearchParams({
    serviceKey: key,
    numOfRows: '100',
    pageNo: '1',
    dataType: 'JSON',
    base_date: baseDate,
    base_time: baseTime,
    nx: String(coords.nx),
    ny: String(coords.ny),
  })

  try {
    const url = `${weatherForecastUrl()}?${params.toString()}`
    const ac = new AbortController()
    const to = setTimeout(() => ac.abort(), 10_000)
    const response = await fetch(url, { signal: ac.signal })
    clearTimeout(to)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const data = await response.json()
    const body = data?.response?.body ?? {}
    let rawItems = body.items
    let items = []
    if (rawItems == null) items = []
    else if (typeof rawItems === 'object' && !Array.isArray(rawItems)) {
      const it = rawItems.item
      if (Array.isArray(it)) items = it
      else if (it) items = [it]
    } else if (Array.isArray(rawItems)) items = rawItems

    const header = data?.response?.header ?? {}
    const rc = String(header.resultCode ?? '00').trim()
    if (rc !== '00' && rc !== '0') {
      const fb = fallbackWeather(airCity, `기상청 API 오류: ${header.resultMsg ?? JSON.stringify(header)}`)
      fb.forecast_anchor_city = gridCity
      fb.forecast_anchor_reason = anchorReason
      return await mergeAir(fb, airCity)
    }

    const [forecast, fcstSlot] = forecastFromItems(items, nowHour)

    const out = {
      temp: numFromForecast(forecast, 'TMP', 20.0),
      precip_prob: numFromForecast(forecast, 'POP', 0.0),
      sky: Math.round(numFromForecast(forecast, 'SKY', 1.0)),
      hour: nowHour,
      city: airCity,
      base_date: baseDate,
      base_time: baseTime,
      fcst_time_slot: fcstSlot,
      dust: 1,
      pm25: null,
      pm10: null,
      air_source: null,
      weather_fallback: false,
      weather_source: 'vilagefcst',
      forecast_anchor_city: gridCity,
      forecast_anchor_reason: anchorReason,
    }
    return await mergeAir(out, airCity)
  } catch (e) {
    const fb = fallbackWeather(airCity, `${e?.name || 'Error'}: ${e?.message || e}`)
    fb.forecast_anchor_city = gridCity
    fb.forecast_anchor_reason = anchorReason
    return await mergeAir(fb, airCity)
  }
}

export function applyClockDate(weather, currentTime, currentDate) {
  const w = { ...weather }
  if (currentTime) {
    const parts = String(currentTime).trim().split(':')
    try {
      w.hour = parseInt(parts[0], 10) % 24
    } catch {
      /* ignore */
    }
    if (parts.length >= 2) {
      try {
        w.minute = parseInt(parts[1], 10) % 60
      } catch {
        w.minute = 0
      }
    }
  }
  if (currentDate) {
    const ds = String(currentDate).trim()
    if (ds) w.current_date_iso = ds
  }
  return w
}

export function toWeatherSnapshotBody(weather) {
  const skyMap = { 1: '맑음', 3: '구름많음', 4: '흐림' }
  const sky = parseInt(String(weather.sky ?? 1), 10)
  return {
    weather: {
      temp: weather.temp,
      precip_prob: weather.precip_prob,
      sky: weather.sky,
      sky_text: skyMap[sky] ?? '알수없음',
      dust: weather.dust,
      hour: weather.hour,
      minute: weather.minute ?? 0,
      current_date_iso: weather.current_date_iso,
      weather_fallback: weather.weather_fallback,
      weather_fallback_note: weather.weather_fallback_note,
      weather_source: weather.weather_source,
      fcst_time_slot: weather.fcst_time_slot,
      forecast_anchor_city: weather.forecast_anchor_city,
      forecast_anchor_reason: weather.forecast_anchor_reason,
      pm25: weather.pm25,
      pm10: weather.pm10,
      air_source: weather.air_source,
    },
  }
}
