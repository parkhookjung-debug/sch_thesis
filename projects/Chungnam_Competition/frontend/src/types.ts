export interface Weather {
  temp: number
  precip_prob: number
  sky: number
  sky_text: string
  dust: number
  /** 추천에 사용한 시각(선택) */
  hour?: number
  minute?: number
  current_date_iso?: string | null
  /** 에어코리아 시도 평균 등 연동 시 */
  pm25?: number | null
  pm10?: number | null
  air_source?: string | null
  /** 기상청 호출 실패 시 대체 값 */
  weather_fallback?: boolean
  weather_fallback_note?: string | null
  /** vilagefcst | fallback */
  weather_source?: string | null
  /** 단기예보에서 골라 쓴 fcstTime 슬롯 (예: "1400") */
  fcst_time_slot?: string | null
  /** 단기예보 nx·ny에 사용한 시군(가까운 앵커) */
  forecast_anchor_city?: string | null
  /** gps_nearest | selected_city | default_city */
  forecast_anchor_reason?: string | null
}

export interface Scores {
  outdoor: number
  photo: number
  indoor: number
}

export interface ScoreAxisDisplay {
  key: string
  label: string
  earned: number
  max: number
}

export interface PracticalInfo {
  distance_km?: number | null
  drive_minutes_approx?: number | null
  mobility_line: string
  mobility_line_distance?: string | null
  mobility_line_drive?: string | null
  transport_note: string
  /** 일정 길이별 규칙 설명 한 줄 */
  duration_fit_line?: string
}

export interface Destination {
  id?: string
  name: string
  address: string
  tags: string[]
  score: number
  weather_score: number
  distance_km: number
  image?: string
  copy: string
  category?: string
  coords?: { lat: number; lng: number }
  /** 메인 추천 휴리스틱 부분점수 0~1 */
  score_breakdown?: Record<string, number>
  score_contributions?: Record<string, number>
  recommendation_summary?: string
  total_score_100?: number
  score_axis_display?: ScoreAxisDisplay[]
  top_reason_tokens?: string[]
  concise_explanation_lines?: string[]
  practical_info?: PracticalInfo
  caution_lines?: string[]
  why?: string[]
  why_detailed?: string[]
  /** 결론 우선 라벨 (점수 대신) */
  decision_conclusion?: string
  lead_weather_sentence?: string
  lead_place_sentence?: string
  why_recommend_bullets?: string[]
  /** 스토리텔링 CSV 매칭 시 */
  story_summary?: string | null
  story_tags?: string[]
  emotional_copy?: string | null
  narrative_enrichment_line?: string | null
  storytelling_match_confidence?: number
  /** 4층 내러티브 — 장소 정체성 한 줄 */
  place_identity?: string
  /** 짧은 유형 요약(설명 레이어) */
  place_identity_summary?: string
  /** 오늘 맥락(일정·날씨 등) */
  why_today_narrative?: string
  /** 기대 포인트 불릿 */
  expectation_bullets?: string[]
  /** 기대 포인트( place_identity_summary 와 쌍) */
  expectation_points?: string[]
  /** 키워드·규칙으로 붙인 시맨틱 태그 */
  enriched_tags?: string[]
  narrative_archetype?: string
  /** Google Places 등(있을 때만) */
  rating?: number
  review_count?: number
}

export interface PlaceReview {
  author: string
  rating: number
  text: string
  relative: string
}

export interface NextPlace {
  place_id?: string
  name: string
  address: string
  rating: number
  review_count: number
  open_now: boolean | null
  photo_url: string | null
  types: string[]
  lat: number
  lng: number
  next_course_score?: number
  /** 0~100 환산 점수(식사 랭킹용) */
  score_100?: number
  score_breakdown?: Record<string, number>
  recommendation_reason_one_line?: string
  distance_from_prev_km?: number
  source_type?: string
  source_mix?: string
  public_data_match?: boolean
  merged_candidate_flag?: boolean
  /** 일부 레거시/실험 응답에서만 제공 */
  reviews?: PlaceReview[]
  website?: string
  google_maps?: string
}

/** /api/course 1순위 장소 블록 */
export interface PrimaryCoursePick {
  name: string
  score?: number
  place_id?: string
  source_type?: string
  source_mix?: string
  public_data_match?: boolean
  merged_candidate_flag?: boolean
  data_source_note?: string | null
  why?: string[]
  after_this?: string[]
  after_this_title?: string
  practical_info?: PracticalInfo
  drive_minutes_approx?: number | null
  score_breakdown?: Record<string, number>
  distance_from_prev_km?: number
  address?: string
  types?: string[]
  /** 리뷰 키워드 기반 보조 점수(원문 없음) */
  review_features?: Record<string, number | string>
}

/** /api/course — 다음 장면(신규 필드) */
export interface NextSceneBlock {
  type: string
  title: string
  why: string[]
  headline?: string
  /** 식사·실내 식사 단계: 왜 지금 끼니인지 */
  why_meal_now?: string[]
}

/** 실내 전환 등 고수준 장면 안의 구체 방식(식사/카페/실내 관람) */
export interface SceneModeBlock {
  type: string
  title: string
  why: string[]
}

/** /api/course — 레거시·실험: 다음 장면 보조(규칙 폴백). 홈 첫 추천과 별개 */
export interface MlNextSceneMeta {
  model_used?: boolean
  next_scene_reason_mode?: 'model-assisted' | 'rule-based'
  predicted_next_scene?: string | null
  rule_based_stage?: string
  scene_probs?: Record<string, number> | null
  top_features?: Array<{ feature: string; importance?: number }> | null
  /** API·디버그용(소비자 문구에 직접 쓰지 않음) */
  fallback_reason?: string | null
}

/** /api/course — 서버가 적용한 힌트·분기(개발·검증용, 소비자 문구에 직접 쓰지 않음) */
export interface CourseControlBlock {
  applied_user_hint?: string | null
  desired_next_scene?: string | null
  desired_course_style?: string | null
  effective_stage?: string
  decision_mode?: string
  next_scene_reason_mode?: string | null
  ml_model_used?: boolean
  replace_step?: boolean
  step_index?: number | null
  step_role?: string | null
  time_band?: string | null
  bias?: {
    family?: number
    scenic?: number
    indoor?: number
    meal?: number
    cafe?: number
  }
}

/** /api/course — 코스 이어가기 응답 */
export interface CourseContinuationResponse {
  course_control?: CourseControlBlock
  course_path?: string
  guided_flow_notes?: string[]
  next_step_headline?: string
  next_scene?: NextSceneBlock
  /** 고수준 장면(indoor_transition 등)과 1순위 장소 사이의 중간 설명 */
  scene_mode?: SceneModeBlock
  next_stage: {
    type: string
    title: string
    why: string[]
    headline?: string
  }
  meal_style?: {
    key: string
    label: string
    secondary_key?: string | null
    secondary_label?: string | null
    why: string[]
    need_meal?: number
    need_rest?: number
  }
  /** 식사 스타일별 요리 편향(가산용, 한·중·일·서) */
  cuisine_bias?: Record<string, number>
  after_this?: string[]
  primary_recommendation: PrimaryCoursePick | null
  /** 장소만 요약(선택 필드, primary_recommendation과 동일 계열) */
  primary_place?: { name?: string; why?: string[]; after_this?: string[] } | null
  /** 식사 단계와 동일 블록(스키마 호환용 별칭) */
  primary_restaurant?: PrimaryCoursePick | null
  alternatives: NextPlace[]
  next_places: NextPlace[]
  meta: {
    radius_used: number
    fallback_applied: boolean
    trip_state?: Record<string, number>
    fallback_note?: string | null
    source_mix?: { google_places: number; citytour_api: number; merged_candidate_count: number }
    /** 2h | half-day | full-day — 코스 이어가기 깊이 */
    duration?: string
    continuation_depth_hint?: string
    /** indoor_backup이 meal/cafe/indoor_visit으로 구체화된 경우 */
    indoor_transition_split?: boolean
    time_band?: string
    replace_step?: boolean
    replace_step_index?: number | null
    replace_step_role?: string | null
    review_meta_applied?: boolean
  }
  /** 규칙 폴백 가능한 약지도 next_scene 분류기 메타 */
  ml_next_scene?: MlNextSceneMeta
}

export interface RecommendInputSummary {
  companion: string
  trip_goal: string
  duration: string
  transport: string
  city: string
  adult_count?: string
  child_count?: string
  current_time?: string
  current_date?: string
  user_location?: { lat: number; lng: number }
  meal_preference?: string
  /** 투어패스 활용 모드(선택). false 이면 기존 코스 전용 추천과 동일하게 동작합니다. */
  tourpass_mode?: boolean
  tourpass_ticket_type?: string
  benefit_priority?: string
  pass_goal?: string | null
  purchased_status?: string
}

export interface CourseBadge {
  key: string
  label: string
  value: string
}

export interface CourseSummary {
  headline: string
  one_liner: string
  badges: CourseBadge[]
  /** API 확장: 세션 요약(한글 라벨) */
  city?: string
  duration?: string
  companion?: string
  goal?: string
  weather_label?: string
  pitch?: string
  /** 시간표 코스 안내(상단 배너 문구) */
  schedule_intro?: string | null
}

/** /api/recommend 코스 후보 재정렬 메타(학습 번들 없으면 model_used=false) */
export interface CourseRerankMeta {
  enabled: boolean
  model_used: boolean
  rerank_mode: 'model-assisted' | 'rule-based'
  fallback_reason?: string | null
}

/** 시간표형 일정(메인 코스) */
export interface ItineraryEntry {
  order: number
  start_time: string
  end_time: string
  place_name: string
  step_role?: string
  step_label?: string
  category: string
  reason: string
  travel_from_prev: string
  meal_data_insufficient?: boolean
}

export interface CourseStep {
  order: number
  step_label: string
  /** 서버 규칙 엔진 역할(main_spot | meal | cafe_rest | …). 소비자에게는 step_label로 표시 */
  step_role?: string | null
  name: string
  one_line: string
  image?: string | null
  address?: string
  /** 장소 소개(큐레이션·요약) */
  detail_intro?: string | null
  detail_bullets?: string[]
  tag_labels?: string[]
  /** Google Places 등에서 온 평점·리뷰 수(본문 리뷰 텍스트는 없음) */
  rating?: number | null
  review_count?: number
  /** `/api/place-reviews`용 — 있으면 Google 리뷰 UI 노출 */
  lat?: number | null
  lng?: number | null
  /** 투어패스 메타(MVP: 일부 장소만 보강, 비단정·방문 전 확인 전제) */
  tourpass_available?: boolean | null
  tourpass_confidence?: number
  pass_benefit_type?: string
  pass_value_level?: string
  pass_category?: string
  time_ticket_fit?: string
  pass_notice?: string
  official_verified?: boolean
}

export interface TopCourse {
  id: string
  title: string
  pitch: string
  reasons_title: string
  reasons: string[]
  /** 코스 성격 태그(표시용) */
  reason_tags?: string[]
  steps: CourseStep[]
  /** 시간표 뷰(있으면 기본 표시) */
  itinerary?: ItineraryEntry[]
  time_based_banner?: string
  hero_image?: string | null
  hero_name: string
  course_id?: string
  estimated_duration?: string
  movement_burden?: string
  weather_fit?: string
  /** 예외 동선 시 디버그·투명성용 코드 */
  course_shape_reason?: string | null
}

export interface AlternativeCourse {
  id: string
  title: string
  one_liner: string
  place_names: string[]
  /** 서버가 보낸 완성 코스면 상세·비교 화면에서 그대로 사용 */
  pitch?: string
  reasons_title?: string
  reasons?: string[]
  reason_tags?: string[]
  steps?: CourseStep[]
  hero_image?: string | null
  hero_name?: string
  course_id?: string
  estimated_duration?: string
  movement_burden?: string
  weather_fit?: string
}

export interface ServiceNotice {
  disclaimer: string
  details: string[]
  short?: string[]
}

export interface PlanBlock {
  title: string
  places: Destination[]
  score?: number
  why?: string[]
  checks?: string[]
}

export interface PassQuestMission {
  mission_index: number
  role: string
  label: string
  place: CourseStep & Record<string, unknown>
  reason: string
  pass_signal: string
  risk_notice: string
}

export interface PassQuestCard {
  quest_id: string
  quest_title: string
  quest_type: string
  ticket_type: string
  summary: string
  missions: PassQuestMission[]
  badges: string[]
  scores: Record<string, number>
  scores_detail?: Record<string, number>
  disclaimer?: string
}

export interface PassQuestRerankMeta {
  model_used: boolean
  mode: string
  confidence: number | null
  features_used?: string[]
  explanation?: string | null
}

export interface PassQuestBundle {
  enabled: boolean
  ticket_type?: string
  benefit_priority?: string
  pass_goal?: string
  purchased_status?: string
  top_pass_quest?: PassQuestCard | null
  alternative_pass_quests?: PassQuestCard[]
  pass_quest_rerank?: PassQuestRerankMeta
  disclaimer?: string
  future_model_env?: Record<string, string>
}

export interface RecommendResponse {
  city: string
  weather: Weather
  scores: Scores
  total_fetched: number
  recommendations: Destination[]
  input_summary?: RecommendInputSummary
  main_scoring_model?: {
    places_review_enrichment?: string
    places_review_enrichment_limit?: number
    tourpass_mode?: boolean
    tourpass_merchant_pool_only?: boolean
    tourpass_merchant_filter_fallback?: boolean
    [key: string]: unknown
  }
  today_course_pitch?: string
  today_course_pitch_source?: 'template' | 'ollama' | 'ollama_failed' | 'none'
  /** 소비자용 — 완성 코스 뷰 */
  summary?: CourseSummary
  top_course?: TopCourse
  alternative_courses?: AlternativeCourse[]
  course_rerank?: CourseRerankMeta
  notice?: ServiceNotice
  plan_a?: PlanBlock
  plan_b?: PlanBlock
  plan_c?: PlanBlock
  meta?: {
    generated_at?: string
    confidence_notes?: string[]
    not_real_time_limitations?: string[]
    /** 심야·새벽 등 운영 가능성 안내(휴리스틱) */
    trip_feasibility_notice?: string | null
    time_based_banner?: string
    meal_data_insufficient?: boolean
    pool_categories?: Record<string, number>
    course_shape?: {
      plan_a_reason?: string | null
      plan_a_step_roles?: string[]
      time_band?: string
      /** 서버: night_late | dawn | morning | … */
      time_band_detail?: string
      trip_hour?: number
      trip_minute?: number
      meal_phase?: string
    }
  }
  itinerary?: ItineraryEntry[]
  meal_context?: {
    phase?: string
    basis_line?: string
    clock_label?: string
    requires_verified_meal_place?: boolean
  }
  /** 투어패스 활용 모드가 켜졌을 때만 상세. 꺼져 있으면 enabled:false 수준의 최소 필드만 옵니다. */
  pass_quest?: PassQuestBundle
}
