import type { AlternativeCourse, CourseStep, RecommendResponse, TopCourse } from '@/types'
import type { ConsumerAlternativeCourse, ConsumerCourse, ConsumerOpenStatus, ConsumerStep } from '@/lib/consumerCourseTypes'
import { COURSE_IMAGE_FALLBACK } from '@/lib/courseImageFallback'
import type { TripFormState } from '@/lib/tripParams'

function roleLabel(role?: string | null): string {
  const r = String(role || '').toLowerCase()
  if (r === 'meal') return '식사'
  if (r === 'cafe_rest') return '카페'
  if (r === 'night_walk' || r === 'finish' || r === 'late_night_rest') return '마무리'
  return '관광·체험'
}

function openFromStep(_step: CourseStep, _hour: number): ConsumerOpenStatus {
  return 'unknown'
}

function stepToConsumer(s: CourseStep, idx: number): ConsumerStep {
  const nm = (s.name || '').replace(/\s+/g, ' ').trim().slice(0, 40)
  const tags = (s.tag_labels && s.tag_labels.length ? s.tag_labels : [])
    .slice(0, 2)
    .filter(Boolean)
  if (tags.length === 0 && s.one_line) {
    const short = s.one_line.replace(/\s+/g, ' ').trim().slice(0, 14)
    if (short) tags.push(short)
  }
  const tp =
    s.tourpass_available === true ||
    (typeof s.tourpass_confidence === 'number' && s.tourpass_confidence >= 0.4)
  return {
    id: `step-${idx}-o${s.order ?? idx}-${nm || 'stop'}`,
    role: roleLabel(s.step_role),
    name: s.name,
    image: s.image?.trim() || null,
    tags: tags.slice(0, 2),
    rating: s.rating ?? undefined,
    reviewCount: s.review_count,
    openStatus: openFromStep(s, new Date().getHours()),
    address: (s.address || '').trim(),
    tourPassCandidate: tp,
    lat: s.lat,
    lng: s.lng,
    reviewTags: [],
    reviews: [],
  }
}

function transportLabel(t: string): string {
  if (t === 'public') return '대중교통'
  if (t === 'walk') return '도보 중심'
  return '자가용'
}

export function topCourseToConsumer(
  tc: TopCourse,
  form: TripFormState,
  data: RecommendResponse,
): ConsumerCourse {
  const wx = data.weather
  const precip = Number(wx?.precip_prob ?? 0)
  const sky = Number(wx?.sky ?? 0)

  const rawSteps = (tc.steps || []).slice(0, 6)
  const steps = rawSteps.slice(0, 3).map((s, i) => stepToConsumer(s, i))

  const extraBadges: string[] = []
  if (form.tourpassMode) extraBadges.push('투어패스 우선')
  if (precip >= 45) extraBadges.push('날씨 맞춤')
  if (precip < 25 && sky <= 3) {
    extraBadges.push('야외 무난')
  }
  const mealFirst = rawSteps.some(s => String(s.step_role) === 'meal' && (s.order ?? 0) <= 1)
  if (mealFirst) extraBadges.push('점심 먼저')
  const indoorish = rawSteps.some(
    s =>
      /실내|박물관|체험/.test(`${s.name} ${s.one_line}`) ||
      String(s.step_role) === 'main_spot',
  )
  if (indoorish && precip >= 35) extraBadges.push('실내 후보')

  const summaryBadges = (data.summary?.badges || []).map(b => b.value).slice(0, 2)

  const badges = [...new Set([...extraBadges, ...summaryBadges])].slice(0, 3)

  const mobility = tc.movement_burden || '이동 부담 보통'
  const sub =
    data.summary?.one_liner ||
    tc.pitch?.split('\n')[0]?.trim() ||
    '지금 가기 좋은 흐름이에요.'

  return {
    id: tc.id || tc.course_id || 'course',
    title:
      data.summary?.headline ||
      tc.title ||
      (form.tourpassMode ? '오늘의 투어패스 코스' : '오늘 추천 코스'),
    subtitle: sub.slice(0, 80),
    durationLabel: tc.estimated_duration || '반나절',
    transportLabel: transportLabel(form.transport),
    mobilityLine: mobility.length > 24 ? `${mobility.slice(0, 24)}…` : mobility,
    badges,
    heroImage: tc.hero_image?.trim() || tc.steps?.[0]?.image || null,
    tourPassEnabled: form.tourpassMode,
    tourPassNote: '투어패스 활용 후보가 포함됐어요',
    steps,
  }
}

export function alternativeToConsumer(a: AlternativeCourse): ConsumerAlternativeCourse {
  const steps = (a.steps || []).slice(0, 3)
  const previews = steps.map(s => ({
    role: roleLabel(s.step_role),
    name: s.name,
    image: s.image?.trim() || null,
  }))
  const typeLabel =
    a.reason_tags?.[0] ||
    (a.title.includes('실내') ? '날씨 안정형' : '') ||
    (a.title.includes('가족') ? '가족 편의형' : '') ||
    '대안 코스'
  return {
    id: a.id,
    title: a.title,
    typeLabel,
    heroImage: a.hero_image || null,
    badges: (a.reason_tags || []).slice(0, 2),
    stepsPreview: previews,
  }
}

/** AlternativeCourse를 TopCourse 형태로 올려 결과 화면 1순위로 쓸 때 */
export function altCourseToTopCourse(alt: AlternativeCourse): TopCourse {
  const steps = alt.steps || []
  return {
    id: alt.id,
    title: alt.title,
    pitch: alt.one_liner || '',
    reasons_title: '',
    reasons: alt.reasons || [],
    reason_tags: alt.reason_tags,
    steps,
    hero_image: alt.hero_image,
    hero_name: alt.hero_name || alt.place_names?.[0] || steps[0]?.name || '',
    course_id: alt.course_id,
    estimated_duration: alt.estimated_duration,
    movement_burden: alt.movement_burden,
  }
}

export function recommendWithTopCourse(data: RecommendResponse, tc: TopCourse): RecommendResponse {
  return { ...data, top_course: tc, summary: data.summary }
}

export function mockConsumerCourse(form: TripFormState): ConsumerCourse {
  const city = form.city === '전체' ? '충남' : form.city
  return {
    id: 'mock-main',
    title: `${city} 반나절 코스`,
    subtitle: '오늘 날씨에 맞춰 잡은 가벼운 동선이에요.',
    durationLabel: '반나절',
    transportLabel: transportLabel(form.transport),
    mobilityLine: '이동 부담 낮음',
    badges: form.tourpassMode
      ? ['투어패스 우선', '휴식']
      : ['가볍게', '휴식'],
    heroImage: COURSE_IMAGE_FALLBACK,
    tourPassEnabled: form.tourpassMode,
    tourPassNote: '투어패스 활용 후보가 포함됐어요',
    steps: [
      {
        id: 'mock-1',
        role: '식사',
        name: '지역 맛집(예시)',
        image: null,
        tags: ['점심', '한 끼'],
        rating: 4.2,
        reviewCount: 120,
        openStatus: 'unknown',
        address: `${city} 시내`,
        tourPassCandidate: form.tourpassMode,
        lat: 36.792,
        lng: 127.003,
        reviewTags: ['가족에게 적합', '빠른 식사'],
        reviews: [],
      },
      {
        id: 'mock-2',
        role: '관광·체험',
        name: '근처 전시·체험(예시)',
        image: null,
        tags: ['실내', '천천히'],
        rating: 4.5,
        reviewCount: 89,
        openStatus: 'unknown',
        address: `${city} 일대`,
        tourPassCandidate: form.tourpassMode,
        lat: 36.795,
        lng: 127.01,
        reviewTags: ['조용함', '사진 좋음'],
        reviews: [],
      },
      {
        id: 'mock-3',
        role: '카페',
        name: '카페로 마무리(예시)',
        image: null,
        tags: ['휴식'],
        rating: 4.3,
        reviewCount: 210,
        openStatus: 'unknown',
        address: `${city}`,
        tourPassCandidate: false,
        lat: 36.79,
        lng: 127.008,
        reviewTags: ['조용함'],
        reviews: [],
      },
    ],
  }
}

/** 목록 화면용 mock → API 대안 코스 형태(상단 코스 교체용) */
export function mockConsumerAltToAlternative(m: ConsumerAlternativeCourse): AlternativeCourse {
  return {
    id: m.id,
    title: m.title,
    one_liner: m.typeLabel,
    place_names: m.stepsPreview.map(s => s.name),
    reason_tags: m.badges,
    hero_image: m.heroImage,
    steps: m.stepsPreview.map((s, i) => ({
      order: i + 1,
      step_label: s.role,
      step_role: i === 0 ? 'meal' : i === 1 ? 'main_spot' : 'cafe_rest',
      name: s.name,
      one_line: '',
      image: s.image,
      tag_labels: [m.badges[i % m.badges.length] || ''],
    })),
  }
}

export const MOCK_ALTERNATIVE_CONSUMER: ConsumerAlternativeCourse[] = [
  {
    id: 'alt-weather',
    title: '날씨 안정형 코스',
    typeLabel: '날씨 안정형',
    heroImage: null,
    badges: ['실내', '무난'],
    stepsPreview: [
      { role: '관광·체험', name: '실내 전시', image: null },
      { role: '카페', name: '휴식', image: null },
      { role: '식사', name: '가벼운 식사', image: null },
    ],
  },
  {
    id: 'alt-pass',
    title: '투어패스 활용형',
    typeLabel: '투어패스 활용형',
    heroImage: null,
    badges: ['혜택 후보', '동선 짧게'],
    stepsPreview: [
      { role: '관광·체험', name: '패스 후보 1', image: null },
      { role: '관광·체험', name: '패스 후보 2', image: null },
      { role: '카페', name: '마무리', image: null },
    ],
  },
  {
    id: 'alt-family',
    title: '가족 편의형',
    typeLabel: '가족 편의형',
    heroImage: null,
    badges: ['가족', '편한 동선'],
    stepsPreview: [
      { role: '식사', name: '가족 식사', image: null },
      { role: '관광·체험', name: '넓은 공간', image: null },
      { role: '카페', name: '디저트', image: null },
    ],
  },
]

export function buildConsumerCourse(data: RecommendResponse | null, form: TripFormState): ConsumerCourse {
  if (data?.top_course) return topCourseToConsumer(data.top_course, form, data)
  return mockConsumerCourse(form)
}
