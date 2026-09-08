# -*- coding: utf-8 -*-
"""
다음 코스(식당·카페) 점수: 거리·단계·품질·목적·날씨 보조.

평점만 쓰지 않고 리뷰 수로 신뢰도를 스무딩한다 (단순 베이지안 근사).
"""
from __future__ import annotations

import math
from typing import Any

from lib.distance import haversine
from lib.scoring_config import NEXT_COURSE_WEIGHTS


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def quality_fit_rating_reviews(
    rating: float | None,
    reviews: int,
) -> float:
    """
    0~1: 평점을 5점 만점으로 정규화하고,
    리뷰 수가 많을수록 그 신뢰를 반영 (소표본 과대평가 완화).
    """
    if rating is None or rating <= 0:
        r_norm = 0.42
    else:
        r_norm = _clamp01(rating / 5.0)
    # 신뢰도: 1 - exp(-reviews/k)
    conf = 1.0 - math.exp(-max(0, reviews) / 18.0)
    # 저신뢰일 때는 중간값 쪽으로 당김
    blended = 0.55 * r_norm + 0.45 * (r_norm * (0.35 + 0.65 * conf))
    return round(_clamp01(blended), 4)


def _distance_fit_km(km: float, max_km: float = 12.0) -> float:
    if km < 0:
        return 0.55
    return _clamp01(1.0 - min(km, max_km) / max_km)


def _meal_stage(hour: int) -> str:
    if 11 <= hour <= 14:
        return "lunch"
    if 17 <= hour <= 21:
        return "dinner"
    if 15 <= hour <= 17:
        return "tea"
    if hour >= 21 or hour < 10:
        return "late_snack"
    return "generic"


def compute_stage_fit(
    hour: int,
    place_types: list[str],
    expected_meal: bool,
) -> float:
    """
    expected_meal: 이번 검색이 식당 위주인지(식사 단계) vs 카페 위주인지.
    """
    types_l = [t.lower() for t in place_types]
    meal_like = any(
        x in types_l
        for x in (
            "restaurant",
            "korean_restaurant",
            "japanese_restaurant",
            "chinese_restaurant",
            "meal_takeaway",
        )
    )
    cafe_like = any(x in types_l for x in ("cafe", "coffee_shop", "bakery"))

    st = _meal_stage(hour)

    if expected_meal:
        if st in ("lunch", "dinner") and meal_like:
            return 0.95
        if st == "tea" and cafe_like:
            return 0.55
        if meal_like:
            return 0.78
        return 0.45

    # 카페·디저트 단계 기대
    if st == "tea" and cafe_like:
        return 0.95
    if cafe_like:
        return 0.82
    if meal_like and st in ("lunch", "dinner"):
        return 0.72
    return 0.58


def compute_next_goal_fit(
    place_types: list[str],
    intent: dict[str, str],
) -> float:
    """Places 타입과 여행 목적의 약한 정합."""
    g = intent.get("trip_goal", "healing")
    types_l = " ".join(place_types).lower()
    s = 0.5
    if g == "kids" and any(
        x in types_l for x in ("restaurant", "meal_takeaway", "bakery")
    ):
        s += 0.18
    if g == "healing" and "cafe" in types_l:
        s += 0.12
    if g == "photo" and "cafe" in types_l:
        s += 0.1
    if g == "indoor":
        s += 0.08
    return _clamp01(s)


def compute_next_weather_fit(
    scores: dict[str, Any] | None,
    place_types: list[str],
) -> float:
    """비·미세먼지 시 실내 성향 식음료에 유리하다는 보조 신호."""
    if not scores:
        return 0.55
    types_l = [t.lower() for t in place_types]
    indoorish = any(x in types_l for x in ("cafe", "restaurant", "bakery"))
    w = 0.55
    if scores.get("is_raining") and indoorish:
        w += 0.28
    if scores.get("is_dust_bad") and indoorish:
        w += 0.15
    return _clamp01(w)


def score_next_place(
    place: dict[str, Any],
    *,
    ref_lat: float,
    ref_lng: float,
    hour: int,
    intent: dict[str, str],
    scores: dict[str, Any] | None,
    expected_meal: bool,
) -> tuple[float, dict[str, float], dict[str, float]]:
    """최종 0~1 점수, 부분 점수, 가중 기여."""
    lat = float(place["lat"])
    lng = float(place["lng"])
    km = haversine(ref_lat, ref_lng, lat, lng)
    df = _distance_fit_km(km)

    qf = quality_fit_rating_reviews(
        place.get("rating") if place.get("rating") else None,
        int(place.get("review_count") or 0),
    )
    sf = compute_stage_fit(hour, place.get("types") or [], expected_meal)
    gf = compute_next_goal_fit(place.get("types") or [], intent)
    wf = compute_next_weather_fit(scores, place.get("types") or [])

    comp = {
        "distance_fit": df,
        "stage_fit": sf,
        "quality_fit": qf,
        "goal_fit": gf,
        "weather_fit": wf,
    }
    total = sum(comp[k] * (NEXT_COURSE_WEIGHTS[k] / 100.0) for k in NEXT_COURSE_WEIGHTS)
    total = round(_clamp01(total), 4)

    contrib = {
        k: round(comp[k] * (NEXT_COURSE_WEIGHTS[k] / 100.0), 4) for k in NEXT_COURSE_WEIGHTS
    }
    return total, comp, contrib


def explain_next_place(
    place: dict[str, Any],
    components: dict[str, float],
    contributions: dict[str, float],
    km: float,
    expected_meal: bool,
    hour: int,
) -> str:
    tops = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:2]
    parts: list[str] = []
    if tops and tops[0][0] == "distance_fit":
        parts.append(f"직전 장소에서 약 {km:.1f}km로 이동 부담이 상대적으로 작습니다.")
    if expected_meal and 11 <= hour <= 14:
        parts.append("점심 시간대에 식사 코스로 묶기 좋은 후보입니다.")
    elif (not expected_meal) and 15 <= hour <= 18:
        parts.append("오후에는 카페·디저트 단계로 이어지기 쉬운 유형입니다.")

    q = components.get("quality_fit", 0)
    if q >= 0.72:
        parts.append("평점·리뷰 수를 함께 본 신뢰도가 비교적 안정적입니다.")
    elif q < 0.55:
        parts.append("평가 표본이 적을 수 있어 현장 확인을 권장합니다.")

    if not parts:
        parts.append("거리·단계·품질·목적을 함께 반영한 다음 코스 휴리스틱 점수입니다.")
    return " ".join(parts[:3])


def rank_next_places(
    places: list[dict[str, Any]],
    *,
    ref_lat: float,
    ref_lng: float,
    hour: int,
    intent: dict[str, str],
    scores: dict[str, Any] | None,
    expected_meal: bool,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for p in places:
        total, comp, contrib = score_next_place(
            p,
            ref_lat=ref_lat,
            ref_lng=ref_lng,
            hour=hour,
            intent=intent,
            scores=scores,
            expected_meal=expected_meal,
        )
        km = haversine(ref_lat, ref_lng, float(p["lat"]), float(p["lng"]))
        expl = explain_next_place(p, comp, contrib, km, expected_meal, hour)
        enriched.append(
            {
                **p,
                "next_course_score": total,
                "score_breakdown": comp,
                "score_contributions": contrib,
                "recommendation_reason_one_line": expl,
                "distance_from_prev_km": round(km, 2),
            }
        )
    enriched.sort(key=lambda x: x.get("next_course_score", 0), reverse=True)
    return enriched
