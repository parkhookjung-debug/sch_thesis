# -*- coding: utf-8 -*-
"""쿼리 의도 정규화 — places·recommend·daytrip_planner 순환 import 방지용 분리 모듈."""
from __future__ import annotations


def normalize_intent(
    companion: str | None,
    trip_goal: str | None,
    duration: str | None,
    transport: str | None,
    *,
    adult_count: int | None = None,
    child_count: int | None = None,
    meal_preference: str | None = None,
) -> dict[str, str]:
    """쿼리/본문 값을 허용 집합으로 보정 (기본값 포함).

    adult_count / child_count가 None이면 동행·목적에 맞춰 보수적 기본값을 쓴다.
    홈페이지 규칙 엔진(/api/recommend 등). next_scene(/api/course)와 무관.
    """
    c = (companion or "solo").lower().strip()
    g = (trip_goal or "healing").lower().strip()
    d = (duration or "half-day").lower().strip()
    t = (transport or "car").lower().strip()

    if c not in ("solo", "couple", "family", "friends"):
        c = "solo"
    if g not in ("healing", "photo", "walking", "indoor", "culture", "kids"):
        g = "healing"
    if d not in ("2h", "half-day", "full-day"):
        d = "half-day"
    if t not in ("car", "public", "walk"):
        t = "car"

    if adult_count is None:
        if c == "couple":
            adults = 2
        elif c == "friends":
            adults = 3
        elif c == "family":
            adults = 2
        else:
            adults = 1
    else:
        adults = max(1, min(10, int(adult_count)))

    if child_count is None:
        children = 0
        if c == "family":
            children = 1
        if g == "kids":
            children = max(children, 1)
    else:
        children = max(0, min(8, int(child_count)))

    mp_raw = (meal_preference or "").strip()
    mp = mp_raw[:80] if mp_raw else "none"

    return {
        "companion": c,
        "trip_goal": g,
        "duration": d,
        "transport": t,
        "adult_count": str(adults),
        "child_count": str(children),
        "meal_preference": mp,
    }
