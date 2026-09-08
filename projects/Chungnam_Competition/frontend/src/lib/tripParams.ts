import { readStoredUserGeo } from '@/lib/userGeoStorage'

export type TripDuration = '2h' | 'half-day' | 'full-day'

export interface RecommendFetchOptions {
  companion?: string
  trip_goal?: string
  transport?: string
  adult_count?: string
  child_count?: string
  current_time?: string
  current_date?: string
  meal_preference?: string
  tourpass_mode?: boolean
  tourpass_ticket_type?: string
  benefit_priority?: string
  pass_goal?: string
  purchased_status?: string
}

export type TourpassTicketType =
  | 'none'
  | '24h'
  | '36h'
  | '48h'
  | 'single'
  | 'theme'
  | 'undecided'

export type BenefitPriority = 'none' | 'balanced' | 'high'

export type PassGoalKey =
  | 'benefit_first'
  | 'food_cafe_linked'
  | 'family_friendly'
  | 'rainy_day_safe'
  | 'short_trip'
  | 'festival_linked'
  | 'experience_focused'

export type PurchasedStatus = 'already_have' | 'considering' | 'not_planned'

/** full-day일 때만 UI·URL에 쓰임(API duration은 full-day 동일) */
export type DurationFullKind = '1d' | '1n2d' | '2n3d'

export interface TripFormState {
  city: string
  tripDuration: TripDuration
  durationFullKind: DurationFullKind
  companion: string
  tripGoal: string
  transport: string
  adultCount: string
  childCount: string
  /** HH:MM — 비우면 서버가 예보 시각 기준 */
  currentTime: string
  /** YYYY-MM-DD */
  currentDate: string
  /** 식사 선호(짧게) */
  mealPreference: string
  /** 투어패스 활용 모드(선택) — 끄면 기존 날씨 코스만 */
  tourpassMode: boolean
  tourpassTicketType: TourpassTicketType
  benefitPriority: BenefitPriority
  /** 패스퀘스트 목표 축(날씨 목적 tripGoal 과 별개) */
  passGoal: PassGoalKey
  purchasedStatus: PurchasedStatus
}

const DUR: TripDuration[] = ['2h', 'half-day', 'full-day']

const TICKETS: TourpassTicketType[] = [
  'none',
  '24h',
  '36h',
  '48h',
  'single',
  'theme',
  'undecided',
]

const PASS_GOALS: PassGoalKey[] = [
  'benefit_first',
  'food_cafe_linked',
  'family_friendly',
  'rainy_day_safe',
  'short_trip',
  'festival_linked',
  'experience_focused',
]

function parseDuration(raw: string | null): TripDuration {
  if (raw && DUR.includes(raw as TripDuration)) return raw as TripDuration
  return 'half-day'
}

function parseDurationFullKind(raw: string | null): DurationFullKind {
  const v = (raw || '').toLowerCase().trim()
  if (v === '1n2d' || v === '2n3d') return v
  return '1d'
}

function parseTicket(raw: string | null): TourpassTicketType {
  const t = (raw || 'none').toLowerCase().trim()
  return TICKETS.includes(t as TourpassTicketType) ? (t as TourpassTicketType) : 'none'
}

function parseBenefit(raw: string | null): BenefitPriority {
  const b = (raw || 'none').toLowerCase().trim()
  if (b === 'balanced' || b === 'high' || b === 'none') return b
  return 'none'
}

function parsePassGoal(raw: string | null): PassGoalKey {
  const p = (raw || 'food_cafe_linked').toLowerCase().trim()
  return PASS_GOALS.includes(p as PassGoalKey) ? (p as PassGoalKey) : 'food_cafe_linked'
}

function parsePurchased(raw: string | null): PurchasedStatus {
  const p = (raw || 'not_planned').toLowerCase().trim()
  if (p === 'already_have' || p === 'considering' || p === 'not_planned') return p
  return 'not_planned'
}

function todayIsoLocal(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function nowTimeHHMM(): string {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function tripFormFromSearchParams(sp: URLSearchParams): TripFormState {
  const companion = sp.get('companion')?.trim() || 'solo'
  const solo = companion === 'solo'
  const ct = sp.get('current_time')?.trim()
  const cd = sp.get('current_date')?.trim()
  const tpm = sp.get('tourpass_mode')?.trim().toLowerCase()
  const tourpassMode = tpm === 'true' || tpm === '1' || tpm === 'yes'
  const tripDuration = parseDuration(sp.get('duration'))

  return {
    city: sp.get('city')?.trim() || '아산',
    tripDuration,
    durationFullKind: parseDurationFullKind(sp.get('duration_full')),
    companion,
    tripGoal: sp.get('trip_goal')?.trim() || 'healing',
    transport: sp.get('transport')?.trim() || 'car',
    adultCount: solo ? '1' : sp.get('adult_count')?.trim() || '2',
    childCount: solo ? '0' : sp.get('child_count')?.trim() || '0',
    currentTime: ct || nowTimeHHMM(),
    currentDate: cd || todayIsoLocal(),
    mealPreference: sp.get('meal_preference')?.trim() || 'none',
    tourpassMode,
    tourpassTicketType: parseTicket(sp.get('tourpass_ticket_type')),
    benefitPriority: parseBenefit(sp.get('benefit_priority')),
    passGoal: parsePassGoal(sp.get('pass_goal')),
    purchasedStatus: parsePurchased(sp.get('purchased_status')),
  }
}

export function toResultQueryString(f: TripFormState): string {
  const p = new URLSearchParams({
    city: f.city,
    duration: f.tripDuration,
    companion: f.companion,
    trip_goal: f.tripGoal,
    transport: f.transport,
    adult_count: f.adultCount,
    child_count: f.childCount,
    current_time: f.currentTime,
    current_date: f.currentDate,
    meal_preference: f.mealPreference,
    tourpass_mode: f.tourpassMode ? 'true' : 'false',
    tourpass_ticket_type: f.tourpassTicketType,
    benefit_priority: f.benefitPriority,
    pass_goal: f.passGoal,
    purchased_status: f.purchasedStatus,
  })
  if (f.tripDuration === 'full-day' && f.durationFullKind !== '1d') {
    p.set('duration_full', f.durationFullKind)
  }
  return p.toString()
}

/** /api/recommend 등에 세션 GPS가 있으면 user_lat·user_lng를 붙입니다. */
export function appendStoredUserGeo(p: URLSearchParams): void {
  const g = readStoredUserGeo()
  if (!g) return
  p.set('user_lat', String(g.lat))
  p.set('user_lng', String(g.lng))
}

export function toRecommendOptions(f: TripFormState): RecommendFetchOptions {
  return {
    companion: f.companion,
    trip_goal: f.tripGoal,
    transport: f.transport,
    adult_count: f.adultCount,
    child_count: f.childCount,
    current_time: f.currentTime,
    current_date: f.currentDate,
    meal_preference: f.mealPreference,
    tourpass_mode: f.tourpassMode,
    tourpass_ticket_type: f.tourpassTicketType,
    benefit_priority: f.benefitPriority,
    pass_goal: f.passGoal,
    purchased_status: f.purchasedStatus,
  }
}

export function toRecommendQuery(f: TripFormState): string {
  const p = new URLSearchParams({
    city: f.city,
    top_n: '18',
    duration: f.tripDuration,
    companion: f.companion,
    trip_goal: f.tripGoal,
    transport: f.transport,
    adult_count: f.adultCount,
    child_count: f.childCount,
    current_time: f.currentTime,
    current_date: f.currentDate,
    meal_preference: f.mealPreference,
    tourpass_mode: f.tourpassMode ? 'true' : 'false',
    tourpass_ticket_type: f.tourpassTicketType,
    benefit_priority: f.benefitPriority,
    pass_goal: f.passGoal,
    purchased_status: f.purchasedStatus,
  })
  appendStoredUserGeo(p)
  return p.toString()
}
