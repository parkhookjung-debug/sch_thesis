# -*- coding: utf-8 -*-
"""
코스 이어가기 엔진 예시 시나리오(결정론적 출력 확인용).

실행: python scripts/sample_course_outputs.py
(GOOGLE_PLACES_KEY 없으면 Places 후보는 비어 있을 수 있음 — 단계·trip_state는 확인 가능)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.course_continuation import (  # noqa: E402
    build_course_payload,
    estimate_trip_state,
    decide_next_stage,
    resolve_spot_metadata,
)
from lib.intent_normalize import normalize_intent  # noqa: E402
from lib.scoring import calc_weather_score  # noqa: E402


def _noop_fetch(lat, lng, types):
    return [], 0.0, True, "샘플: Places 호출 생략"


SCENARIOS = [
    {
        "name": "힐링 + 반나절 + 야외(점심 무렵)",
        "spot_id": "gokgyocheon",
        "hour": 12,
        "intent": ("solo", "healing", "half-day", "car"),
        "weather": {"temp": 22, "precip_prob": 10, "sky": 1, "dust": 1, "hour": 12},
    },
    {
        "name": "가족 + 키즈 목적 + 비 오는 날",
        "spot_id": None,
        "spot_name": "곡교천 은행나무길",
        "hour": 14,
        "intent": ("family", "kids", "half-day", "car"),
        "weather": {"temp": 18, "precip_prob": 75, "sky": 4, "dust": 2, "hour": 14},
    },
    {
        "name": "사진 + 늦은 오후",
        "spot_id": "gongju_fortress",
        "hour": 18,
        "intent": ("couple", "photo", "full-day", "car"),
        "weather": {"temp": 24, "precip_prob": 5, "sky": 1, "dust": 1, "hour": 18},
    },
    {
        "name": "미세먼지 나쁨 → 실내 전환",
        "spot_id": "gokgyocheon",
        "hour": 15,
        "intent": ("family", "walking", "half-day", "public"),
        "weather": {"temp": 26, "precip_prob": 15, "sky": 3, "dust": 4, "hour": 15},
    },
]


def main() -> None:
    for sc in SCENARIOS:
        intent = normalize_intent(*sc["intent"])
        w = sc["weather"]
        scores = calc_weather_score(w)
        spot = resolve_spot_metadata(sc.get("spot_id"), sc.get("spot_name"))
        spot.setdefault("category", "outdoor")
        ts = estimate_trip_state(
            spot, sc["hour"], intent, scores, w["precip_prob"], w["dust"]
        )
        stage, title, why = decide_next_stage(
            spot, ts, sc["hour"], intent, scores, w["precip_prob"], w["dust"]
        )
        print("===", sc["name"], "===")
        print(json.dumps({"trip_state": ts, "next_stage": {"type": stage, "title": title, "why": why}}, ensure_ascii=False, indent=2))
        payload = build_course_payload(
            lat=36.79,
            lng=127.02,
            category=spot.get("category", "outdoor"),
            hour=sc["hour"],
            intent=intent,
            scores=scores,
            precip_prob=float(w["precip_prob"]),
            dust=int(w["dust"]),
            temp=float(w["temp"]),
            spot_id=sc.get("spot_id"),
            spot_name=sc.get("spot_name"),
            fetch_places_fn=_noop_fetch,
        )
        keys = (
            "next_scene",
            "next_stage",
            "meal_style",
            "cuisine_bias",
            "after_this",
            "primary_recommendation",
            "meta",
        )
        print(json.dumps({k: payload[k] for k in keys if k in payload}, ensure_ascii=False, indent=2))
        print()


if __name__ == "__main__":
    main()
