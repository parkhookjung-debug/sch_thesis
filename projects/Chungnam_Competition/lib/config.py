# -*- coding: utf-8 -*-
"""
중앙 환경 설정 로더. API 키·베이스 URL은 여기서만 읽고, 소스에 비밀을 넣지 않는다.
python-dotenv는 이 모듈에서 한 번만 호출한다.
"""
from __future__ import annotations

import json
from typing import Any
import os
import sys
from pathlib import Path
from urllib.parse import unquote

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _strip_encoded_key(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = raw.strip().strip('"').strip("'")
    if not s:
        return None
    return unquote(s) if "%" in s else s


def _first_encoded_key(*env_names: str) -> str | None:
    for name in env_names:
        v = _strip_encoded_key(os.getenv(name))
        if v:
            return v
    return None


def _env_str(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return str(v).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    try:
        return int(str(v).strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    try:
        return float(str(v).strip())
    except ValueError:
        return default


def _requests_ssl_verify() -> bool | str:
    """
    requests의 verify 인자.
    Windows 등에서 시스템 CA가 비어 Google Places 등 HTTPS가 실패할 때 certifi 번들을 쓴다.
    개발 전용 탈출구: REQUESTS_SSL_INSECURE=1 (운영에서는 사용 금지).
    """
    if _env_bool("REQUESTS_SSL_INSECURE"):
        print(
            "[config] WARNING: REQUESTS_SSL_INSECURE=1 — HTTPS 인증서 검증을 끕니다. 운영 환경에서는 사용하지 마세요.",
            file=sys.stderr,
        )
        return False
    try:
        import certifi

        return certifi.where()
    except ImportError:
        return True


# ── 기본 URL (공공데이터·Google 공개 엔드포인트, 비밀 아님) ───────────────
_DEFAULT_WEATHER_SERVICE_ROOT = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
_DEFAULT_TOUR_BASE = "https://apis.data.go.kr/B551011/KorService2"
_DEFAULT_AIR_SERVICE_ROOT = "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc"
_DEFAULT_GOOGLE_PLACES_SEARCH = "https://places.googleapis.com/v1/places:searchNearby"
_DEFAULT_GOOGLE_PLACES_V1 = "https://places.googleapis.com/v1"


def _weather_forecast_url() -> str:
    """getVilageFcst 전체 URL."""
    full = _env_str("WEATHER_FORECAST_URL")
    if full:
        return full.rstrip()
    root = _env_str("WEATHER_BASE_URL", _DEFAULT_WEATHER_SERVICE_ROOT)
    return f"{root.rstrip('/')}/getVilageFcst"


def _tour_base() -> str:
    return _env_str("TOUR_BASE_URL", _DEFAULT_TOUR_BASE).rstrip("/")


def _air_ctprvn_url() -> str:
    full = _env_str("AIR_KOREA_FORECAST_URL")
    if full:
        return full.rstrip()
    root = _env_str("AIR_KOREA_BASE_URL", _DEFAULT_AIR_SERVICE_ROOT)
    return f"{root.rstrip('/')}/getCtprvnRltmMesureDnsty"


def _google_places_search_url() -> str:
    return _env_str("GOOGLE_PLACES_BASE_URL", _DEFAULT_GOOGLE_PLACES_SEARCH).rstrip()


def _google_places_v1_root() -> str:
    return _env_str("GOOGLE_PLACES_V1_ROOT", _DEFAULT_GOOGLE_PLACES_V1).rstrip("/")


class Settings:
    """런타임 설정(한 번 로드)."""

    def __init__(self) -> None:
        self.project_root: Path = _PROJECT_ROOT
        self.debug: bool = _env_bool("DEBUG", default=False)
        self.port: int = _env_int("PORT", 8000)
        # UI: Vite 빌드( frontend/dist )가 있으면 기본으로 dist, 없으면 static(레거시 HTML).
        # 강제하려면 FRONTEND_UI=static | dist
        _ui = (_env_str("FRONTEND_UI") or "").strip().lower()
        if _ui in ("static", "dist"):
            self.frontend_ui = _ui
        else:
            _dist_index = _PROJECT_ROOT / "frontend" / "dist" / "index.html"
            self.frontend_ui = "dist" if _dist_index.is_file() else "static"

        # 코스 단위 재정렬(학습) — /api/recommend 후보 순서. 번들 없으면 lib.course_rerank 가 규칙 순서 유지.
        self.course_rerank_model_dir: str | None = _env_str("COURSE_RERANK_MODEL_DIR")

        # 시나리오 학습 next_scene 모델 (약지도·합성). /api/course 실험·레거시 경로 전용.
        # 홈 첫 추천(/api/recommend)과 역할을 섞지 않는다.
        self.use_next_scene_model: bool = _env_bool("NEXT_SCENE_MODEL", False)
        self.next_scene_model_dir: str | None = _env_str("NEXT_SCENE_MODEL_DIR")
        self.next_scene_model_min_confidence: float = _env_float(
            "NEXT_SCENE_MODEL_MIN_CONFIDENCE", 0.38
        )

        # 선택: Ollama(로컬) — 설명문 생성만, 랭킹에 사용하지 않음
        self.ollama_base_url: str | None = _env_str("OLLAMA_BASE_URL")
        self.ollama_model: str = (_env_str("OLLAMA_MODEL", "llama3.2") or "llama3.2")

        self.weather_api_key: str | None = _strip_encoded_key(os.getenv("WEATHER_API_KEY"))
        self.tour_api_key: str | None = _strip_encoded_key(os.getenv("TOUR_API_KEY"))
        self.google_places_key: str | None = _strip_encoded_key(os.getenv("GOOGLE_PLACES_KEY"))

        # 에어코리아: 전용 키 → 공용 키 → (선택) 기상청과 동일 키 재사용
        self.air_korea_api_key: str | None = _first_encoded_key(
            "AIR_KOREA_API_KEY",
            "PUBLIC_DATA_SERVICE_KEY",
            "WEATHER_API_KEY",
        )

        self.weather_forecast_url: str = _weather_forecast_url()
        self.tour_base_url: str = _tour_base()
        self.tour_api_timeout_seconds: float = max(
            1.0,
            min(10.0, _env_float("TOUR_API_TIMEOUT_SECONDS", 3.0)),
        )
        self.air_ctprvn_url: str = _air_ctprvn_url()
        self.google_places_search_url: str = _google_places_search_url()
        self.google_places_v1_root: str = _google_places_v1_root()
        self.requests_ssl_verify: bool | str = _requests_ssl_verify()
        # requests는 기본적으로 HTTP_PROXY/HTTPS_PROXY 환경변수를 자동 사용한다.
        # 로컬 개발·일부 샌드박스에서는 127.0.0.1:9 같은 더미 프록시가 잡혀 공공데이터/Google 호출이 전부 실패한다.
        # 실제 프록시가 필요한 환경에서만 REQUESTS_TRUST_ENV=1 로 켠다.
        self.requests_trust_env: bool = _env_bool("REQUESTS_TRUST_ENV", False)
        # /api/recommend 첫 응답 속도 보호: 리뷰/사진 보강은 상위 일부만 동기 처리.
        # 자세한 리뷰는 장소 상세 모달에서 지연 조회한다.
        self.main_places_review_max_fetch: int = max(
            0,
            min(8, _env_int("MAIN_PLACES_REVIEW_MAX_FETCH", 3)),
        )

        _story_rel = (
            _env_str(
                "STORYTELLING_CSV_PATH",
                "한국관광공사_관광 스토리텔링 DB 정보_20160906.csv",
            )
            or "한국관광공사_관광 스토리텔링 DB 정보_20160906.csv"
        )
        _sp = Path(_story_rel)
        self.storytelling_csv_path: str = str(_sp if _sp.is_absolute() else _PROJECT_ROOT / _sp)

        self.citytour_restaurant_api_key: str | None = _strip_encoded_key(
            os.getenv("CITYTOUR_RESTAURANT_API_KEY")
        )
        self.citytour_restaurant_base_url: str | None = _env_str("CITYTOUR_RESTAURANT_BASE_URL")
        self.citytour_restaurant_path: str = (_env_str("CITYTOUR_RESTAURANT_PATH", "") or "").strip()
        self.citytour_restaurant_key_param: str = (
            _env_str("CITYTOUR_RESTAURANT_KEY_PARAM", "serviceKey") or "serviceKey"
        )
        self.citytour_restaurant_send_coords: bool = _env_bool("CITYTOUR_RESTAURANT_SEND_COORDS", True)
        self.citytour_restaurant_extra_params: dict[str, Any] = {}
        _ct_ex = _env_str("CITYTOUR_RESTAURANT_EXTRA_PARAMS")
        if _ct_ex:
            try:
                parsed = json.loads(_ct_ex)
                if isinstance(parsed, dict):
                    self.citytour_restaurant_extra_params = parsed
            except json.JSONDecodeError:
                pass

    def log_config_summary(self) -> None:
        """DEBUG일 때만 키 존재 여부를 로그(값은 절대 출력하지 않음)."""
        if not self.debug:
            return
        def _flag(x: str | None) -> str:
            return "set" if x else "missing"
        story_ok = Path(self.storytelling_csv_path).is_file()
        msg = (
            "[config] DEBUG=true — key presence: "
            f"WEATHER={_flag(self.weather_api_key)} "
            f"TOUR={_flag(self.tour_api_key)} "
            f"AIR={_flag(self.air_korea_api_key)} "
            f"GOOGLE_PLACES={_flag(self.google_places_key)} "
            f"CITYTOUR_REST={_flag(self.citytour_restaurant_api_key)} "
            f"STORYTELLING_CSV={'ok' if story_ok else 'missing'}"
        )
        print(msg, file=sys.stderr)


settings = Settings()


def requests_session():
    import requests

    s = requests.Session()
    s.trust_env = settings.requests_trust_env
    return s


def request_get(url: str, **kwargs):
    with requests_session() as s:
        return s.get(url, **kwargs)


def request_post(url: str, **kwargs):
    with requests_session() as s:
        return s.post(url, **kwargs)

if settings.debug and not (_PROJECT_ROOT / ".env").exists():
    print(
        "[config] .env not found at project root; using OS environment only.",
        file=sys.stderr,
    )
