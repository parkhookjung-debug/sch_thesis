# -*- coding: utf-8 -*-
"""
Google Places API (New) 연동
- 특정 좌표 근처 식당/카페 검색 (코스 추천)
- 장소명으로 리뷰 검색 (메인 장소 리뷰)
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY       = os.getenv("GOOGLE_PLACES_KEY")
NEARBY_URL    = "https://places.googleapis.com/v1/places:searchNearby"
TEXT_URL      = "https://places.googleapis.com/v1/places:searchText"

NEARBY_MASK = ",".join([
    "places.displayName", "places.rating", "places.userRatingCount",
    "places.formattedAddress", "places.location", "places.currentOpeningHours",
    "places.photos", "places.types", "places.priceLevel",
    "places.reviews", "places.websiteUri", "places.googleMapsUri",
])

REVIEW_MASK = ",".join([
    "places.displayName", "places.rating", "places.userRatingCount",
    "places.reviews", "places.websiteUri", "places.googleMapsUri",
    "places.currentOpeningHours",
])

_cache: dict = {}
CACHE_TTL = 1800


def _cache_get(key: str):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _cache_set(key, data):
    _cache[key] = (time.time(), data)


def _parse_reviews(raw: list) -> list[dict]:
    """리뷰 파싱 — publishTime 기준 최신순 정렬, 한국어 우선"""
    sorted_raw = sorted(raw, key=lambda x: x.get("publishTime", ""), reverse=True)
    result = []
    for r in sorted_raw:
        text = r.get("text", {}).get("text", "").strip()
        if not text:
            continue
        result.append({
            "author":   r.get("authorAttribution", {}).get("displayName", "익명"),
            "rating":   r.get("rating", 0),
            "text":     text,
            "relative": r.get("relativePublishTimeDescription", ""),
        })
    return result


def next_types(target_category: str, hour: int) -> list[str]:
    if target_category == "restaurant":
        if 17 < hour <= 22:
            return ["restaurant", "korean_restaurant", "japanese_restaurant"]
        return ["restaurant", "korean_restaurant", "chinese_restaurant"]
    elif target_category == "cafe":
        return ["cafe", "coffee_shop", "bakery"]
    elif target_category == "attraction":
        return ["tourist_attraction", "museum", "park", "art_gallery"]
    else:
        return ["restaurant", "korean_restaurant"]


# ── 코스 추천: 근처 장소 검색 ─────────────────────────────────
def fetch_next_places(
    lat: float, lng: float,
    current_category: str = "outdoor",
    hour: int = 12,
    radius_m: int = 5000,
    max_results: int = 5,
) -> list[dict]:
    if not API_KEY:
        return []

    types = next_types(current_category, hour)
    key   = f"nearby_{round(lat,3)}_{round(lng,3)}_{'_'.join(types[:1])}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    payload = {
        "includedTypes":      types[:3],
        "maxResultCount":     max_results,
        "languageCode":       "ko",
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius_m),
            }
        },
        "rankPreference": "POPULARITY",
    }
    headers = {
        "Content-Type":    "application/json",
        "X-Goog-Api-Key":  API_KEY,
        "X-Goog-FieldMask": NEARBY_MASK,
    }

    try:
        r = requests.post(NEARBY_URL, json=payload, headers=headers, timeout=8)
        r.raise_for_status()
        raw = r.json().get("places", [])
    except Exception:
        return []

    results = []
    for p in raw:
        rating  = p.get("rating", 0)
        reviews = p.get("userRatingCount", 0)
        if rating < 3.0 or reviews < 3:
            continue

        photo_url = None
        photos = p.get("photos", [])
        if photos:
            ref = photos[0].get("name", "")
            if ref:
                photo_url = (
                    f"https://places.googleapis.com/v1/{ref}/media"
                    f"?maxHeightPx=400&key={API_KEY}"
                )

        open_now = None
        oh = p.get("currentOpeningHours", {})
        if "openNow" in oh:
            open_now = oh["openNow"]

        results.append({
            "name":         p["displayName"]["text"],
            "address":      p.get("formattedAddress", ""),
            "rating":       rating,
            "review_count": reviews,
            "open_now":     open_now,
            "photo_url":    photo_url,
            "types":        p.get("types", []),
            "lat":          p["location"]["latitude"],
            "lng":          p["location"]["longitude"],
            "reviews":      _parse_reviews(p.get("reviews", [])),
            "website":      p.get("websiteUri", ""),
            "google_maps":  p.get("googleMapsUri", ""),
        })

    _cache_set(key, results)
    return results


# ── 메인 장소 리뷰: 장소명 Text Search ───────────────────────
def fetch_place_reviews(name: str, lat: float, lng: float, address: str = "") -> dict:
    """장소명으로 Google Places 검색 → 리뷰(최신순, 한국어) 반환"""
    if not API_KEY:
        return {}

    key = f"review_{name}_{round(lat,3)}_{round(lng,3)}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    # 주소에서 시/군 추출해 쿼리에 포함 → 동명 타지역 장소 필터링
    city_hint = ""
    if address:
        parts = address.replace("충청남도 ", "").split()
        if parts:
            city_hint = f" {parts[0]}"

    payload = {
        "textQuery":      f"{name}{city_hint}",
        "languageCode":   "ko",
        "maxResultCount": 1,
        # locationBias(우선순위) → locationRestriction(엄격 제한)으로 변경
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 5000.0,   # 5km 이내만 허용
            }
        },
    }
    headers = {
        "Content-Type":    "application/json",
        "X-Goog-Api-Key":  API_KEY,
        "X-Goog-FieldMask": REVIEW_MASK,
    }

    try:
        r = requests.post(TEXT_URL, json=payload, headers=headers, timeout=8)
        r.raise_for_status()
        places = r.json().get("places", [])
        if not places:
            return {}
        p = places[0]
    except Exception:
        return {}

    open_now = None
    oh = p.get("currentOpeningHours", {})
    if "openNow" in oh:
        open_now = oh["openNow"]

    result = {
        "rating":       p.get("rating", 0),
        "review_count": p.get("userRatingCount", 0),
        "reviews":      _parse_reviews(p.get("reviews", [])),
        "website":      p.get("websiteUri", ""),
        "google_maps":  p.get("googleMapsUri", ""),
        "open_now":     open_now,
    }
    _cache_set(key, result)
    return result
