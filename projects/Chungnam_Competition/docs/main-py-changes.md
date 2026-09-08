# main.py 변경 요약

기준: Git 커밋 `18f5e75` (*Initial project upload*) → 현재 저장소의 `main.py`  
(원격 `main` 머지 + 로컬 수정이 합쳐진 상태와 동일한 범위입니다.)

---

## 1. import

| 변경 | 설명 |
|------|------|
| `fetch_place_reviews` | `lib.places`에서 함께 import — `/api/place-reviews` 라우트에서 사용 |
| `normalize_intent` | `lib.daytrip_planner`가 아니라 **`lib.intent_normalize`** 에서 import (`daytrip_planner` ↔ `places` 순환 import 방지) |
| `build_daytrip_payload` | `daytrip_planner`에서는 페이로드 빌드만 import |

---

## 2. `GET /api/recommend`

### 추가 쿼리 파라미터

- **`current_time`** (선택): `HH:MM` — `weather["hour"]` / `weather["minute"]`에 반영. **랭킹(`match_from_api`) 호출 전**에 적용되므로 점수·시간축에 실제로 탑재됨.
- **`current_date`** (선택): `YYYY-MM-DD` — `weather["current_date_iso"]`에 반영(시간표 시작일 등).
- **`meal_preference`** (선택): `normalize_intent(..., meal_preference=...)`로 넘김.

### 동작 보강

- `weather.setdefault("minute", 0)` 로 분 단위 기본값.
- `match_from_api` 이후 **`trip_context`** dict를 만들어 `build_daytrip_payload(..., trip_context=...)`에 전달  
  (`clock_hour`, `clock_minute`, `current_date_iso`, `meal_preference`, `user_lat`, `user_lng`).
- 의도 정규화 시 **`meal_preference`** 인자 추가.

(응답 본문에 날씨 확장 필드 머지하는 블록은 기존과 동일한 역할.)

---

## 3. 신규: `GET /api/place-reviews`

- **역할**: 메인 카드용 Google 리뷰 조회 (`fetch_place_reviews`).
- **필수 쿼리**: `name`, `lat`, `lng` / **선택**: `address`.
- 백그라운드에서 `run_in_executor` 로 동기 함수 호출 (다른 API와 동일 패턴).

*(리뷰 정렬·동명 장소 매칭 보정 등 상세 로직은 `lib/places.py` 쪽 커밋 메시지: 메인 장소 리뷰, 동명 타지역 오매칭 완화.)*

---

## 4. `GET /api/course`

### 추가 쿼리 파라미터 (재구성·단계 교체 UX)

| 파라미터 | 용도 |
|----------|------|
| `reconfigure_target` | 수정 대상 식별(문서화/향후 분기) |
| `selected_course_type` | `active` / `top` / `alternative` |
| `course_id` | 편집 기준 코스 id |
| `replace_step` | `True`면 단계 교체 후보만 (리뷰 메타 재랭킹 등) |
| `step_index` | 교체 대상 단계 인덱스 |
| `step_role` | `main_spot` \| `meal` \| `cafe_rest` \| `secondary_spot` \| `finish` |
| `time_band` | 시간대 힌트; 비우면 서버가 `hour`로 산출 |

### `build_course_payload`에 넘기는 인자

현재 `main.py`에서는 위 중 **`replace_step`**, **`replace_step_index`** (`step_index`), **`replace_step_role`** (`step_role`), **`time_band`** 만 코어 빌더에 전달합니다. 나머지 재구성 식별자는 API 시그니처에만 노출된 상태로 둘 수 있습니다(프론트·향후 확장용).

---

## 5. 변경 없는 부분

- **루트 `/`**, **`/legacy`**, **SPA 폴백** `/{full_path:path}` — 구조 동일.
- **`__main__`**: `uvicorn.run(app, host="0.0.0.0", port=settings.port)` — 포트는 기본 `PORT` 환경변수 / `8000` (`lib/config.py`).
- **정적 마운트** `FRONTEND_DIST` + `/assets` — 기존과 동일 조건.

---

## 6. 한 줄 정리

**홈 추천**은 시각·날짜·식사 선호를 받아 날씨 객체와 `trip_context`로 **코스/랭킹 파이프**에 넘기고, **리뷰**는 별도 **`/api/place-reviews`**로 분리했으며, **코스 이어가기**는 재구성·단계 교체용 쿼리와 **`intent_normalize` 모듈 분리**가 `main.py`에서의 주요 차이입니다.

---

*생성 시점: 로컬 `git diff 18f5e75 HEAD -- main.py` 기준으로 정리.*
