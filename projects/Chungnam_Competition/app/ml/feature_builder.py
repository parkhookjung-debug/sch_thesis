# -*- coding: utf-8 -*-
"""
`next_scene` 학습·추론용 피처 행 생성.

- 시나리오 CSV의 열 이름과 동일한 키를 맞춘다 (chungnam_feature_roles.csv).
- 라벨은 **약지도·합성 시나리오** 전제이며 실사용 행동을 대표하지 않는다.
"""
from __future__ import annotations

from typing import Any


def _duration_type(intent: dict[str, str]) -> str:
    d = (intent.get("duration") or "half-day").strip().lower()
    if d == "2h":
        return "2h"
    if d == "full-day":
        return "full_day"
    return "half_day"


def _weather_type(precip_prob: float, scores: dict[str, Any] | None) -> str:
    s = scores or {}
    if s.get("is_raining") or precip_prob >= 70:
        return "rainy"
    if precip_prob >= 35:
        return "cloudy"
    return "sunny"


def _dust_level(dust: int) -> str:
    if dust <= 1:
        return "good"
    if dust == 2:
        return "normal"
    return "bad"


def _companion_type(intent: dict[str, str]) -> str:
    c = (intent.get("companion") or "solo").strip().lower()
    if c == "family":
        return "family_medium"
    if c == "couple":
        return "couple"
    if c == "friends":
        return "friends"
    return "solo"


def _trip_goal_scenario(intent: dict[str, str]) -> str:
    g = (intent.get("trip_goal") or "healing").strip().lower()
    if g == "culture":
        return "experience"
    if g == "kids":
        return "family"
    if g == "walking":
        return "healing"
    return g


def _current_place_type(spot_meta: dict[str, Any]) -> str:
    cat = str(spot_meta.get("category") or "outdoor").lower()
    tags = [str(t).lower() for t in (spot_meta.get("tags") or [])]
    blob = cat + " " + " ".join(tags)
    if "축제" in blob or "festival" in blob or "행사" in blob:
        return "festival"
    if cat == "indoor" or "박물관" in blob or "전시" in blob:
        return "indoor_culture"
    if "사진" in blob or "photo" in blob or "전망" in blob:
        return "photo_spot"
    if "카페" in blob or "cafe" in blob:
        return "cafe_area"
    if "역사" in blob or "유적" in blob:
        return "history"
    if cat == "outdoor":
        return "nature"
    return "indoor_culture"


def _activity_level_scenario(spot_meta: dict[str, Any]) -> str:
    a = str(spot_meta.get("activity_level") or "moderate").lower()
    if a in ("high",):
        return "high"
    if a in ("low",):
        return "low"
    if a in ("moderate", "medium"):
        return "medium"
    return "medium"


def row_from_scenario_context(
    *,
    spot_meta: dict[str, Any],
    trip_state: dict[str, float],
    hour: int,
    intent: dict[str, str],
    scores: dict[str, Any] | None,
    precip_prob: float,
    dust: int,
    temp: float,
) -> dict[str, Any]:
    """시나리오 CSV(`duration_type`, `weather_type`, …)와 동일 키로 추론 행을 만든다. temp는 스키마에 없어 무시."""
    _ = temp
    s = scores or {}
    comp = _companion_type(intent)
    kids_tol = 1.0 if comp.startswith("family") else 0.5
    return {
        "duration_type": _duration_type(intent),
        "weather_type": _weather_type(float(precip_prob), s),
        "rain_prob": float(precip_prob),
        "dust_level": _dust_level(int(dust)),
        "hour": int(hour),
        "trip_goal": _trip_goal_scenario(intent),
        "current_place_type": _current_place_type(spot_meta),
        "companion_type": comp,
        "adult_count": 1,
        "child_count": 1 if comp.startswith("family") and "large" in comp else 0,
        "transport": str(intent.get("transport") or "car").lower(),
        "activity_level": _activity_level_scenario(spot_meta),
        "avg_stay_minutes": float(spot_meta.get("avg_stay_minutes") or 60.0),
        "indoor_ratio": float(spot_meta.get("indoor_ratio") or 0.2),
        "event_active": 0.0,
        "event_schedule_known": 0.0,
        "hunger": float(trip_state.get("need_meal", 0.0)),
        "fatigue": float(trip_state.get("need_rest", 0.0)),
        "need_indoor": float(trip_state.get("need_indoor", 0.0)),
        "keep_mood": float(trip_state.get("keep_healing_mood", 0.0)),
        "move_tolerance": float(trip_state.get("move_tolerance", 0.5)),
        "kids_tolerance": kids_tol,
        "photo_motivation": float(spot_meta.get("photo_fit") or 0.5),
    }


def row_from_course_context(
    *,
    spot_meta: dict[str, Any],
    trip_state: dict[str, float],
    hour: int,
    intent: dict[str, str],
    scores: dict[str, Any] | None,
    precip_prob: float,
    dust: int,
    temp: float,
) -> dict[str, Any]:
    """API 코스 이어가기와 동일한 맥락에서 단일 행(dict)을 만든다."""
    s = scores or {}
    return {
        "hour": int(hour),
        "precip_prob": float(precip_prob),
        "dust": int(dust),
        "temp": float(temp),
        "companion": str(intent.get("companion") or "solo"),
        "trip_goal": str(intent.get("trip_goal") or "healing"),
        "duration": str(intent.get("duration") or "half-day"),
        "transport": str(intent.get("transport") or "car"),
        "spot_category": str(spot_meta.get("category") or "outdoor").lower(),
        "activity_level": str(spot_meta.get("activity_level") or "moderate").lower(),
        "need_meal": float(trip_state.get("need_meal", 0.0)),
        "need_rest": float(trip_state.get("need_rest", 0.0)),
        "need_indoor": float(trip_state.get("need_indoor", 0.0)),
        "keep_healing_mood": float(trip_state.get("keep_healing_mood", 0.0)),
        "move_tolerance": float(trip_state.get("move_tolerance", 0.0)),
        "indoor_ratio": float(spot_meta.get("indoor_ratio") or 0.0),
        "avg_stay_minutes": float(spot_meta.get("avg_stay_minutes") or 0.0),
        "photo_fit": float(spot_meta.get("photo_fit") or 0.0),
        "healing_fit": float(spot_meta.get("healing_fit") or 0.0),
        "golden_hour_bonus": 1.0 if spot_meta.get("golden_hour_bonus") else 0.0,
        "is_raining": 1.0 if s.get("is_raining") else 0.0,
        "is_dust_bad": 1.0 if s.get("is_dust_bad") else 0.0,
        "is_golden_hour": 1.0 if s.get("is_golden_hour") else 0.0,
    }


def assert_columns_present(row: dict[str, Any], feature_columns: list[str]) -> None:
    missing = [c for c in feature_columns if c not in row]
    if missing:
        raise KeyError(f"Missing feature keys: {missing}")
