/**
 * 에어코리아 시도별 실시간 대기질 (공공데이터) — Python lib/airquality.py 와 동일 규칙.
 */

function parseFloatVal(val) {
  if (val == null) return null
  const s = String(val).trim()
  if (s === '' || s === '-' || s === '측정불가') return null
  const m = /^([\d.]+)/.exec(s)
  if (!m) return null
  const n = Number(m[1])
  return Number.isFinite(n) ? n : null
}

export function pm25ToGrade(pm25) {
  if (pm25 <= 15) return 1
  if (pm25 <= 35) return 2
  if (pm25 <= 75) return 3
  return 4
}

export function pm10ToGrade(pm10) {
  if (pm10 <= 30) return 1
  if (pm10 <= 80) return 2
  if (pm10 <= 150) return 3
  return 4
}

function normalizeItems(body) {
  const items = body?.items
  if (items == null) return []
  if (Array.isArray(items)) return items
  if (typeof items === 'object') {
    const it = items.item
    if (it == null) return []
    return Array.isArray(it) ? it : [it]
  }
  return []
}

function stripEncodedKey(raw) {
  if (raw == null || raw === '') return null
  let s = String(raw).trim().replace(/^["']|["']$/g, '')
  if (!s) return null
  return s.includes('%') ? decodeURIComponent(s) : s
}

function firstEncodedKey(...names) {
  for (const name of names) {
    const v = stripEncodedKey(process.env[name])
    if (v) return v
  }
  return null
}

function airCtprvnUrl() {
  const full = process.env.AIR_KOREA_FORECAST_URL?.trim()
  if (full) return full.replace(/\/$/, '')
  const base =
    process.env.AIR_KOREA_BASE_URL?.trim() ||
    'https://apis.data.go.kr/B552584/ArpltnInforInqireSvc'
  return `${base.replace(/\/$/, '')}/getCtprvnRltmMesureDnsty`
}

/** 충남 시군 코스용 시도는 항상 충남 */
export async function airQualityForCity(_city) {
  const key = firstEncodedKey('AIR_KOREA_API_KEY', 'PUBLIC_DATA_SERVICE_KEY', 'WEATHER_API_KEY')
  if (!key) return null

  const sidoName = '충남'
  const params = new URLSearchParams({
    serviceKey: key,
    returnType: 'json',
    numOfRows: '200',
    pageNo: '1',
    sidoName,
    ver: '1.0',
  })

  try {
    const url = `${airCtprvnUrl()}?${params.toString()}`
    const ac = new AbortController()
    const to = setTimeout(() => ac.abort(), 12_000)
    const r = await fetch(url, { signal: ac.signal })
    clearTimeout(to)
    if (!r.ok) return null
    const data = await r.json()
    const header = data?.response?.header
    const rc = String(header?.resultCode ?? '').trim()
    if (rc !== '00' && rc !== '0') return null
    const body = data?.response?.body
    if (!body) return null

    const rows = normalizeItems(body)
    const pm25List = []
    const pm10List = []
    for (const row of rows) {
      const v = parseFloatVal(row.pm25Value ?? row.pm25value)
      if (v != null) pm25List.push(v)
      const v10 = parseFloatVal(row.pm10Value ?? row.pm10value)
      if (v10 != null) pm10List.push(v10)
    }

    if (!pm25List.length && !pm10List.length) return null

    const pm25Avg = pm25List.length ? pm25List.reduce((a, b) => a + b, 0) / pm25List.length : null
    const pm10Avg = pm10List.length ? pm10List.reduce((a, b) => a + b, 0) / pm10List.length : null

    let grade
    let basis
    if (pm25Avg != null) {
      grade = pm25ToGrade(pm25Avg)
      basis = 'pm25'
    } else if (pm10Avg != null) {
      grade = pm10ToGrade(pm10Avg)
      basis = 'pm10'
    } else {
      return null
    }

    return {
      dust: grade,
      pm25: pm25Avg != null ? Math.round(pm25Avg * 10) / 10 : null,
      pm10: pm10Avg != null ? Math.round(pm10Avg * 10) / 10 : null,
      sido_name: sidoName,
      stations_used: pm25List.length || pm10List.length,
      grade_basis: basis,
    }
  } catch {
    return null
  }
}
