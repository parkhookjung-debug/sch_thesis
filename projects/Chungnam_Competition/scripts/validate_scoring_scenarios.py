# -*- coding: utf-8 -*-
"""
대표 시나리오로 메인·다음코스 점수와 설명이 자연스러운지 수동 점검용.
정확도 벤치마크가 아니라 휴리스틱 체감 검증.
실행: 프로젝트 루트에서  python scripts/validate_scoring_scenarios.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.intent_normalize import normalize_intent
from lib.main_scoring import compute_main_components, weighted_main_score, explain_main_destination, contribution_points
from lib.next_course_scoring import rank_next_places
from lib.scoring import calc_weather_score


def _fake_dest(outdoor: bool = True, tags=None, golden=False):
    tags = tags or ["자연", "산책"]
    return {
        "name": "테스트장소",
        "category": "outdoor" if outdoor else "indoor",
        "tags": tags,
        "weather_weights": {"sunny": 0.9, "rainy": 0.4},
        "coords": {"lat": 36.5, "lng": 127.0},
        "golden_hour_bonus": golden,
    }


def scenario(name: str, weather: dict, intent: dict, dest: dict):
    scores = calc_weather_score(weather)
    comp = compute_main_components(
        dest, weather, scores, intent, distance_fit=0.85, hour=int(weather.get("hour", 12))
    )
    total = weighted_main_score(comp)
    expl = explain_main_destination(
        dest, comp, contribution_points(comp), intent, weather, scores
    )
    print(f"\n=== {name} ===")
    print("total:", total, "breakdown:", comp)
    print("summary:", expl.get("summary", "")[:200])


def main():
    # 1) 맑음 + 힐링 + 반나절
    scenario(
        "1) sunny + healing + half-day",
        {"temp": 22, "precip_prob": 10, "sky": 1, "dust": 1, "hour": 14},
        normalize_intent("solo", "healing", "half-day", "car"),
        _fake_dest(True, ["자연", "힐링"]),
    )
    # 2) 비 + 가족 + 반나절
    scenario(
        "2) rainy + family + half-day",
        {"temp": 18, "precip_prob": 80, "sky": 4, "dust": 2, "hour": 11},
        normalize_intent("family", "kids", "half-day", "car"),
        _fake_dest(False, ["박물관", "실내"], False),
    )
    # 3) 일몰·사진 (골든아워)
    scenario(
        "3) sunset-oriented (golden hour)",
        {"temp": 20, "precip_prob": 5, "sky": 1, "dust": 1, "hour": 18},
        normalize_intent("couple", "photo", "2h", "car"),
        _fake_dest(True, ["야경", "전망"], True),
    )
    # 4) 실내 선호 + 나쁜 미세먼지
    scenario(
        "4) indoor + bad dust",
        {"temp": 24, "precip_prob": 15, "sky": 3, "dust": 4, "hour": 13},
        normalize_intent("solo", "indoor", "half-day", "public"),
        _fake_dest(False, ["전시", "미술"], False),
    )

    # 5)(6) 다음 코스 — 더미 후보 (API 없이 순위만)
    print("\n=== 5) next-course lunch-time restaurants (dummy) ===")
    scores = calc_weather_score(
        {"temp": 20, "precip_prob": 20, "sky": 1, "dust": 2, "hour": 12}
    )
    intent = normalize_intent("family", "healing", "half-day", "car")
    dummy = [
        {
            "name": "A식당",
            "address": "x",
            "rating": 4.2,
            "review_count": 120,
            "open_now": True,
            "photo_url": None,
            "types": ["restaurant", "korean_restaurant"],
            "lat": 36.51,
            "lng": 127.01,
        },
        {
            "name": "B카페",
            "address": "y",
            "rating": 4.8,
            "review_count": 2,
            "open_now": True,
            "photo_url": None,
            "types": ["cafe"],
            "lat": 36.5001,
            "lng": 127.0001,
        },
    ]
    ranked = rank_next_places(
        dummy,
        ref_lat=36.5,
        ref_lng=127.0,
        hour=12,
        intent=intent,
        scores=scores,
        expected_meal=True,
    )
    for r in ranked:
        print(r["name"], "score", r.get("next_course_score"), r.get("recommendation_reason_one_line", "")[:100])

    print("\n=== 6) next-course afternoon cafe (dummy) ===")
    ranked2 = rank_next_places(
        dummy,
        ref_lat=36.5,
        ref_lng=127.0,
        hour=16,
        intent=intent,
        scores=scores,
        expected_meal=False,
    )
    for r in ranked2:
        print(r["name"], "score", r.get("next_course_score"))


if __name__ == "__main__":
    main()
