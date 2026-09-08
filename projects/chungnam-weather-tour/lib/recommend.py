# -*- coding: utf-8 -*-
"""
통합 추천 파이프라인 v2
- 충남 14개 시군 전체 병렬 수집
- destinations.json 수동 태그로 자동 태그 덮어씀 (하이브리드)
- 30분 인메모리 캐시 (API 과호출 방지)
"""
import os
import json
import time
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from lib.scoring import calc_weather_score
from lib.auto_tag import auto_tag
from lib.distance import calc_distance_score, get_user_coords

load_dotenv()

TOUR_API_KEY = os.getenv("TOUR_API_KEY")
BASE_URL     = "https://apis.data.go.kr/B551011/KorService2"

SIGUNGU_CODES = {
    "공주": 1, "금산": 2, "논산": 3, "당진": 4,
    "보령": 5, "부여": 6, "서산": 7, "서천": 8,
    "아산": 9, "예산": 11, "천안": 12, "청양": 13,
    "태안": 14, "홍성": 15,
}

DESTINATIONS_PATH = Path(__file__).parent.parent / "data" / "destinations.json"

# ── 캐시 ──────────────────────────────────────────────
_cache: dict = {}          # { cache_key: (timestamp, data) }
CACHE_TTL = 1800           # 30분


def _cache_get(key: str):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _cache_set(key: str, data):
    _cache[key] = (time.time(), data)


# ── 수동 태그 로드 ─────────────────────────────────────
def _load_manual() -> dict:
    """destinations.json을 {name: dest} 딕셔너리로 반환"""
    with open(DESTINATIONS_PATH, encoding="utf-8") as f:
        items = json.load(f)
    return {item["name"]: item for item in items}


# ── 단일 시군 수집 ─────────────────────────────────────
def _fetch_city(sigungu_code: int, num: int = 100) -> list:
    cache_key = f"city_{sigungu_code}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        "serviceKey":  TOUR_API_KEY,
        "numOfRows":   num,
        "pageNo":      1,
        "MobileOS":    "ETC",
        "MobileApp":   "ChungnamTour",
        "_type":       "json",
        "areaCode":    34,
        "sigunguCode": sigungu_code,
        "arrange":     "C",
    }
    try:
        r = requests.get(f"{BASE_URL}/areaBasedList2", params=params, timeout=10)
        data = r.json()
        if data["response"]["header"]["resultCode"] != "0000":
            return []
        body = data["response"]["body"]["items"]
        result = body["item"] if body else []
    except Exception:
        result = []

    # 숙박·쇼핑 제외
    result = [it for it in result if str(it.get("contenttypeid")) not in ("32", "38")]
    _cache_set(cache_key, result)
    return result


# ── 충남 전체 or 특정 도시 수집 ────────────────────────
def fetch_and_tag(city: str = "전체", num: int = 100) -> list:
    """
    city="전체"  → 14개 시군 병렬 수집 후 합산
    city="아산"  → 해당 도시만
    """
    manual = _load_manual()

    if city == "전체":
        codes = list(SIGUNGU_CODES.values())
    else:
        code = SIGUNGU_CODES.get(city)
        if code is None:
            raise ValueError(f"지원하지 않는 도시: {city}")
        codes = [code]

    # 병렬 수집
    raw_items = []
    with ThreadPoolExecutor(max_workers=7) as pool:
        futures = {pool.submit(_fetch_city, code, num): code for code in codes}
        for future in as_completed(futures):
            raw_items.extend(future.result())

    # 자동 태깅 + 수동 태그 덮어쓰기 (하이브리드)
    result = []
    for item in raw_items:
        tagged = auto_tag(item)
        name   = tagged["name"]

        if name in manual:
            # 수동 태그로 교체 (날씨 가중치, 태그, 카피 등)
            manual_data = manual[name].copy()
            # TourAPI에서만 얻을 수 있는 정보는 유지
            manual_data.setdefault("image",   tagged.get("image", ""))
            manual_data.setdefault("address", tagged.get("address", ""))
            manual_data["source"] = "manual"
            result.append(manual_data)
        else:
            result.append(tagged)

    # 수동 데이터 중 TourAPI에 없는 것도 추가 (도시 필터 적용)
    api_names = {d["name"] for d in result}
    for name, dest in manual.items():
        if name not in api_names:
            # 특정 도시 선택 시 해당 도시 수동 데이터만 추가
            if city != "전체" and dest.get("city") and dest["city"] != city:
                continue
            dest = dest.copy()
            dest["source"] = "manual"
            result.append(dest)

    return result


# ── 최종 매칭 ──────────────────────────────────────────
def match_from_api(weather: dict, city: str = "전체", top_n: int = 6,
                   user_lat: float = None, user_lng: float = None) -> dict:
    scores       = calc_weather_score(weather)
    destinations = fetch_and_tag(city)

    ref_city = city if city != "전체" else "아산"
    if user_lat is None or user_lng is None:
        user_lat, user_lng = get_user_coords(ref_city)

    WEATHER_W  = 0.6
    DISTANCE_W = 0.4

    results = []
    for dest in destinations:
        w = dest["weather_weights"]

        # Hard Filter
        if scores["is_raining"] and dest["category"] == "outdoor":
            continue
        if scores["is_dust_bad"] and w.get("fine_dust_limit") == "good":
            continue

        # 날씨 점수
        if dest["category"] == "outdoor":
            weather_score = scores["outdoor"] * w["sunny"]
        else:
            weather_score = scores["indoor"] * w["rainy"]
            # 야외 날씨가 좋을수록 실내 장소 페널티
            # outdoor=1.0이면 실내 점수 최대 50% 감소
            outdoor_penalty = scores["outdoor"] * 0.5
            weather_score = max(0.0, weather_score - outdoor_penalty)

        if dest.get("golden_hour_bonus") and scores["is_golden_hour"]:
            weather_score = min(weather_score + 0.3, 1.0)

        # 거리 점수
        lat = dest["coords"]["lat"]
        lng = dest["coords"]["lng"]
        dist_score, dist_km = calc_distance_score(lat, lng, user_lat, user_lng)

        total = round(weather_score * WEATHER_W + dist_score * DISTANCE_W, 3)

        results.append({
            **dest,
            "score":          total,
            "weather_score":  round(weather_score, 3),
            "distance_score": dist_score,
            "distance_km":    dist_km,
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "city":            city,
        "user_coords":     {"lat": user_lat, "lng": user_lng},
        "weather":         scores,
        "total_fetched":   len(destinations),
        "recommendations": results[:top_n],
    }
