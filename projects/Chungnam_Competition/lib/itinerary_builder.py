# -*- coding: utf-8 -*-
"""
관광 코스 → 시간표형 itinerary (시작·종료·이동 설명).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from lib.course_flow import consumer_label_for_role
from lib.distance import haversine
from lib.meal_context import MealContext
from lib.recommend_ui import approximate_drive_minutes


def _category_ko(place: dict[str, Any], role: str) -> str:
    if place.get("meal_data_insufficient"):
        return "식사(데이터 부족)"
    if role in ("meal",):
        return "음식점"
    if role in ("cafe_rest", "finish", "late_night_rest"):
        return "카페·휴식"
    if role == "night_walk":
        return "야간 산책·야외"
    cat = str(place.get("category") or "")
    if cat == "outdoor":
        return "관광·야외"
    if cat == "indoor":
        return "실내·관람"
    return "관광지"


def _stay_minutes(role: str, duration: str) -> int:
    d = str(duration).strip().lower()
    if role in ("meal",):
        return 60 if d != "2h" else 50
    if role in ("cafe_rest", "finish", "late_night_rest"):
        return 45
    if role == "night_walk":
        return 40
    if role == "main_spot":
        return 90 if d == "full-day" else 75
    if role == "secondary_spot":
        return 50
    return 60


def _travel_line(
    prev: dict[str, Any] | None,
    cur: dict[str, Any],
    transport: str,
) -> str:
    if not prev:
        return "출발 지점에서 첫 일정으로 이동해요."
    la = float(prev.get("coords", {}).get("lat") or 0)
    ln = float(prev.get("coords", {}).get("lng") or 0)
    ca = float(cur.get("coords", {}).get("lat") or 0)
    cn = float(cur.get("coords", {}).get("lng") or 0)
    if la == 0 and ln == 0 or ca == 0 and cn == 0:
        return "이전 장소에서 도보·차량으로 이동해요."
    km = haversine(la, ln, ca, cn)
    if str(transport).lower() == "car":
        mins = approximate_drive_minutes(km) if km > 0 else 5
        return f"약 {km:.1f}km · 자가용 약 {mins}분 거리예요."
    walk = max(5, int(km * 12))
    return f"약 {km:.1f}km · 도보 약 {walk}분(참고)예요."


def build_itinerary_for_course(
    places: list[dict[str, Any]],
    roles: list[str],
    *,
    start_local: datetime,
    duration_key: str,
    transport: str,
    meal_ctx: MealContext | None,
    meal_preference: str,
    time_basis_line: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cur = start_local
    prev_place: dict[str, Any] | None = None
    mp = (meal_preference or "").strip()
    for i, pl in enumerate(places):
        role = str(roles[i] if i < len(roles) else "main_spot")
        label = consumer_label_for_role(role)
        insufficient = bool(pl.get("meal_data_insufficient"))
        name = str(pl.get("name") or "").strip()
        if insufficient:
            pname = "식사 장소 데이터 부족"
            reason = (
                "주변 식당·공공 식사 데이터를 찾지 못했어요. 지도 앱으로 직접 검색해 주세요."
            )
        else:
            pname = name or "(이름 없음)"
            reason_parts = [time_basis_line]
            if mp:
                reason_parts.append(f"식사 선호: {mp}")
            if role == "meal" and meal_ctx and meal_ctx.phase == "pre_lunch":
                reason_parts.append(
                    "점심 전 관광 후 11:30~13:00대에 맞춰 식사 슬롯을 두었어요."
                )
            reason = " ".join(reason_parts)
        stay = _stay_minutes(role, duration_key)
        if (
            meal_ctx
            and meal_ctx.phase == "pre_lunch"
            and role == "meal"
            and meal_ctx.lunch_window_start
        ):
            lh, lm = meal_ctx.lunch_window_start
            slot_start = datetime.combine(cur.date(), time(lh, lm))
            if cur < slot_start:
                cur = slot_start
        end = cur + timedelta(minutes=stay)
        travel = _travel_line(prev_place, pl, transport)
        out.append(
            {
                "order": i + 1,
                "start_time": cur.strftime("%H:%M"),
                "end_time": end.strftime("%H:%M"),
                "place_name": pname,
                "step_role": role,
                "step_label": label,
                "category": _category_ko(pl, role),
                "reason": reason,
                "travel_from_prev": travel,
                "meal_data_insufficient": insufficient,
            }
        )
        prev_place = pl
        cur = end
    return out


def trip_start_datetime(date_iso: str | None, hour: int, minute: int) -> datetime:
    if date_iso:
        try:
            y, mo, d = [int(x) for x in date_iso.split("-", 2)]
            return datetime(y, mo, d, hour % 24, minute % 60)
        except ValueError:
            pass
    today = date.today()
    return datetime(today.year, today.month, today.day, hour % 24, minute % 60)
