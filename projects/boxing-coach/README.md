# 복싱 코치 — AI 스타일 매칭 + 코칭 웹

Bivol / Canelo / Ryan Garcia / LIM 네 명의 복싱 스타일 중, 사용자의 영상과 가장
닮은 코치를 자동으로 추천하고 그 코치 버전으로 자세·펀치 피드백을 합성해 주는
풀스택 웹 앱.

기존 Python 코치 시스템(`C:\Users\parkh\통합\VScode\복싱`)을 재사용하며,
모든 코치를 RTMPose(RTMO-s · COCO 17)로 통일된 형식으로 처리합니다.

```
복싱코치/
├── backend/        FastAPI + RTMPose
│   ├── app/
│   │   ├── pose/       포즈 추출, 자세 DNA, 펀치 DNA
│   │   ├── coaching/   자세 점수, 펀치 감지, 결과 영상 렌더
│   │   ├── matching/   사용자 ↔ 4명 코치 종합 점수
│   │   ├── api/        라우트, job 트래킹
│   │   ├── config.py
│   │   └── main.py
│   ├── scripts/
│   │   ├── extract_videos.py   원본 영상 → full_data CSV
│   │   └── build_dna.py         full_data → DNA + punch_DNA
│   └── data/
│       ├── full_data/           (생성됨)
│       ├── {coach}_DNA.csv      (생성됨)
│       └── {coach}_punch_DNA.csv (생성됨)
└── frontend/       React + Vite + Tailwind
    └── src/
        ├── pages/   Landing · Upload · Recommendation · CoachSelect · CoachingResult
        ├── api.js
        ├── App.jsx
        └── main.jsx
```

## 1. 데이터 준비 (최초 1회)

기존 영상은 `C:\Users\parkh\통합\VScode\복싱\*.mp4` 에 그대로 두면 됩니다.
RTMPose 모델은 첫 실행 시 자동으로 다운로드됩니다.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 1) 4명의 원본 영상 → RTMPose 키포인트 CSV 추출
python -m scripts.extract_videos

# 2) DNA + 펀치 DNA 산출
python -m scripts.build_dna
```

`backend/data/` 에 `bivol_DNA.csv`, `bivol_punch_DNA.csv`, ... 8개 파일이
생성되면 준비 완료.

## 2. 백엔드 실행

```powershell
cd backend
uvicorn app.main:app --reload --port 8001
```

스웨거 문서: <http://localhost:8001/docs>

> 8000 포트는 다른 프로젝트(예: 복싱게임)가 자주 쓰므로 기본을 8001로 잡았습니다. 포트를 바꾸려면 위 명령의 `--port` 와 `frontend/vite.config.js` 의 proxy 대상 포트를 같이 맞춰 주세요.

## 3. 프론트엔드 실행

```powershell
cd frontend
npm install
npm run dev
```

> **PowerShell 실행 정책 안내**  
> 처음 `npm` 명령을 쓸 때 `npm.ps1 ... UnauthorizedAccess` 에러가 나면
> 한 번만 다음을 실행하세요(현재 사용자에게만 적용, 관리자 권한 불필요):  
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`  
> 또한 Windows PowerShell 5.1 에서는 `&&` 가 동작하지 않으므로 명령을 줄
> 단위로 실행하거나 `;` 로 연결하세요 (`npm install; npm run dev`).

브라우저에서 <http://localhost:5173> 열기.

## 사용자 흐름

1. **랜딩** — 시작하기
2. **업로드** — 본인 복싱 영상 업로드(또는 스킵해서 코치 직접 선택)
3. **분석 진행률** — RTMPose 추출 → 자세/펀치 DNA 산출 → 4명과 z-score 거리 계산
4. **추천** — 종합 점수(자세 0.6 + 펀치 0.4)로 가장 닮은 코치 추천 + 4명 모두 점수 표시
5. **코칭 세션** — 영상 업로드 → 선택된 코치의 DNA로 자세 점수 · 펀치 감지 · 오버레이된 결과 영상

## 종합 점수 산식

- 자세 거리: 17개 메트릭의 z-score RMS  
  `z = (user - coach_avg) / coach_std`
- 펀치 거리: 펀치 타입별 6개 메트릭 z-score RMS 를 표본 수로 가중 평균
- similarity = `1 / (1 + distance)` (0~1)
- 종합 = `0.6 · pose_sim + 0.4 · punch_sim`
- 확신도(confidence) = softmax(score, temp=0.15)

펀치 표본이 부족하면 자세 점수만으로 평가합니다.

## API 요약

| 메서드 | 경로                   | 설명                              |
|--------|------------------------|-----------------------------------|
| GET    | `/api/coaches`         | 4명 코치 메타 + 데이터 준비 여부  |
| POST   | `/api/analyze-style`   | 영상 업로드 → 4명 점수 (job 반환) |
| POST   | `/api/coaching-session`| 영상 + coach → 결과 영상 (job)    |
| GET    | `/api/jobs/{id}`       | 진행률/상태/결과                  |
| GET    | `/api/result/{name}`   | 결과 mp4 다운로드                 |

## 의존성

- Python ≥ 3.10 (RTMPose 사용)
- Node ≥ 18
- `rtmlib` + `onnxruntime` (CPU. GPU 가속은 `onnxruntime-gpu` 로 교체)
- 한글 자막 렌더링은 Windows `Malgun Gothic` 폰트를 사용 (없으면 영문 fallback)

## 한계 / 후속 작업

- 코칭 세션은 **영상 업로드형 only** — 실시간 웹캠형(WebSocket 스트리밍) 후속
- 단일 프로세스 in-memory job 트래커 → 본격 배포 시 Redis/Celery 권장
- 음성 피드백(pyttsx3) 은 백엔드 콘솔용으로 비활성 — 후속에서 클라이언트 TTS 추가
- 코치별 영상 표본이 4~6편으로 적음 → DNA 신뢰도 보강 필요
