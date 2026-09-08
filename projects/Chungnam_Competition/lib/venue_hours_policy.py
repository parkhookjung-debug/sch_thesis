# -*- coding: utf-8 -*-
"""
실시간 영업시간 API가 없을 때, TourAPI 기반 목적지에 대해
‘지금 갈 수 있을 가능성’을 휴리스틱으로 판단한다.

메인 추천 1차 제약(새벽·심야 일반 관람/식음료 제외)과
opening_feasibility 메타(신뢰도 표시)를 제공한다.
"""
from __future__ import annotations

from typing import Any, Literal

TripDetailBand = Literal[
    "night_late",
    "dawn",
    "early",
    "morning",
    "lunch",
    "afternoon",
    "evening",
]

_NIGHT_WALK_TAGS = frozenset(
    {
        "산책",
        "야경",
        "전망",
        "하천",
        "공원",
        "해안",
        "강변",
        "둘레길",
        "트레킹",
        "일출",
        "일몰",
        "드라이브",
        "자연",
        "호수",
        "저수지",
    }
)


def trip_detail_band(hour: int) -> TripDetailBand:
    """심야 20~02, 새벽 02~06을 분리한 시간대."""
    h = int(hour) % 24
    if h >= 20 or h < 2:
        return "night_late"
    if 2 <= h < 6:
        return "dawn"
    if 6 <= h < 9:
        return "early"
    if 9 <= h < 11:
        return "morning"
    if 11 <= h < 13:
        return "lunch"
    if 13 <= h < 17:
        return "afternoon"
    if 17 <= h < 20:
        return "evening"
    return "early"


def time_band_compat(hour: int) -> str:
    """기존 API·로그용: night_late·dawn → night."""
    b = trip_detail_band(hour)
    if b in ("night_late", "dawn"):
        return "night"
    if b == "early":
        return "early"
    if b == "morning":
        return "morning"
    if b == "lunch":
        return "lunch"
    if b == "afternoon":
        return "afternoon"
    if b == "evening":
        return "evening"
    return "early"


def _norm_tags(dest: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for t in dest.get("tags") or []:
        s = str(t).strip().lower()
        if s:
            out.add(s)
    return out


def is_night_walk_friendly_dest(dest: dict[str, Any]) -> bool:
    """야간·새벽에도 실질적으로 접근 가능한 야외·산책형 후보."""
    if dest.get("outdoor_free_access") or dest.get("dawn_walk_ok") or dest.get("late_night_ok"):
        return True
    tags = _norm_tags(dest)
    if tags & _NIGHT_WALK_TAGS:
        return True
    name = str(dest.get("name") or "")
    for kw in ("공원", "천", "강", "해안", "산책", "둘레길", "저수지", "호수", "전망", "해수욕"):
        if kw in name:
            return True
    if str(dest.get("category") or "") == "outdoor" and any(
        k in name for k in ("공원", "해안", "천", "강", "산", "섬")
    ):
        return True
    return False


def _content_type_id(dest: dict[str, Any]) -> str:
    return str(dest.get("contenttypeid") or dest.get("content_type_id") or "").strip()


def _is_food_content(dest: dict[str, Any]) -> bool:
    if _content_type_id(dest) == "39":
        return True
    tags = _norm_tags(dest)
    if tags & frozenset({"맛집", "음식", "식당", "카페", "한식", "횟집", "요리"}):
        return True
    name = str(dest.get("name") or "")
    return any(x in name for x in ("카페", "커피", "식당", "막국수", "국밥", "횟집"))


def _is_ticketed_culture_indoor(dest: dict[str, Any]) -> bool:
    ctype = _content_type_id(dest)
    if ctype in ("14", "15"):  # 문화시설·행사
        return True
    tags = _norm_tags(dest)
    if tags & frozenset({"박물관", "미술관", "전시", "공연장"}):
        return True
    if str(dest.get("category") or "") == "indoor" and tags & frozenset(
        {"문화", "전시", "역사", "유적"}
    ):
        return True
    return False


def should_exclude_primary_recommendation(
    dest: dict[str, Any],
    band: TripDetailBand | str,
) -> tuple[bool, str | None]:
    """
    새벽·심야에 일반 관람·식음료를 메인 후보에서 제외할지.
    반환: (제외 여부, 내부 코드)
    """
    b = str(band)
    if b not in ("night_late", "dawn"):
        return False, None

    if dest.get("twenty_four_hour"):
        return False, None
    if dest.get("late_night_ok") or dest.get("outdoor_free_access"):
        return False, None

    if is_night_walk_friendly_dest(dest):
        return False, None

    if _is_food_content(dest):
        return True, "food_typical_hours"

    if _is_ticketed_culture_indoor(dest):
        return True, "indoor_culture_typical_hours"

    cat = str(dest.get("category") or "")
    if cat == "indoor":
        return True, "generic_indoor_typical_hours"

    # 야외라도 야간 친화 태그가 없으면(일반 관광지) 새벽·심야엔 보수적으로 제외
    if cat == "outdoor":
        return True, "daytime_outdoor_only"

    return True, "unspecified_closed_window"


def build_opening_feasibility_meta(
    dest: dict[str, Any],
    band: TripDetailBand | str,
) -> dict[str, Any]:
    """Places open_now 없이도 프론트·로그용으로 쓸 수 있는 보수적 메타."""
    walk = is_night_walk_friendly_dest(dest)
    late = bool(
        dest.get("twenty_four_hour")
        or dest.get("late_night_ok")
        or dest.get("outdoor_free_access")
        or walk
    )
    conf = "manual_override" if any(
        dest.get(k) for k in ("twenty_four_hour", "late_night_ok", "outdoor_free_access", "dawn_walk_ok")
    ) else "heuristic"

    open_guess: bool | None = True if dest.get("twenty_four_hour") else None

    return {
        "is_open_now": open_guess,
        "open_now": open_guess,
        "opens_at": None,
        "closes_at": None,
        "late_night_possible": late,
        "open_status_confidence": conf,
    }


def trip_context_consumer_note(band: TripDetailBand | str) -> str | None:
    """야간·새벽 fallback 안내 문구."""
    b = str(band)
    if b == "night_late":
        return "지금은 운영 중인 실내 장소가 많지 않아 야간 산책형으로 추천했어요."
    if b == "dawn":
        return "새벽 시간대라 일반 관람지 대신 짧게 다녀올 수 있는 동선으로 구성했어요."
    return None
