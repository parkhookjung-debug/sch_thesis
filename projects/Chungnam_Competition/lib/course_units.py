# -*- coding: utf-8 -*-
"""완성 코스 단위 메타(이동 부담·날씨 적합 등) — 규칙 기반 휴리스틱."""
from __future__ import annotations

from typing import Any

from lib.distance import haversine


def movement_burden_label(
    places: list[dict[str, Any]],
    user_lat: float,
    user_lng: float,
) -> str:
    """코스 내 대략 이동 거리(km) 합으로 부담 등급(내비 최적 경로 아님)."""
    if not places:
        return "알 수 없음"
    total_km = 0.0
    cur_lat, cur_lng = float(user_lat), float(user_lng)
    for p in places:
        coords = p.get("coords") or {}
        lat = float(coords.get("lat") or 0)
        lng = float(coords.get("lng") or 0)
        if lat == 0 and lng == 0:
            continue
        total_km += haversine(cur_lat, cur_lng, lat, lng)
        cur_lat, cur_lng = lat, lng
    if total_km < 12:
        return "가벼운 편"
    if total_km < 28:
        return "보통"
    if total_km < 55:
        return "다소 있음"
    return "이동 거리가 꽤 길어요"


def weather_fit_label(weather: dict[str, Any], scores: dict[str, Any]) -> str:
    pp = float(weather.get("precip_prob", 0) or 0)
    dust = int(weather.get("dust", 1) or 1)
    if scores.get("is_raining") or pp >= 60:
        return "비 가능성이 높아요 — 실내·짧은 동선을 추천했어요"
    if pp >= 50:
        return "강수를 염두에 두고 실내·혼합으로 맞췄어요"
    if pp >= 30:
        return "가끔 비 가능 — 짧게 야외·실내를 섞기 좋아요"
    if dust >= 3:
        return "미세먼지 나쁨 — 실내·마스크를 고려해요"
    return "오늘 날씨엔 가볍게 둘러보기 좋은 편이에요"


def indoor_outdoor_balance(places: list[dict[str, Any]]) -> str:
    if not places:
        return "혼합"
    n_in = sum(1 for p in places if (p.get("category") or "") == "indoor")
    n_out = len(places) - n_in
    if n_in == 0:
        return "야외 위주"
    if n_out == 0:
        return "실내 위주"
    return "실내·야외 혼합"


def course_feature_snapshot(
    *,
    places: list[dict[str, Any]],
    intent: dict[str, str],
    weather: dict[str, Any],
    scores: dict[str, Any],
    user_lat: float,
    user_lng: float,
    course_kind: str,
) -> dict[str, Any]:
    """코스 재정렬·로깅용 특징 스냅샷(비밀·개인정보 없음)."""
    return {
        "course_kind": course_kind,
        "step_count": len(places),
        "duration_key": intent.get("duration"),
        "trip_goal": intent.get("trip_goal"),
        "companion": intent.get("companion"),
        "transport": intent.get("transport"),
        "adult_count": intent.get("adult_count"),
        "child_count": intent.get("child_count"),
        "weather_precip_prob": round(float(weather.get("precip_prob", 0) or 0), 2),
        "weather_dust": int(weather.get("dust", 1) or 1),
        "weather_sky": int(weather.get("sky", 1) or 1),
        "movement_burden": movement_burden_label(places, user_lat, user_lng),
        "weather_fit": weather_fit_label(weather, scores),
        "io_balance": indoor_outdoor_balance(places),
        "avg_place_score": round(
            sum(float(p.get("score") or 0) for p in places) / max(len(places), 1),
            3,
        ),
    }
