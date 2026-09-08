# 충남 날씨 기반 당일 코스 프로토타입

충남 지역 단기예보·사용자 조건(동행, 목적, 일정)을 반영해 **관광 코스를 추천**하는 프로토타입입니다.  
백엔드는 **FastAPI**, 소비자 UI는 기본적으로 **React(Vite)** 이며, 예전 단일 HTML UI는 **`/legacy`** 로 남아 있습니다.

---

## 팀원 온보딩: 빠른 시작

1. **저장소 받기**

   ```bash
   git clone <저장소 URL>
   cd chungnam-weather-tour
   ```

2. **Python 의존성**

   ```bash
   pip install -r requirements.txt
   ```

3. **환경 변수 (필수는 아니지만, 실제 API 연동 시 필요)**

   - 루트에서 **`.env.example`을 복사**해 **`.env`** 를 만듭니다.

     ```bash
     copy .env.example .env
     ```

     (macOS/Linux: `cp .env.example .env`)

   - **`.env`에는 본인 API 키만 넣고, Git에는 올리지 않습니다.** 변수 이름·역할은 `.env.example` 주석을 참고하세요.

4. **서버 실행**

   ```bash
   python main.py
   ```

   기본 포트는 `PORT` 환경 변수로 바꿀 수 있습니다(미설정 시 설정 모듈 기본값 사용).

5. **React UI를 쓰는 경우 (`/` 메인 화면)**

   ```bash
   cd frontend
   npm install
   npm run build
   ```

   빌드 후 루트에서 서버를 다시 띄우면, `frontend/dist`가 있을 때 **`/`에서 Vite 앱**이 서빙됩니다. 자세한 조합은 아래 **프론트 모드**를 보세요.

6. **브라우저**

   - 메인(React): **`http://127.0.0.1:8000/`** (설정·빌드 조건 충족 시)
   - 레거시 UI: **`http://127.0.0.1:8000/legacy`**
   - API 문서: **`http://127.0.0.1:8000/docs`** (FastAPI Swagger)

---

## 이 저장소에 무엇이 있나요

| 경로 | 역할 |
|------|------|
| `main.py` | FastAPI 앱 진입, `/api/recommend`, `/api/course` 등 라우트 |
| `lib/` | 추천·날씨·코스 이어가기·설정(`config`) 등 핵심 로직 |
| `data/` | `destinations.json` 등 정적 관광 메타 |
| `frontend/` | React 소스(`src/`), 빌드 산출물(`dist/`) |
| `static/` | 레거시 HTML, 빌드 안내 등 |
| `scripts/` | 검증·학습 보조 스크립트(선택) |
| `app/ml/` | `/api/course` 등에서 쓰는 **선택적** ML 보조(next_scene 등). 홈 `/api/recommend` 랭킹과는 역할이 다릅니다. |

---

## 주요 API (백엔드)

| 엔드포인트 | 설명 |
|------------|------|
| `GET /api/recommend` | 홈에서 조건 제출 시 호출. 장소 랭킹·당일 코스 묶음(`top_course`, `alternative_courses` 등) 반환 |
| `GET /api/course` | 이전 장소 기준 **다음 단계** 코스(식당·카페 등) 후보. 쿼리로 날씨·의도 일부 전달 가능 |

프론트(`frontend/src`)는 위 API를 `fetch`로 호출합니다.

---

## UI 두 가지 (레거시 vs React)

| 구분 | 레거시 | React (Vite) |
|------|--------|----------------|
| 주소 | **`/legacy`** | **`/`** (`frontend/dist/index.html`이 있고 설정이 맞을 때) |
| 소스 | `static/legacy_app.html` | `frontend/src/**` |
| 빌드 | 없음 | `cd frontend && npm run build` |
| 필요 도구 | Python만 | Python + Node.js |

**루트 `/`가 무엇을 줄지**는 `lib/config.py`의 `FRONTEND_UI`와 `frontend/dist` 존재 여부로 결정됩니다.

- **`FRONTEND_UI=dist`** 이고 **`frontend/dist/index.html`** 이 있으면 → React 앱.
- **`FRONTEND_UI=static`** 이면 → 짧은 안내 HTML 위주(React 안 씀).
- `dist`가 없으면 → 빌드 안내; 당일 체험은 **`/legacy`** 로 가능.

---

## 환경 변수·보안 (팀 공유 시 꼭 읽기)

- **커밋 가능한 것:** `.env.example` (변수 이름과 설명만, 실제 키 값 없음).
- **커밋하면 안 되는 것:** `.env`, `.env.local`, `.env.*` 실키 파일, `*.local` 등(`.gitignore` 참고).
- **키는 채팅/메일로 원문 공유하지 말고**, 변수 **이름**과 “어디서 발급받는지”만 공유하는 것을 권장합니다.
- 실수로 `.env`를 푸시했다면: `git rm --cached .env` 후 커밋하고, **키는 재발급**하는 것이 안전합니다.

키가 없을 때의 동작 요약은 아래 표를 참고하세요.

| 변수 | 없을 때(대략) |
|------|----------------|
| `WEATHER_API_KEY` | 단기예보 대신 보수적 기본값·폴백 안내 |
| `TOUR_API_KEY` | TourAPI 목록 비어 있을 수 있음, `data/destinations.json` 위주 |
| `AIR_KOREA_API_KEY` 등 | 대기(PM) 연동 생략 |
| `GOOGLE_PLACES_KEY` | Places·**리뷰** 연동 생략(다음 장소 후보 축소, 리뷰 기반 스코어 보조·코스 단계 리뷰 UI 비활성) |

### Google Places 리뷰 활성화 체크리스트

리뷰는 **키가 있고 장소가 식별 가능할 때**부터 바로 쓰입니다. 별도 “리뷰 전용 개발 단계”보다는 아래 조건 충족 여부를 보면 됩니다.

1. **환경 변수**  
   - `.env`에 **`GOOGLE_PLACES_KEY`** 설정(값은 Git에 올리지 않기).  
   - 기본 엔드포인트는 `.env.example`의 **`GOOGLE_PLACES_V1_ROOT`** 등을 따릅니다. 커스텀 루트를 쓸 때만 해당 변수를 맞춥니다.

2. **Google Cloud 콘솔**  
   - 프로젝트에 **Maps Platform(Places API New 등)** 사용이 켜져 있고, **결제 계정**이 연결돼 있어야 합니다.  
   - 키 제한(HTTP 리퍼러·IP)을 쓰는 경우, 로컬·배포 호스트에서 호출이 막히지 않는지 확인합니다.

3. **장소 데이터(좌표)**  
   - `GET /api/place-reviews` 및 코스 카드의 **`CourseStepGoogleReviews`**는 **위도·경도**가 있을 때 매칭이 안정적입니다. 좌표가 없으면 프론트에 “좌표 없어 리뷰를 불러올 수 없음”류 안내가 뜰 수 있습니다.

4. **키가 없을 때 동작**  
   - 백엔드: `lib/places.py`·`lib/review_features.py` 경로에서 리뷰 fetch·요약 보조를 **건너뜁니다**.  
   - 앱 전체는 동작하지만, **리뷰 텍스트 기반 가중·요약 라인**은 비어 있거나 약해질 수 있습니다.

5. **기대치·운영**  
   - Places 상세에서 내려주는 **리뷰 본문은 소수(대략 상위 몇 개)**이며, 전체 리뷰 DB를 가져오는 API가 아닙니다.  
   - 서버에는 **짧은 TTL 인메모리 캐시**(`lib/places.py`)가 있어 반복 호출을 줄입니다. 저장·재배포 정책은 [Google Maps Platform 이용약관](https://developers.google.com/maps/terms)을 따릅니다.  
   - 호출당 과금이 있으므로, 배포 후 **쿼ota·비용 알림**을 콘솔에서 설정하는 것을 권장합니다.

에어코리아 키 대체 시도 등 세부는 `lib/config.py`를 보세요.

**배포(Render 등):** 호스팅 콘솔에 동일 이름의 **환경 변수**를 넣으면 됩니다. `.env` 파일이 없어도 동작합니다.

---

## 추천 로직이 궁금할 때 (요약)

- **메인 관광지 랭킹:** 규칙 기반 가중 합 (`lib/main_scoring.py`, `lib/scoring_config.py`). `/api/recommend`의 장소 순위는 이 파이프라인을 탑니다.
- **완성 코스 카드(`top_course` 등):** `lib/daytrip_planner.py`와 `lib/course_view.py`에서 조합됩니다.
- **코스 단위 ML 재정렬(`course_rerank`):** 응답에 `course_rerank` 메타 필드는 있으나, 현재 저장소 기준으로는 **학습 모델 추론 없이 순서 유지·메타만 채우는 스텁**입니다 (`lib/course_rerank.py`).
- **next_scene ML:** `/api/course` 쪽 **선택 경로** (`app/ml/` 등). 홈 추천 랭킹과는 별개입니다.

다음 코스(식당·카페) 점수 요인은 `lib/next_course_scoring.py` 등을 참고하면 됩니다.

#### 메인 관광지 가중치(요약)

| 요인 | 비중 | 의미 |
|------|------|------|
| weather_fit | 35 | 날씨·대기 맥락 |
| goal_fit | 25 | 목적·동행 |
| distance_fit | 20 | 당일 거리 |
| time_fit | 10 | 시간대·일정 길이 |
| season_event_bonus | 10 | 골든아워·태그 등 |

#### 다음 코스(식당·카페) 가중치(요약)

| 요인 | 비중 |
|------|------|
| distance_fit | 30 |
| stage_fit | 25 |
| quality_fit | 20 |
| goal_fit | 15 |
| weather_fit | 10 |

### 검증 스크립트 (선택)

```bash
python scripts/validate_scoring_scenarios.py
```

---

## 선택 기능 (ML·실험)

- `requirements-ml.txt`, `scripts/train_next_scene_model.py`, `data/scenario_ml/` 등은 **필수가 아닙니다.**
- Ollama·코스 재정렬 번들 등은 `.env.example` 주석과 `lib/config.py`를 참고하세요.

---

## 문의·개선

구조나 API 변경 시 이 README의 **주요 API**, **디렉터리 표**, **프론트 모드**를 함께 갱신해 주시면 이후 팀원이 따라가기 쉽습니다.
