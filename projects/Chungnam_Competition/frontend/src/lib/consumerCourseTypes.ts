/** 소비자용 코스 UI 모델(API 응답·mock 공통) */

export interface ConsumerReview {
  author: string
  rating: number
  text: string
  relativeTime: string
}

export type ConsumerOpenStatus = 'open' | 'unknown' | 'closing_soon'

export interface ConsumerStep {
  id: string
  role: string
  name: string
  image: string | null
  tags: string[]
  rating?: number | null
  reviewCount?: number
  openStatus: ConsumerOpenStatus
  address: string
  tourPassCandidate: boolean
  lat?: number | null
  lng?: number | null
  reviewTags: string[]
  /** API에 시드가 있으면(대부분 빈 배열) — 상세에서 보강 */
  reviews: ConsumerReview[]
}

export interface ConsumerCourse {
  id: string
  title: string
  subtitle: string
  durationLabel: string
  transportLabel: string
  mobilityLine: string
  badges: string[]
  heroImage: string | null
  tourPassEnabled: boolean
  tourPassNote: string
  steps: ConsumerStep[]
}

export interface ConsumerAlternativePreview {
  role: string
  name: string
  image: string | null
}

export interface ConsumerAlternativeCourse {
  id: string
  title: string
  typeLabel: string
  heroImage: string | null
  badges: string[]
  stepsPreview: ConsumerAlternativePreview[]
}
