# -*- coding: utf-8 -*-
"""
코스 이어가기(Course Continuation): 관광지 이후 '다음 장면' 결정 + Places 후보 재랭킹.

결정론적 규칙 기반. Google Places는 후보만 제공하고, 순위·설명은 여기서 생성한다.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Literal

from lib.distance import haversine
from lib.course_flow import time_band_for_hour
from lib.intent_normalize import normalize_intent
from lib.meal_style import (
    compute_cuisine_bonus,
    compute_meal_style_fit,
    cuisine_bias_vector,
    explain_restaurant_why,
    infer_cuisine_weights,
    infer_meal_style_bundle,
    load_restaurant_style_overrides,
)
from lib.next_course_scoring import quality_fit_rating_reviews
from lib.recommend_ui import approximate_drive_minutes

_ROOT = Path(__file__).resolve().parent.parent
DESTINATIONS_PATH = _ROOT / "data" / "destinations.json"
_log = logging.getLogger(__name__)
OVERRIDES_PATH = _ROOT / "data" / "next_course_overrides.json"

StageType = Literal[
    "meal",
    "cafe_rest",
    "indoor_backup",
    "indoor_visit",
    "short_walk",
    "sunset_finish",
]

# 실내 전환(indoor_backup) 이후 구체화: 식사 / 카페 / 실내 관람·몰
SceneModeType = Literal["meal_rest", "cafe_rest", "indoor_visit", "short_walk", "sunset_finish"]

_cache_dest: dict[str, Any] | None = None
_cache_overrides: tuple[float, list[dict[str, Any]]] | None = None


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _load_destinations() -> dict[str, dict[str, Any]]:
    global _cache_dest
    if _cache_dest is not None:
        return _cache_dest
    with open(DESTINATIONS_PATH, encoding="utf-8") as f:
        items = json.load(f)
    by_id: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for it in items:
        i = it.get("id")
        if i:
            by_id[str(i)] = it
        n = (it.get("name") or "").strip()
        if n:
            by_name[n] = it
    _cache_dest = {"by_id": by_id, "by_name": by_name, "all": items}
    return _cache_dest


def load_next_course_overrides() -> list[dict[str, Any]]:
    """선택 파일. 없거나 깨져 있으면 빈 목록."""
    global _cache_overrides
    if _cache_overrides is not None:
        ts, data = _cache_overrides
        if time.time() - ts < 300:
            return data
    if not OVERRIDES_PATH.is_file():
        _cache_overrides = (time.time(), [])
        return []
    try:
        with open(OVERRIDES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = []
    except Exception:
        data = []
    _cache_overrides = (time.time(), data)
    return data


def spot_in_destination_catalog(spot_id: str | None, spot_name: str | None) -> bool:
    """관광지 JSON(destinations)에 등록된 지점인지. Google place_id 등은 False."""
    d = _load_destinations()
    if spot_id and str(spot_id).strip() in d["by_id"]:
        return True
    if spot_name and str(spot_name).strip() in d["by_name"]:
        return True
    return False


def resolve_spot_metadata(
    spot_id: str | None,
    spot_name: str | None,
) -> dict[str, Any]:
    """관광지 메타(선택 필드 포함). 없으면 category 등 기본만."""
    d = _load_destinations()
    if spot_id and str(spot_id) in d["by_id"]:
        return dict(d["by_id"][str(spot_id)])
    if spot_name:
        key = spot_name.strip()
        if key in d["by_name"]:
            return dict(d["by_name"][key])
    return {
        "category": "outdoor",
        "name": spot_name or "",
        "tags": [],
    }


def estimate_trip_state(
    spot_meta: dict[str, Any],
    hour: int,
    intent: dict[str, str],
    scores: dict[str, Any] | None,
    precip_prob: float,
    dust: int,
) -> dict[str, float]:
    """경량 여행 상태 (0~1). 홈페이지 규칙 엔진용(ML과 독립)."""
    cat = (spot_meta.get("category") or "outdoor").lower()
    activity = (spot_meta.get("activity_level") or "moderate").lower()
    healing_fit = float(spot_meta.get("healing_fit", 0.55))
    photo_fit = float(spot_meta.get("photo_fit", 0.5))
    indoor_ratio = float(spot_meta.get("indoor_ratio", 0.35 if cat == "indoor" else 0.15))
    avg_stay = float(spot_meta.get("avg_stay_minutes") or 75)

    goal = intent.get("trip_goal", "healing")
    companion = intent.get("companion", "solo")
    duration = intent.get("duration", "half-day")
    try:
        child_n = int(str(intent.get("child_count") or "0").strip() or "0")
    except ValueError:
        child_n = 0
    child_n = max(0, min(8, child_n))

    need_meal = 0.35
    if 11 <= hour <= 14:
        need_meal += 0.42
    if 17 <= hour <= 21:
        need_meal += 0.38
    if cat == "outdoor":
        need_meal += 0.12
    if activity in ("high", "moderate"):
        need_meal += 0.08 if activity == "high" else 0.04
    if avg_stay >= 90:
        need_meal += 0.06

    need_rest = 0.28
    if goal == "healing":
        need_rest += 0.22
    if activity == "high":
        need_rest += 0.18
    if companion in ("family", "kids"):
        need_rest += 0.08
    if duration == "full-day":
        need_rest += 0.06

    need_indoor = 0.15 + 0.55 * indoor_ratio
    if precip_prob >= 70:
        need_indoor += 0.45
    elif precip_prob >= 40:
        need_indoor += 0.22
    if dust >= 3:
        need_indoor += 0.35
    elif dust == 2:
        need_indoor += 0.1
    if scores and scores.get("is_raining"):
        need_indoor += 0.2
    if scores and scores.get("is_dust_bad"):
        need_indoor += 0.15

    keep_healing_mood = healing_fit * (0.55 + 0.45 * (1.0 if goal == "healing" else 0.65))

    move_tol = 0.55
    if intent.get("transport") == "public":
        move_tol -= 0.18
    if duration == "2h":
        move_tol -= 0.12
    if goal == "photo":
        move_tol += 0.1
    move_tol += 0.08 * (1.0 - min(photo_fit, 0.95))
    if child_n > 0:
        move_tol -= 0.05 * min(child_n, 3)

    return {
        "need_meal": _clamp01(need_meal),
        "need_rest": _clamp01(need_rest),
        "need_indoor": _clamp01(need_indoor),
        "keep_healing_mood": _clamp01(keep_healing_mood),
        "move_tolerance": _clamp01(move_tol),
    }


def _stage_title(st: StageType, hour: int) -> str:
    if st == "meal":
        if 11 <= hour <= 14:
            return "다음 단계 추천: 점심 식사"
        if 17 <= hour <= 21:
            return "다음 단계 추천: 저녁 식사"
        return "다음 단계 추천: 식사"
    if st == "cafe_rest":
        return "다음 단계 추천: 카페 · 짧은 휴식"
    if st == "indoor_backup":
        return "다음 단계 추천: 실내로 흐름 전환"
    if st == "indoor_visit":
        return "다음 단계 추천: 실내 전시·체험"
    if st == "short_walk":
        return "다음 단계 추천: 짧은 산책 · 여유 코스"
    return "다음 단계 추천: 노을 · 마무리 장면"


def _next_step_headline(st: StageType, hour: int) -> str:
    """다음 행동 한 줄(결론 우선 톤)."""
    if st == "meal":
        if 11 <= hour <= 14:
            return "지금은 점심 식사로 이어가기 좋아요"
        if 17 <= hour <= 21:
            return "지금은 저녁 식사로 이어가기 좋아요"
        return "지금은 식사로 이어가기 좋아요"
    if st == "cafe_rest":
        return "지금은 카페에서 잠깐 쉬기 좋아요"
    if st == "indoor_backup":
        return "지금은 실내로 옮겨 쉬기 좋아요"
    if st == "indoor_visit":
        return "지금은 실내 전시·몰 쪽으로 이어가기 좋아요"
    if st == "short_walk":
        return "지금은 짧은 산책으로 호흡 바꾸기 좋아요"
    return "지금은 노을·마무리 장면을 노리기 좋아요"


_USER_HINT_MAP: dict[str, StageType] = {
    "meal": "meal",
    "식사": "meal",
    "cafe": "cafe_rest",
    "카페": "cafe_rest",
    "quiet": "cafe_rest",
    "조용": "cafe_rest",
    "photo": "sunset_finish",
    "사진": "sunset_finish",
    "indoor": "indoor_backup",
    "실내": "indoor_backup",
    "kids": "meal",
    "아이": "meal",
}


def _hint_to_stage(hint: str) -> StageType | None:
    h = (hint or "").strip().lower()
    return _USER_HINT_MAP.get(h)


def _parse_desired_next_scene_param(raw: str | None) -> StageType | None:
    """쿼리 desired_next_scene → 내부 단계. 코스 다시 짜기 API용."""
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    m: dict[str, StageType] = {
        "meal": "meal",
        "cafe_rest": "cafe_rest",
        "cafe": "cafe_rest",
        "indoor_backup": "indoor_backup",
        "indoor": "indoor_backup",
        "sunset_finish": "sunset_finish",
        "photo": "sunset_finish",
        "short_walk": "short_walk",
        "indoor_visit": "indoor_visit",
    }
    return m.get(key)


def _continuation_rank_bias(
    place: dict[str, Any],
    effective_stage: str,
    *,
    meal_bias: float,
    cafe_bias: float,
    indoor_bias: float,
    scenic_bias: float,
    family_bias: float,
) -> float:
    """태그 기반 재랭킹 가산(0~1 스케일 점수에 더함). 소비자 문구 아님."""
    types_low = [str(t).lower() for t in (place.get("types") or [])]
    blob = " ".join(types_low) + " " + str(place.get("name") or "").lower()
    bonus = 0.0
    mb = max(0.0, min(1.0, float(meal_bias)))
    cb = max(0.0, min(1.0, float(cafe_bias)))
    ib = max(0.0, min(1.0, float(indoor_bias)))
    sb = max(0.0, min(1.0, float(scenic_bias)))
    fb = max(0.0, min(1.0, float(family_bias)))

    if mb > 0 and effective_stage == "meal":
        if any(x in blob for x in ("restaurant", "meal_takeaway", "food", "korean_restaurant")):
            bonus += 0.2 * mb
    if cb > 0 and effective_stage == "cafe_rest":
        if any(x in blob for x in ("cafe", "coffee_shop", "bakery", "dessert")):
            bonus += 0.24 * cb
        if "restaurant" in blob and "cafe" not in blob and "coffee" not in blob:
            bonus -= 0.14 * cb
    if ib > 0:
        if any(
            x in blob
            for x in (
                "museum",
                "shopping_mall",
                "spa",
                "library",
                "art_gallery",
                "movie_theater",
            )
        ):
            bonus += 0.14 * ib
    if sb > 0:
        if any(x in blob for x in ("park", "natural_feature", "campground", "marina", "tourist_attraction")):
            bonus += 0.16 * sb
    if fb > 0:
        if any(x in blob for x in ("playground", "amusement_park", "zoo", "aquarium")) or any(
            k in blob for k in ("키즈", "kid", "family", "어린이")
        ):
            bonus += 0.16 * fb
    return bonus


def _guided_flow_notes(ai_stage: StageType, chosen: StageType, hour: int) -> list[str]:
    if ai_stage == chosen:
        return ["요청하신 방향이 지금 흐름과 잘 맞아요."]
    if chosen == "cafe_rest" and ai_stage == "meal" and 11 <= hour <= 14:
        return [
            "카페로 이어가도 괜찮아요.",
            "다만 점심 시간대라, 식사 후 카페가 더 자연스러울 수 있어요.",
        ]
    if chosen == "meal" and ai_stage == "cafe_rest":
        return [
            "식사를 먼저 해도 좋아요.",
            "AI는 잠깐 쉬는 흐름을 제안했는데, 배가 고프면 식사 우선이 편할 수 있어요.",
        ]
    if chosen == "sunset_finish" and ai_stage in ("meal", "cafe_rest"):
        return [
            "노을·전망을 노리는 흐름이에요.",
            "식사·카페와 겹치면 동선이 길어질 수 있어 여유만 확인해 주세요.",
        ]
    if chosen == "indoor_backup":
        return ["실내로 정리하면 날씨 변동에 덜 흔들려요."]
    return ["원하신 방향으로 후보를 골랐어요. AI가 잡았던 흐름과는 조금 달라질 수 있어요."]


def _stage_why_for_forced(
    st: StageType,
    spot_meta: dict[str, Any],
    hour: int,
    intent: dict[str, str],
) -> list[str]:
    cat = (spot_meta.get("category") or "outdoor").lower()
    why: list[str] = []
    if st == "indoor_backup":
        why.append("강수·미세먼지를 감안하면 잠시 실내에서 호흡 고르기 좋아요.")
        if cat == "outdoor":
            why.append("방금이 야외 위주였다면 실내로 넘기기 자연스러워요.")
    elif st == "sunset_finish":
        why.append("시간대를 보면 노을·전망으로 마무리하는 단계가 어울려요.")
    elif st == "meal":
        why.append("지금 리듬을 나누기에 식사 단계가 어울려요.")
    elif st == "cafe_rest":
        why.append("잠깐 앉아 쉬며 힐링 무드를 유지하기 좋아요.")
    elif st == "short_walk":
        why.append("부담 없이 짧게 걸으며 전환하기 좋아요.")
    elif st == "indoor_visit":
        why.append("실내에서 보며 걷기 좋은 전시·몰형 동선이 어울려요.")
        if cat == "outdoor":
            why.append("야외 위주였다면 실내에서 호흡을 고르기 좋습니다.")
    _ = hour, intent
    return why[:4]


def decide_next_stage(
    spot_meta: dict[str, Any],
    trip_state: dict[str, float],
    hour: int,
    intent: dict[str, str],
    scores: dict[str, Any] | None,
    precip_prob: float,
    dust: int,
) -> tuple[StageType, str, list[str]]:
    """다음 장면 1개 + 제목 + 왜 지금인지 (규칙·상태값 기반 문장)."""
    cat = (spot_meta.get("category") or "outdoor").lower()
    goal = intent.get("trip_goal", "healing")
    golden = bool(spot_meta.get("golden_hour_bonus"))

    weights: dict[str, float] = {
        "meal": 0.0,
        "cafe_rest": 0.0,
        "indoor_backup": 0.0,
        "short_walk": 0.0,
        "sunset_finish": 0.0,
    }

    bad_outdoor = precip_prob >= 60 or dust >= 3 or (scores and scores.get("is_raining"))
    if bad_outdoor and cat == "outdoor":
        weights["indoor_backup"] += 0.95 + 0.25 * trip_state["need_indoor"]
    elif bad_outdoor:
        weights["indoor_backup"] += 0.35

    if (
        17 <= hour <= 19
        and goal in ("photo", "walking", "healing")
        and precip_prob < 70
        and dust < 4
    ):
        weights["sunset_finish"] += 0.55 + 0.25 * float(spot_meta.get("photo_fit", 0.5))
        if golden:
            weights["sunset_finish"] += 0.2
        if goal == "photo":
            weights["sunset_finish"] += 0.42

    weights["meal"] += trip_state["need_meal"] * 0.85
    if 11 <= hour <= 14 or 17 <= hour <= 21:
        weights["meal"] += 0.25
    if cat == "outdoor":
        weights["meal"] += 0.12

    weights["cafe_rest"] += trip_state["need_rest"] * 0.7 + trip_state["keep_healing_mood"] * 0.35
    if 15 <= hour <= 17:
        weights["cafe_rest"] += 0.2
    if goal == "healing":
        weights["cafe_rest"] += 0.15

    if 14 <= hour <= 17 and goal in ("walking", "healing", "photo") and precip_prob < 40 and dust < 3:
        weights["short_walk"] += 0.35 + 0.2 * trip_state["move_tolerance"]

    rns = spot_meta.get("recommended_next_steps") or []
    if isinstance(rns, list):
        for step in rns:
            if step in weights:
                weights[step] += 0.12

    if weights["indoor_backup"] >= 0.9:
        for k in ("meal", "cafe_rest", "short_walk", "sunset_finish"):
            weights[k] *= 0.35

    if 11 <= hour <= 14 and weights["indoor_backup"] < 0.75:
        weights["meal"] += 0.25

    # 일정 길이: 2h는 한두 단계·이동 최소, 종일은 산책·마무리 가중
    dur = (intent.get("duration") or "half-day").strip().lower()
    if dur == "2h":
        weights["cafe_rest"] *= 1.38
        weights["meal"] *= 0.88
        weights["short_walk"] *= 0.48
        weights["sunset_finish"] *= 0.52
    elif dur == "full-day":
        weights["short_walk"] *= 1.28
        weights["sunset_finish"] *= 1.18
        weights["cafe_rest"] *= 1.06
        weights["meal"] *= 1.04

    st: StageType = max(weights, key=lambda k: weights[k])  # type: ignore[assignment]

    # 점심 창: 식사 vs 카페만 묶어서 정리 (날씨·실내 대피·노을이 이기면 건드리지 않음)
    if (
        11 <= hour <= 14
        and st in ("meal", "cafe_rest")
        and weights["meal"] >= weights["cafe_rest"] - 0.15
        and weights["meal"] > weights["indoor_backup"]
    ):
        st = "meal"

    if (
        17 <= hour <= 19
        and goal == "photo"
        and weights["sunset_finish"] >= max(weights["meal"], weights["cafe_rest"]) - 0.05
        and weights["sunset_finish"] >= weights["indoor_backup"] - 0.05
    ):
        st = "sunset_finish"

    title = _stage_title(st, hour)
    why = build_stage_why_lines(st, spot_meta, hour, intent)
    return st, title, why


def build_stage_why_lines(
    st: StageType,
    spot_meta: dict[str, Any],
    hour: int,
    intent: dict[str, str],
) -> list[str]:
    """선택된 단계에 대한 짧은 근거 문장(규칙 기반). ML이 단계만 바꿀 때 제목·설명 재생성에 재사용."""
    cat = (spot_meta.get("category") or "outdoor").lower()
    why: list[str] = []
    if st == "indoor_backup":
        why.append(
            "강수·미세먼지 맥락에서 야외 동선을 이어가기보다 실내에서 호흡을 고르는 단계로 두는 편이 안전합니다."
        )
        if cat == "outdoor":
            why.append("직전 장소가 야외 중심이라 실내 전환이 대비에 해당합니다.")
    elif st == "sunset_finish":
        why.append(
            "일몰 전후 시간대이며 사진·산책 목표가 있어, 하루의 마무리 장면으로 노을·전망류가 자연스럽습니다."
        )
    elif st == "meal":
        why.append("현재 시각과 직전 활동을 고려하면 식사로 리듬을 나누는 단계가 자연스럽습니다.")
        if cat == "outdoor":
            why.append("앞선 관광이 활동 위주라 식사로 리듬을 나누는 편이 흔합니다.")
    elif st == "cafe_rest":
        why.append(
            "휴식·힐링 무드를 유지하기에 카페·짧게 앉아 쉬는 정지가 지금 흐름에 잘 맞습니다."
        )
    elif st == "short_walk":
        why.append(
            "날씨가 허용될 때 짧은 산책으로 이동 부담을 크게 늘리지 않고 호흡만 바꾸기 좋습니다."
        )
    elif st == "indoor_visit":
        why.append("실내 전시·몰 등에서 가볍게 보며 걷기 좋은 단계로 이어가기에 맞습니다.")
        if cat == "outdoor":
            why.append("야외 위주였다면 실내에서 호흡을 고르기 좋습니다.")
    _ = hour, intent
    return why[:4]


def decide_indoor_scene_mode(
    trip_state: dict[str, float],
    hour: int,
    intent: dict[str, str],
    precip_prob: float,
    dust: int,
    scores: dict[str, Any] | None,
    spot_meta: dict[str, Any],
) -> tuple[SceneModeType, list[str]]:
    """indoor_backup 당시: 식사 / 카페 / 실내 관람 중 하나를 결정론으로 고른다."""
    nm = float(trip_state.get("need_meal", 0.35))
    nr = float(trip_state.get("need_rest", 0.28))
    dur = (intent.get("duration") or "half-day").lower().strip()
    goal = intent.get("trip_goal", "healing")
    companion = intent.get("companion", "solo")
    move_tol = float(trip_state.get("move_tolerance", 0.55))
    meal_window = (11 <= hour <= 14) or (17 <= hour <= 21)
    raining_or_dust = precip_prob >= 60 or (scores and scores.get("is_raining")) or dust >= 3
    _ = spot_meta

    if goal in ("culture", "indoor") and nm < 0.62 and (not meal_window or nm < 0.52):
        return "indoor_visit", [
            "목표에 문화·실내 관람 성격이 있어, 전시·실내 체험으로 호흡을 바꾸기 좋습니다.",
            "실내 전환은 유지하되 ‘앉아 먹기’보다 ‘보며 걷기’에 가까운 흐름입니다.",
        ]

    if goal == "kids" and companion in ("family", "kids") and nm < 0.68 and nr >= 0.52 and not meal_window:
        return "indoor_visit", [
            "가족 동행에서 잠깐 몰·전시 같은 실내 활동이 동선 버퍼로 잘 맞는 편입니다.",
            "끼니가 급하지 않다면 앉아만 있기보다 움직임이 있는 실내가 부담이 덜합니다.",
        ]

    if nr >= 0.58 and nm < 0.56 and not (meal_window and nm >= 0.7):
        why = [
            "휴식 쪽 필요가 더 커져, 실내 전환 후보 중에서는 카페·짧게 앉아 쉬는 편이 자연스럽습니다.",
            "끼니보다는 호흡만 고르는 정지로 이동 부담을 줄였습니다.",
        ]
        if dur == "2h":
            why.append("짧은 일정이라 동선을 길게 늘리지 않는 것도 포인트입니다.")
        return "cafe_rest", why[:3]

    if meal_window and nm >= 0.62:
        why = [
            "현재 시간이 끼니대에 가깝고, 식사 필요도도 함께 올라가 있습니다.",
            "실내 전환을 ‘한 끼 + 쉼’으로 묶으면 다음 동선이 단순해집니다.",
        ]
        if raining_or_dust:
            why.append("강수·먼지 맥락에서 실내 식사로 정리하면 안전하게 리듬을 나눌 수 있어요.")
        return "meal_rest", why[:3]

    if nm >= 0.8:
        return "meal_rest", [
            "에너지·배고픔 신호가 커서, 실내에서 한 끼로 정리하는 편이 무리가 적어 보입니다.",
            "그래서 실내 전환의 구체적 방식으로 식사 공간을 우선했습니다.",
        ]

    if dur == "2h" and move_tol <= 0.48:
        return "cafe_rest", [
            "이동 여력이 작은 편이라, 실내 전환은 짧게 앉아 쉬는 쪽이 부담이 덜합니다.",
            "카페·베이커리류가 후보에 잘 맞습니다.",
        ]

    if meal_window:
        return "meal_rest", [
            "시간대상 끼니 흐름이 있어 식사로 이어가는 편이 무난합니다.",
            "실내 전환의 구체적 방법으로 식사 공간을 택했습니다.",
        ]

    return "cafe_rest", [
        "지금 리듬에서는 실내에서 잠깐 쉬는 흐름이 가장 자연스럽습니다.",
        "실내 전환의 구체적 방법으로 카페·디저트 정지를 우선했습니다.",
    ]


def _why_scene_judgement_bullets(
    intent: dict[str, str],
    trip_state: dict[str, float],
    precip_prob: float,
    dust: int,
    scores: dict[str, Any] | None,
    spot_meta: dict[str, Any],
) -> list[str]:
    """‘왜 이렇게 판단했나요?’ 공통 맥락(날씨·일정·이동)."""
    lines: list[str] = []
    dur = (intent.get("duration") or "half-day").lower().strip()
    move_tol = float(trip_state.get("move_tolerance", 0.55))
    if dur == "2h":
        lines.append("2시간 일정이라 동선을 길게 잡기보다, 부담 적은 다음 단계를 우선했습니다.")
    elif dur == "full-day":
        lines.append("종일 일정이라 쉼·다음 장면을 나눠 볼 여지가 있습니다.")
    else:
        lines.append("반나절 일정 기준으로, 쉬었다가 이어가는 리듬을 봤습니다.")

    if move_tol <= 0.42:
        lines.append("이동 부담을 크게 늘리지 않는 쪽을 함께 고려했습니다.")
    elif move_tol >= 0.68:
        lines.append("이동 여력이 있는 편이라, 후보 범위를 조금 넓게 볼 수 있습니다.")

    if precip_prob >= 60 or (scores and scores.get("is_raining")):
        lines.append("강수 가능성이 있어 야외만 고집하기보다 실내·쉼 전환이 유리할 수 있습니다.")
    elif dust >= 3 or (scores and scores.get("is_dust_bad")):
        lines.append("미세먼지 맥락에서 실내로 잠시 넘기면 호흡이 편해질 수 있습니다.")

    cat = (spot_meta.get("category") or "outdoor").lower()
    if cat == "outdoor":
        lines.append("직전 장소가 야외 중심이면, 다음은 실내·정지로 균형을 맞추는 경우가 많습니다.")

    return lines[:3]


def _scene_mode_title(mode: SceneModeType, *, indoor_prefix: bool) -> str:
    """indoor_prefix=True면 본문만(프론트에서 ‘실내 전환 방식’ 라벨과 조합)."""
    body = {
        "meal_rest": "가볍게 식사하며 쉬기",
        "cafe_rest": "카페에서 쉬기",
        "indoor_visit": "실내 전시·체험으로 이어가기",
        "short_walk": "짧은 산책으로 호흡 전환",
        "sunset_finish": "노을·마무리 장면",
    }.get(mode, "다음 장면")
    if indoor_prefix:
        return body
    return "다음 장면 방식: " + body


def _scene_mode_why_direct(
    mode: SceneModeType,
    trip_state: dict[str, float],
    hour: int,
    intent: dict[str, str],
) -> list[str]:
    """비실내전환 단계에서 scene_mode 설명."""
    if mode == "meal_rest":
        return [
            "끼니로 리듬을 나누면 이후 동선이 단순해지는 편입니다.",
            "시간대와 직전 활동을 함께 보면 식사 단계가 자연스럽습니다.",
        ]
    if mode == "cafe_rest":
        return [
            "짧게 앉아 쉬며 힐링 무드를 유지하기 좋은 단계입니다.",
            "휴식 쪽 신호가 식사보다 앞설 때 자주 고릅니다.",
        ]
    if mode == "indoor_visit":
        return [
            "실내에서도 가볍게 움직이며 볼거리를 채우기 좋습니다.",
            "문화·실내 목표와 잘 맞을 때 이 방식을 택합니다.",
        ]
    if mode == "short_walk":
        return [
            "날씨가 허용될 때 짧게 걸으며 전환하기 좋습니다.",
            "이동 허용치와 오후 시간대를 함께 봤습니다.",
        ]
    if mode == "sunset_finish":
        return [
            f"현재 시각({hour}시)과 사진·마무리 목표를 함께 봤습니다.",
            "노을·전망으로 하루를 정리하는 흐름이 자연스럽습니다.",
        ]
    _ = intent
    return []


def _mode_from_effective_stage(stage: StageType) -> SceneModeType:
    if stage == "meal":
        return "meal_rest"
    if stage == "cafe_rest":
        return "cafe_rest"
    if stage == "indoor_visit":
        return "indoor_visit"
    if stage == "short_walk":
        return "short_walk"
    return "sunset_finish"


def google_types_for_stage(stage: StageType) -> list[str]:
    if stage == "meal":
        return ["restaurant", "korean_restaurant", "japanese_restaurant"]
    if stage == "cafe_rest":
        return ["cafe", "coffee_shop", "bakery"]
    if stage == "indoor_backup":
        return ["restaurant", "cafe", "shopping_mall", "meal_takeaway"]
    if stage == "indoor_visit":
        return ["museum", "art_gallery", "shopping_mall", "tourist_attraction"]
    if stage == "short_walk":
        return ["park", "hiking_area", "tourist_attraction"]
    return ["park", "natural_feature", "tourist_attraction", "marina"]


def _meal_like(types_l: list[str]) -> bool:
    return any(
        x in types_l
        for x in (
            "restaurant",
            "korean_restaurant",
            "japanese_restaurant",
            "chinese_restaurant",
            "meal_takeaway",
            "food",
        )
    )


def _cafe_like(types_l: list[str]) -> bool:
    return any(x in types_l for x in ("cafe", "coffee_shop", "bakery"))


def _indoor_comfort_types(types_l: list[str]) -> bool:
    return any(
        x in types_l
        for x in ("cafe", "restaurant", "bakery", "shopping_mall", "meal_takeaway")
    )


def _transition_fit(stage: StageType, place_types: list[str]) -> float:
    t = [x.lower() for x in place_types]
    if stage in ("meal", "indoor_backup"):
        return _clamp01(0.45 + 0.5 * (1.0 if _meal_like(t) else 0.35))
    if stage == "cafe_rest":
        return _clamp01(0.45 + 0.5 * (1.0 if _cafe_like(t) else 0.3))
    if stage == "indoor_visit":
        good = any(
            x in t
            for x in ("museum", "art_gallery", "shopping_mall", "tourist_attraction", "library")
        )
        return _clamp01(0.44 + 0.52 * (1.0 if good else 0.3))
    if stage == "short_walk":
        return _clamp01(0.4 + 0.55 * (1.0 if any(x in t for x in ("park", "hiking_area", "tourist_attraction", "natural_feature")) else 0.35))
    # sunset_finish
    return _clamp01(0.42 + 0.55 * (1.0 if any(x in t for x in ("park", "natural_feature", "tourist_attraction", "marina")) else 0.32))


def _context_fit(intent: dict[str, str], place_types: list[str], override: dict[str, Any] | None) -> float:
    g = intent.get("trip_goal", "healing")
    t = " ".join(place_types).lower()
    s = 0.48
    if g == "kids" and _meal_like([t]):
        s += 0.18
    if g in ("kids", "family") and override and override.get("kids_friendly"):
        s += 0.15
    if g == "healing" and ("cafe" in t or "bakery" in t):
        s += 0.12
    if g == "photo" and ("cafe" in t or "restaurant" in t):
        s += 0.08
    if g in ("culture", "indoor", "kids") and any(x in t for x in ("museum", "art_gallery", "shopping_mall")):
        s += 0.14
    if override and isinstance(override.get("mood_tags"), list):
        if g == "healing" and "healing" in override["mood_tags"]:
            s += 0.12
        if g == "kids" and "family" in override["mood_tags"]:
            s += 0.1
    return _clamp01(s)


def _mood_fit(intent: dict[str, str], place_types: list[str], trip_state: dict[str, float], override: dict[str, Any] | None) -> float:
    g = intent.get("trip_goal", "healing")
    t = " ".join(place_types).lower()
    s = 0.45 + 0.35 * trip_state.get("keep_healing_mood", 0.5)
    if g == "healing" and "cafe" in t:
        s += 0.15
    if g == "photo" and ("bakery" in t or "cafe" in t):
        s += 0.12
    if override and isinstance(override.get("mood_tags"), list) and "healing" in override["mood_tags"]:
        s += 0.12
    return _clamp01(s)


def _distance_fit_km(km: float, move_tol: float) -> float:
    max_km = 8.0 + move_tol * 6.0
    return _clamp01(1.0 - min(km, max_km) / max_km)


def _weather_comfort_fit(
    stage: StageType,
    place_types: list[str],
    scores: dict[str, Any] | None,
    temp: float,
) -> float:
    t = [x.lower() for x in place_types]
    indoorish = _indoor_comfort_types(t)
    outdoorish = any(x in t for x in ("park", "hiking_area", "natural_feature", "tourist_attraction"))

    w = 0.52
    if stage in ("sunset_finish", "short_walk") and outdoorish:
        if scores and not scores.get("is_raining") and not scores.get("is_dust_bad"):
            w += 0.28
        if temp >= 33 or temp <= 3:
            w -= 0.12
    if indoorish:
        if scores and scores.get("is_raining"):
            w += 0.22
        if scores and scores.get("is_dust_bad"):
            w += 0.14
        if temp >= 30 or temp <= 5:
            w += 0.1
    return _clamp01(w)


def _likely_followup_stage(current: StageType, hour: int) -> str:
    if current == "meal":
        return "cafe_rest" if hour <= 17 else "go_home"
    if current == "cafe_rest":
        return "sunset_finish" if 16 <= hour <= 18 else "go_home"
    if current == "short_walk":
        return "meal"
    if current == "sunset_finish":
        return "go_home"
    if current == "indoor_backup":
        return "meal"
    if current == "indoor_visit":
        if (11 <= hour <= 14) or (17 <= hour <= 20):
            return "meal"
        return "cafe_rest"
    return "cafe_rest"


def _followup_fit(
    stage: StageType,
    place_types: list[str],
    trip_state: dict[str, float],
    hour: int,
) -> float:
    nxt = _likely_followup_stage(stage, hour)
    t = [x.lower() for x in place_types]
    sitdown = _meal_like(t) and "meal_takeaway" not in t
    takeaway = "meal_takeaway" in t

    if stage == "meal" and nxt == "cafe_rest":
        return _clamp01(0.55 + 0.35 * (1.0 if sitdown else 0.45) - 0.2 * (1.0 if takeaway else 0.0))
    if stage == "cafe_rest":
        return _clamp01(0.5 + 0.4 * trip_state.get("keep_healing_mood", 0.5))
    if stage == "indoor_backup":
        return _clamp01(0.58 + 0.2 * (1.0 if _indoor_comfort_types(t) else 0.0))
    if stage == "indoor_visit":
        return _clamp01(
            0.54
            + 0.22 * (1.0 if any(x in t for x in ("museum", "art_gallery", "shopping_mall")) else 0.0)
        )
    if stage in ("short_walk", "sunset_finish"):
        return _clamp01(0.52 + 0.25 * trip_state.get("move_tolerance", 0.5))
    return 0.55


def _override_for_place(overrides: list[dict[str, Any]], place_id: str | None) -> dict[str, Any] | None:
    if not place_id:
        return None
    for o in overrides:
        if str(o.get("place_id", "")) == str(place_id):
            return o
    return None


def _merge_overrides(
    rs_ov: dict[str, Any] | None, nc_ov: dict[str, Any] | None
) -> dict[str, Any] | None:
    """식당 스타일 오버라이드 + next_course 오버라이드를 place_id 기준 병합."""
    if not rs_ov and not nc_ov:
        return None
    m: dict[str, Any] = {}
    if rs_ov:
        m = dict(rs_ov)
    if nc_ov:
        for k, v in nc_ov.items():
            if v is None:
                continue
            if k == "meal_tags" and isinstance(v, list):
                prev = m.get("meal_tags")
                base = list(prev) if isinstance(prev, list) else []
                m["meal_tags"] = list(dict.fromkeys(base + v))
            elif k == "mood_tags" and isinstance(v, list):
                prev = m.get("mood_tags")
                base = list(prev) if isinstance(prev, list) else []
                m["mood_tags"] = list(dict.fromkeys(base + v))
            else:
                m[k] = v
    return m if m else None


def _score_restaurant_meal_flow(
    place: dict[str, Any],
    *,
    inferred_style: str,
    secondary_style: str | None,
    stage: StageType,
    ref_lat: float,
    ref_lng: float,
    hour: int,
    trip_state: dict[str, float],
    scores: dict[str, Any] | None,
    temp: float,
    merged_override: dict[str, Any] | None,
    rs_override: dict[str, Any] | None,
) -> tuple[float, dict[str, float]]:
    """식사·실내 식사 후보: 스타일 + 요리 편향 + 전환·거리·품질·날씨·이후 동선."""
    types = place.get("types") or []
    pname = str(place.get("name") or "")
    lat = float(place["lat"])
    lng = float(place["lng"])
    km = haversine(ref_lat, ref_lng, lat, lng)

    msf = compute_meal_style_fit(
        inferred_style, secondary_style, pname, types, rs_override
    )
    cw = infer_cuisine_weights(pname, types, rs_override)
    cbonus = compute_cuisine_bonus(inferred_style, cw)
    tf = _transition_fit(stage, types)
    df = _distance_fit_km(km, trip_state.get("move_tolerance", 0.5))
    wf = _weather_comfort_fit(stage, types, scores, temp)
    ff = _followup_fit(stage, types, trip_state, hour)
    qf = quality_fit_rating_reviews(
        place.get("rating") if place.get("rating") else None,
        int(place.get("review_count") or 0),
    )
    if merged_override:
        qf = _clamp01(qf + float(merged_override.get("local_bonus", 0.0)))
        if merged_override.get("indoor_comfort") is not None and _indoor_comfort_types(
            [x.lower() for x in types]
        ):
            wf = _clamp01(wf + 0.08 * float(merged_override["indoor_comfort"]))

    total = (
        0.26 * msf
        + 0.18 * cbonus
        + 0.18 * tf
        + 0.16 * df
        + 0.12 * qf
        + 0.06 * wf
        + 0.04 * ff
    )
    total = round(_clamp01(total), 4)
    comp = {
        "meal_style_fit": round(msf, 4),
        "cuisine_bonus": round(cbonus, 4),
        "transition_fit": round(tf, 4),
        "distance_fit": round(df, 4),
        "quality_fit": round(qf, 4),
        "weather_comfort_fit": round(wf, 4),
        "followup_fit": round(ff, 4),
    }
    return total, comp


def score_place_course(
    place: dict[str, Any],
    *,
    stage: StageType,
    ref_lat: float,
    ref_lng: float,
    hour: int,
    intent: dict[str, str],
    trip_state: dict[str, float],
    scores: dict[str, Any] | None,
    temp: float,
    override: dict[str, Any] | None,
) -> tuple[float, dict[str, float]]:
    types = place.get("types") or []
    lat = float(place["lat"])
    lng = float(place["lng"])
    km = haversine(ref_lat, ref_lng, lat, lng)
    qf = quality_fit_rating_reviews(
        place.get("rating") if place.get("rating") else None,
        int(place.get("review_count") or 0),
    )
    tf = _transition_fit(stage, types)
    df = _distance_fit_km(km, trip_state.get("move_tolerance", 0.5))
    wf = _weather_comfort_fit(stage, types, scores, temp)
    ff = _followup_fit(stage, types, trip_state, hour)

    if override:
        qf = _clamp01(qf + float(override.get("local_bonus", 0.0)))
        if override.get("indoor_comfort") is not None and _indoor_comfort_types([x.lower() for x in types]):
            wf = _clamp01(wf + 0.08 * float(override["indoor_comfort"]))

    if stage in ("meal", "indoor_backup", "indoor_visit", "short_walk", "sunset_finish"):
        cf = _context_fit(intent, types, override)
        if stage == "indoor_backup":
            cf = _clamp01(cf + 0.12 * trip_state.get("need_indoor", 0.0))
        if stage == "indoor_visit":
            cf = _clamp01(cf + 0.1 * trip_state.get("need_indoor", 0.0))
        total = (
            0.30 * tf
            + 0.20 * cf
            + 0.20 * df
            + 0.15 * qf
            + 0.10 * wf
            + 0.05 * ff
        )
        comp = {
            "transition_fit": tf,
            "context_fit": cf,
            "distance_fit": df,
            "quality_fit": qf,
            "weather_comfort_fit": wf,
            "followup_fit": ff,
        }
    else:
        mf = _mood_fit(intent, types, trip_state, override)
        total = (
            0.28 * tf
            + 0.22 * mf
            + 0.18 * df
            + 0.15 * qf
            + 0.10 * wf
            + 0.07 * ff
        )
        comp = {
            "transition_fit": tf,
            "mood_fit": mf,
            "distance_fit": df,
            "quality_fit": qf,
            "weather_comfort_fit": wf,
            "followup_fit": ff,
        }

    total = round(_clamp01(total), 4)
    return total, {k: round(v, 4) for k, v in comp.items()}


def _mobility_line_next(km: float, intent: dict[str, str]) -> str:
    if intent.get("transport") == "car":
        dm = approximate_drive_minutes(km)
        return f"직전 장소에서 약 {km:.1f}km · 자가용 기준 약 {dm}분(근사)로 이동 부담이 크지 않습니다."
    return f"직전 장소에서 약 {km:.1f}km · 대중교통은 노선에 따라 달라집니다."


def _why_indoor_shift_now(
    spot_meta: dict[str, Any],
    scores: dict[str, Any] | None,
    precip_prob: float,
    dust: int,
) -> list[str]:
    """실내 전환 단계: 식사 중심 설명과 겹치지 않게."""
    lines: list[str] = []
    cat = (spot_meta.get("category") or "outdoor").lower()
    activity = (spot_meta.get("activity_level") or "moderate").lower()
    if cat == "outdoor" and activity in ("high", "moderate"):
        lines.append("야외 동선 뒤에는 잠시 실내로 넘겨 호흡·리듬을 안정화하기 좋습니다.")
    elif cat == "outdoor":
        lines.append("야외 위주였다면 실내에서 잠깐 쉬며 다음 동선을 정하기 좋습니다.")
    if precip_prob >= 60 or (scores and scores.get("is_raining")) or dust >= 3:
        lines.append("강수·미세먼지 맥락에서 실내에 머무는 편이 부담이 적습니다.")
    if len(lines) < 3:
        lines.append("이 단계는 ‘한 끼’가 아니라 실내에서 부담 적게 쉬는 흐름에 가깝습니다.")
    return lines[:3]


def _why_meal_now(
    spot_meta: dict[str, Any],
    trip_state: dict[str, float],
    hour: int,
    intent: dict[str, str],
    scores: dict[str, Any] | None,
    precip_prob: float,
    dust: int,
) -> list[str]:
    """식사 단계: 왜 지금 끼니로 두는지(장면 설명 보강)."""
    lines: list[str] = []
    cat = (spot_meta.get("category") or "outdoor").lower()
    activity = (spot_meta.get("activity_level") or "moderate").lower()
    if cat == "outdoor":
        if activity in ("high", "moderate"):
            lines.append(
                "야외 위주로 움직였기 때문에 지금은 끼니로 에너지를 보충하는 단계가 자연스럽습니다."
            )
        else:
            lines.append("야외 동선 뒤에는 앉아서 한 끼로 호흡을 바꾸기 쉽습니다.")
    if 11 <= hour <= 14:
        lines.append("현재 시각이 점심 식사 구간에 들어갑니다.")
    elif 17 <= hour <= 21:
        lines.append("저녁 식사 시간대에 가깝습니다.")
    if precip_prob >= 60 or (scores and scores.get("is_raining")) or dust >= 3:
        lines.append("날씨·미세먼지 맥락에서 실내에서 한 끼로 정리하는 편이 안전합니다.")
    if float(trip_state.get("need_meal", 0)) >= 0.82:
        lines.append("오늘 코스에서 식사 필요도가 비교적 높게 추정됩니다.")
    if intent.get("transport") == "public" and len(lines) < 3:
        lines.append("대중교통 동선을 고려해 무리한 이동 직후보다는 식사로 쉬는 흐름이 흔합니다.")
    return lines[:3]


def _after_this_short(stage: StageType, duration: str = "half-day") -> list[str]:
    """일정 길이에 따라 이후 불릿 깊이를 다르게 한다."""
    d = (duration or "half-day").strip().lower()
    if stage == "meal":
        if d == "2h":
            return ["카페에서 잠깐만 쉬기", "바로 귀가·정리"]
        if d == "full-day":
            return ["오후 다른 명소 한 곳", "카페·디저트", "저녁·노을·귀가"]
        return ["근처 카페에서 쉬기", "짧은 산책", "귀가"]
    if stage == "cafe_rest":
        if d == "2h":
            return ["귀가·정리"]
        if d == "full-day":
            return ["오후 명소", "노을·전망", "저녁·귀가"]
        return ["노을·전망 포인트", "가벼운 산책", "귀가"]
    if stage == "indoor_backup":
        if d == "2h":
            return ["카페·휴식만", "귀가"]
        if d == "full-day":
            return ["가벼운 식사", "야외·산책 한 번", "저녁·귀가"]
        return ["식사로 에너지 보충", "카페에서 휴식", "귀가"]
    if stage == "indoor_visit":
        if d == "2h":
            return ["카페에서 짧게", "귀가"]
        if d == "full-day":
            return ["가벼운 식사", "야외·노을", "저녁·귀가"]
        return ["카페·휴식", "식사 또는 산책", "귀가"]
    if stage == "short_walk":
        if d == "2h":
            return ["카페", "귀가"]
        if d == "full-day":
            return ["가벼운 식사", "다음 코스", "귀가"]
        return ["가벼운 식사", "카페", "귀가"]
    if d == "2h":
        return ["카페 또는 귀가"]
    if d == "full-day":
        return ["다음 명소", "카페", "저녁·귀가"]
    return ["가벼운 식사 또는 카페", "귀가"]


def explain_primary(
    stage: StageType,
    stage_why: list[str],
    place: dict[str, Any],
    comp: dict[str, float],
    km: float,
    trip_state: dict[str, float],
    intent: dict[str, str],
    after_labels: list[str],
    duration: str = "half-day",
) -> tuple[list[str], list[str], list[str]]:
    """A: 단계 이유, B: 이 장소(짧게·점수축 연결), C: 이후(짧은 불릿)."""
    a = list(stage_why[:2])
    tops = sorted(comp.items(), key=lambda x: x[1], reverse=True)[:3]
    top_keys = {x[0] for x in tops}
    b: list[str] = []
    if tops and ("distance_fit" in top_keys or tops[0][0] == "distance_fit"):
        b.append(_mobility_line_next(km, intent))
    if "transition_fit" in top_keys:
        st_ko = {
            "meal": "식사",
            "cafe_rest": "카페·휴식",
            "indoor_backup": "실내 전환",
            "indoor_visit": "실내 전시·체험",
            "short_walk": "짧은 산책",
            "sunset_finish": "노을·마무리",
        }.get(stage, str(stage))
        b.append(f"지금 단계는 「{st_ko}」에 맞는 유형으로 골랐습니다.")
    if "quality_fit" in top_keys:
        b.append("후보 중 평점·리뷰 수 신뢰도가 비교적 안정적인 편입니다.")
    if "context_fit" in top_keys or "mood_fit" in top_keys:
        b.append(
            f"목표·동행(「{intent.get('trip_goal')}」, {intent.get('companion')})와의 맥락이 잘 맞습니다."
        )
    if "weather_comfort_fit" in top_keys and len(b) < 3:
        b.append("비·미세먼지·기온 맥락에서 쉬기 좋은 실내·야외 균형을 봤습니다.")
    if len(b) < 2:
        b.append("현재 설정 기준에서 다음 장면에 어울리는 후보입니다.")
    c = _after_this_short(stage, duration)
    return a, b[:3], c


def _step_role_to_continuation_stage(step_role: str) -> StageType:
    """코스 단계 교체: UI step_role → Places 검색·점수 단계."""
    r = (step_role or "").strip().lower()
    if r == "meal":
        return "meal"
    if r in ("cafe_rest", "finish"):
        return "cafe_rest"
    if r == "indoor_visit":
        return "indoor_visit"
    return "short_walk"


def build_course_payload(
    *,
    lat: float,
    lng: float,
    category: str,
    hour: int,
    intent: dict[str, str] | None,
    scores: dict[str, Any] | None,
    precip_prob: float,
    dust: int,
    temp: float,
    spot_id: str | None,
    spot_name: str | None,
    fetch_places_fn: Any,
    course_path: str | None = None,
    user_next_hint: str | None = None,
    user_custom_note: str | None = None,
    use_ml_next_scene_assist: bool = False,
    desired_next_scene: str | None = None,
    desired_course_style: str | None = None,
    family_bias: float = 0.0,
    scenic_bias: float = 0.0,
    indoor_bias: float = 0.0,
    meal_bias: float = 0.0,
    cafe_bias: float = 0.0,
    replace_step: bool = False,
    replace_step_index: int | None = None,
    replace_step_role: str | None = None,
    time_band: str | None = None,
) -> dict[str, Any]:
    """
    fetch_places_fn: (lat, lng, types, radius_m) -> tuple[list[dict], float, bool, str | None]
      반환: (results, radius_used, fallback_applied, fallback_note)

    use_ml_next_scene_assist가 True일 때만(그리고 NEXT_SCENE_MODEL 등 환경이 갖춰졌을 때만)
    시나리오 next_scene 분류기를 호출한다. 기본 False = 홈·일반 경로는 규칙 전용.
    """
    intent_use = intent if intent is not None else normalize_intent(None, None, None, None)
    dur_flow = str(intent_use.get("duration") or "half-day").strip().lower()
    family_bias = max(0.0, min(1.0, float(family_bias or 0.0)))
    scenic_bias = max(0.0, min(1.0, float(scenic_bias or 0.0)))
    indoor_bias = max(0.0, min(1.0, float(indoor_bias or 0.0)))
    meal_bias = max(0.0, min(1.0, float(meal_bias or 0.0)))
    cafe_bias = max(0.0, min(1.0, float(cafe_bias or 0.0)))
    from_catalog = spot_in_destination_catalog(spot_id, spot_name)
    spot_meta = resolve_spot_metadata(spot_id, spot_name)
    # DB에 없는 선택(Google place 등)은 요청 category로 앵커 유형을 맞춘다. 그렇지 않으면 기본 outdoor로
    # 식당 앵커 보정·동일 장소 제외가 전부 빠진다.
    if not from_catalog:
        spot_meta = {
            **spot_meta,
            "category": (category or spot_meta.get("category") or "outdoor").strip().lower(),
        }
    else:
        spot_meta.setdefault("category", (category or "outdoor").strip().lower())
    # Places에서 식당을 골라 이어갈 때: 기준지가 이미 식사 장소이므로 또 식사 단계가 잡히지 않게 한다.
    anchor_is_restaurant = (spot_meta.get("category") or "").lower() == "restaurant"
    trip_state = estimate_trip_state(
        spot_meta, hour, intent_use, scores, precip_prob, dust
    )
    if anchor_is_restaurant:
        trip_state = {
            **trip_state,
            "need_meal": min(float(trip_state.get("need_meal", 0.5)), 0.07),
            "need_rest": max(float(trip_state.get("need_rest", 0.28)), 0.82),
        }
    replace_step_mode = bool(replace_step) and bool((replace_step_role or "").strip())
    if replace_step_mode:
        sr0 = (replace_step_role or "").strip().lower()
        stage_ai = _step_role_to_continuation_stage(sr0)
        title_ai = _stage_title(stage_ai, hour)
        why_ai = _stage_why_for_forced(stage_ai, spot_meta, hour, intent_use)[:4]
    else:
        stage_ai, title_ai, why_ai = decide_next_stage(
            spot_meta, trip_state, hour, intent_use, scores, precip_prob, dust
        )
    stage: StageType = stage_ai
    stage_title = title_ai
    stage_why = why_ai

    path_norm = (course_path or "ai").strip().lower()
    if path_norm not in ("ai", "guided"):
        path_norm = "ai"
    guided_notes: list[str] = []
    hint_raw = (user_next_hint or "").strip()
    hint_key = hint_raw.lower()
    forced = _hint_to_stage(hint_key) if hint_key else None
    desired_stage = _parse_desired_next_scene_param(desired_next_scene)
    if desired_stage is not None:
        forced = desired_stage
    # 명시적 단계·칩이 있으면 시간대 휴리스틱보다 우선한다.
    user_stage_from_hint = forced is not None
    _ = desired_course_style  # 향후 meal_style 가중용 훅

    if forced is not None:
        guided_notes = _guided_flow_notes(stage_ai, forced, hour)
        stage = forced
        stage_title = _stage_title(stage, hour)
        stage_why = _stage_why_for_forced(stage, spot_meta, hour, intent_use)[:4]
    elif path_norm == "guided" and hint_key in ("custom", "직접", "직접장소") and (user_custom_note or "").strip():
        note = (user_custom_note or "").strip()[:120]
        guided_notes = [
            f"말씀해 주신「{note}」은 참고에 두었어요. 아래는 같은 조건에서 AI가 잡은 다음 흐름이에요."
        ]
    elif path_norm == "guided" and hint_raw and forced is None and hint_key not in ("custom", "직접", "직접장소"):
        guided_notes = ["요청을 해석하지 못해 AI 추천 흐름을 그대로 씁니다."]
    # 식당을 이미 골랐는데 indoor_backup이면 Places가 또 restaurant 위주로 잡혀 같은 유형이 반복된다.
    if anchor_is_restaurant and stage in ("meal", "indoor_backup"):
        stage = "cafe_rest"
        stage_title = _stage_title(stage, hour)
        stage_why = _stage_why_for_forced(stage, spot_meta, hour, intent_use)[:4]
        guided_notes = list(guided_notes) + [
            "이미 식당을 기준으로 잡혀 있어, 다음 단계는 카페·디저트(휴식)로 넘겼어요.",
        ]

    # 시나리오 학습 next_scene (선택). guided·식당 앵커 보정 뒤, Places 조회 전에만 적용.
    ml_next_scene: dict[str, Any] = {
        "model_used": False,
        "next_scene_reason_mode": "rule-based",
        "predicted_next_scene": None,
        "rule_based_stage": str(stage),
        "scene_probs": None,
        "top_features": None,
    }
    if (
        path_norm == "ai"
        and not anchor_is_restaurant
        and use_ml_next_scene_assist
        and not user_stage_from_hint
        and not replace_step_mode
    ):
        try:
            from app.ml.next_scene_predictor import try_model_stage_override

            chosen, ml_meta = try_model_stage_override(
                rule_stage=str(stage),
                spot_meta=spot_meta,
                trip_state=trip_state,
                hour=hour,
                intent=intent_use,
                scores=scores,
                precip_prob=precip_prob,
                dust=dust,
                temp=float(temp),
            )
            ml_next_scene = {**ml_next_scene, **ml_meta}
            if ml_meta.get("model_used"):
                if chosen in (
                    "meal",
                    "cafe_rest",
                    "indoor_backup",
                    "short_walk",
                    "sunset_finish",
                    "indoor_visit",
                ):
                    stage = chosen  # type: ignore[assignment]
                    stage_title = _stage_title(stage, hour)
                    stage_why = build_stage_why_lines(stage, spot_meta, hour, intent_use)
        except Exception:
            _log.exception("next_scene ML assist failed (import, bundle, or predict)")

    if use_ml_next_scene_assist:
        if user_stage_from_hint:
            ml_next_scene["fallback_reason"] = "user_hint_takes_priority"
        elif ml_next_scene.get("model_used"):
            ml_next_scene["fallback_reason"] = None
        elif replace_step_mode:
            ml_next_scene["fallback_reason"] = "replace_step_skips_ml"
        elif path_norm != "ai":
            ml_next_scene["fallback_reason"] = "guided_flow"
        elif anchor_is_restaurant:
            ml_next_scene["fallback_reason"] = "restaurant_anchor"
        else:
            ml_next_scene["fallback_reason"] = "rules_or_model_unavailable"
    else:
        ml_next_scene["fallback_reason"] = "assist_not_requested"

    # 고수준(실내 전환 등) ↔ scene_mode(식사/카페/실내 관람) ↔ Places 조회용 effective_stage 분리
    indoor_transition_split = stage == "indoor_backup"
    scene_mode_why: list[str]
    mode: SceneModeType
    if indoor_transition_split:
        mode, scene_mode_why = decide_indoor_scene_mode(
            trip_state, hour, intent_use, precip_prob, dust, scores, spot_meta
        )
        effective_stage: StageType = {
            "meal_rest": "meal",
            "cafe_rest": "cafe_rest",
            "indoor_visit": "indoor_visit",
        }[mode]
    else:
        mode = _mode_from_effective_stage(stage)
        scene_mode_why = _scene_mode_why_direct(mode, trip_state, hour, intent_use)
        effective_stage = stage

    scene_mode_block: dict[str, Any] = {
        "type": mode,
        "title": _scene_mode_title(mode, indoor_prefix=indoor_transition_split),
        "why": scene_mode_why,
    }

    judgement_why = _why_scene_judgement_bullets(
        intent_use, trip_state, precip_prob, dust, scores, spot_meta
    )
    if indoor_transition_split:
        ns_why = list(dict.fromkeys([*(stage_why or [])[:2], *judgement_why]))[:3]
        next_scene_payload: dict[str, Any] = {
            "type": "indoor_transition",
            "title": _stage_title("indoor_backup", hour),
            "headline": _next_step_headline("indoor_backup", hour),
            "why": ns_why,
            "why_meal_now": [],
        }
    else:
        ns_why = list(dict.fromkeys([*(stage_why or [])[:2], *judgement_why]))[:3]
        next_scene_payload = {
            "type": stage,
            "title": stage_title,
            "headline": _next_step_headline(stage, hour),
            "why": ns_why,
            "why_meal_now": [],
        }

    if effective_stage == "meal":
        next_scene_payload["why_meal_now"] = _why_meal_now(
            spot_meta, trip_state, hour, intent_use, scores, precip_prob, dust
        )

    next_step_headline = (
        _next_step_headline("indoor_backup", hour)
        if indoor_transition_split
        else _next_step_headline(effective_stage, hour)
    )
    next_scene_payload["headline"] = next_step_headline

    if path_norm == "ai":
        if dur_flow == "2h":
            guided_notes = list(guided_notes) + [
                "2시간 일정: 다음은 한 단계만 강하게 이어가요. 두 번째 관광지까지 늘리지 않는 편이 자연스러워요.",
            ]
        elif dur_flow == "full-day":
            guided_notes = list(guided_notes) + [
                "종일 일정: 쉼·다음 장면·마무리까지 여유 있게 볼 수 있어요.",
            ]
        else:
            guided_notes = list(guided_notes) + [
                "반나절 일정: 한 번 쉬고 다음 장면까지 이어가기 무난해요.",
            ]

    meal_style = infer_meal_style_bundle(
        stage=str(effective_stage),
        spot_meta=spot_meta,
        trip_state=trip_state,
        hour=hour,
        intent=intent_use,
        scores=scores,
        temp=temp,
        precip_prob=precip_prob,
    )

    types = google_types_for_stage(effective_stage)
    raw_result = fetch_places_fn(lat, lng, types)
    if isinstance(raw_result, tuple) and len(raw_result) >= 3:
        results, radius_used, fallback_applied = raw_result[0], raw_result[1], raw_result[2]
        fallback_note = raw_result[3] if len(raw_result) > 3 else None
    else:
        results, radius_used, fallback_applied = [], 0, True
        fallback_note = "Places 호출 결과 형식 오류"

    overrides = load_next_course_overrides()
    restaurant_overrides = load_restaurant_style_overrides()
    use_meal_flow = effective_stage == "meal"
    inferred_style = str(meal_style.get("key") or "family_relaxed_meal")
    if inferred_style in ("none", "", "cafe_rest", "indoor_comfort"):
        inferred_style = "family_relaxed_meal"
    secondary_style = meal_style.get("secondary_key")
    if not isinstance(secondary_style, str):
        secondary_style = None

    ranked: list[dict[str, Any]] = []
    for p in results:
        oid = p.get("place_id") or ""
        nc_ov = _override_for_place(overrides, oid if oid else None)
        rs_ov = _override_for_place(restaurant_overrides, oid if oid else None)
        merged = _merge_overrides(rs_ov, nc_ov)
        if use_meal_flow:
            total, comp = _score_restaurant_meal_flow(
                p,
                inferred_style=inferred_style,
                secondary_style=secondary_style,
                stage=effective_stage,
                ref_lat=lat,
                ref_lng=lng,
                hour=hour,
                trip_state=trip_state,
                scores=scores,
                temp=temp,
                merged_override=merged,
                rs_override=rs_ov,
            )
        else:
            total, comp = score_place_course(
                p,
                stage=effective_stage,
                ref_lat=lat,
                ref_lng=lng,
                hour=hour,
                intent=intent_use,
                trip_state=trip_state,
                scores=scores,
                temp=temp,
                override=merged if merged is not None else nc_ov,
            )
        bias_add = _continuation_rank_bias(
            p,
            str(effective_stage),
            meal_bias=meal_bias,
            cafe_bias=cafe_bias,
            indoor_bias=indoor_bias,
            scenic_bias=scenic_bias,
            family_bias=family_bias,
        )
        total = min(1.0, max(0.0, float(total) + bias_add))
        km = haversine(lat, lng, float(p["lat"]), float(p["lng"]))
        ranked.append(
            {
                **p,
                "next_course_score": total,
                "score_100": round(float(total) * 100.0, 1),
                "score_breakdown": comp,
                "distance_from_prev_km": round(km, 2),
            }
        )
    ranked.sort(key=lambda x: x.get("next_course_score", 0), reverse=True)

    review_meta_applied = False
    if replace_step_mode:
        from lib.review_features import rerank_with_review_text_signals

        ranked, review_meta_applied = rerank_with_review_text_signals(
            ranked,
            intent_use,
            lat,
            lng,
            hour=hour,
            meal_bias=meal_bias,
            cafe_bias=cafe_bias,
            family_bias=family_bias,
            scenic_bias=scenic_bias,
            indoor_bias=indoor_bias,
        )

    tb_resolved = (time_band or "").strip() or time_band_for_hour(hour)

    sid = str(spot_id).strip() if spot_id else ""
    if sid:
        ranked = [p for p in ranked if str(p.get("place_id") or "").strip() != sid]
    sn_anchor = str(spot_name).strip() if spot_name else ""
    if sn_anchor:
        ranked = [p for p in ranked if (p.get("name") or "").strip() != sn_anchor]

    primary = ranked[0] if ranked else None
    alternatives = ranked[1:8] if len(ranked) > 1 else []

    after = _likely_followup_stage(effective_stage, hour)
    after_labels_map = {
        "cafe_rest": "카페에서 짧게 쉬기",
        "meal": "식사",
        "sunset_finish": "노을·전망 포인트",
        "go_home": "귀가·정리",
        "short_walk": "짧은 산책",
    }
    after_labels = [after_labels_map.get(after, after)]
    if effective_stage == "meal":
        after_labels.append(after_labels_map.get("cafe_rest", "카페"))
    elif effective_stage == "cafe_rest":
        after_labels.append(after_labels_map.get("go_home", "귀가"))
    elif effective_stage == "indoor_visit":
        if after == "meal":
            after_labels.append(after_labels_map.get("meal", "식사"))
        else:
            after_labels.append(after_labels_map.get("cafe_rest", "카페"))

    n_ct = sum(1 for p in ranked if p.get("source_type") == "citytour_api")
    n_go = sum(1 for p in ranked if p.get("source_type") == "google_places")
    meta = {
        "radius_used": radius_used,
        "fallback_applied": fallback_applied,
        "trip_state": trip_state,
        "spot_meta_used": bool(spot_meta.get("id") or spot_meta.get("role_tags")),
        "fallback_note": fallback_note,
        "time_band": tb_resolved,
        "replace_step": replace_step_mode,
        "replace_step_index": replace_step_index if replace_step_mode else None,
        "replace_step_role": (replace_step_role or "").strip() or None if replace_step_mode else None,
        "review_meta_applied": review_meta_applied,
        "duration": dur_flow,
        "continuation_depth_hint": {
            "2h": "다음 한 단계만 강하게 제안",
            "half-day": "쉬었다가 다음 장면까지",
            "full-day": "오후·저녁까지 여유 있게",
        }.get(dur_flow, "반나절"),
        "source_mix": {
            "google_places": n_go,
            "citytour_api": n_ct,
            "merged_candidate_count": sum(
                1 for p in ranked if p.get("merged_candidate_flag")
            ),
        },
        "indoor_transition_split": indoor_transition_split,
    }

    after_this_top = _after_this_short(effective_stage, dur_flow)

    meal_key = meal_style.get("key")
    cuisine_bias_out: dict[str, float] = {}
    if use_meal_flow and meal_key and str(meal_key) not in ("none", "cafe_rest", "indoor_comfort"):
        cuisine_bias_out = cuisine_bias_vector(str(meal_key))

    out: dict[str, Any] = {
        "course_path": path_norm,
        "guided_flow_notes": guided_notes,
        "next_step_headline": next_step_headline,
        "next_scene": next_scene_payload,
        "scene_mode": scene_mode_block,
        "next_stage": {
            "type": effective_stage,
            "title": _stage_title(effective_stage, hour),
            "why": stage_why if not indoor_transition_split else scene_mode_block.get("why") or [],
            "headline": next_step_headline,
        },
        "meal_style": {
            "key": meal_style.get("key"),
            "label": meal_style.get("label"),
            "secondary_key": meal_style.get("secondary_key"),
            "secondary_label": meal_style.get("secondary_label"),
            "why": meal_style.get("why") or [],
            "need_meal": meal_style.get("need_meal"),
            "need_rest": meal_style.get("need_rest"),
        },
        "cuisine_bias": cuisine_bias_out,
        "after_this": after_this_top,
        "primary_recommendation": None,
        "primary_place": None,
        "primary_restaurant": None,
        "alternatives": alternatives,
        "meta": meta,
        "next_places": ranked[:12],
        "next_scoring_model": "course_continuation.v3_meal_cuisine",
        "context": {"intent": intent_use, "weather_scores_used": scores},
        "ml_next_scene": ml_next_scene,
    }

    if primary:
        km = float(primary["distance_from_prev_km"])
        comp = primary.get("score_breakdown") or {}
        mob = _mobility_line_next(km, intent_use)
        stage_why_for_place = (
            list(scene_mode_block.get("why") or []) if indoor_transition_split else list(stage_why)
        )
        if use_meal_flow:
            b = explain_restaurant_why(
                str(meal_style.get("label") or ""),
                comp,
                mob,
            )
            a_stage = list(stage_why_for_place[:2])
            c = after_this_top
        else:
            a_stage, b, c = explain_primary(
                effective_stage,
                stage_why_for_place,
                primary,
                comp,
                km,
                trip_state,
                intent_use,
                after_labels,
                dur_flow,
            )
        sig = primary.get("review_signal_lines")
        if isinstance(sig, list) and sig:
            b = list(b) + [str(s) for s in sig if str(s).strip()][:3]
            b = b[:6]
        primary["why_next_stage"] = a_stage
        primary["why_this_place"] = b
        primary["after_this"] = c
        dm = approximate_drive_minutes(km) if intent_use.get("transport") == "car" else None
        def _data_source_note(pr: dict[str, Any]) -> str | None:
            if pr.get("merged_candidate_flag"):
                return "공공데이터 + 지도 검색 보강"
            if pr.get("source_type") == "citytour_api":
                return "공공 관광 데이터 기반 후보"
            return None

        dsn = _data_source_note(primary)
        pr_block = {
            "name": primary.get("name"),
            "score": round(float(primary.get("next_course_score") or 0.0) * 100.0, 1),
            "place_id": primary.get("place_id"),
            "source_type": primary.get("source_type") or "google_places",
            "source_mix": primary.get("source_mix") or "google_places",
            "public_data_match": bool(primary.get("public_data_match")),
            "merged_candidate_flag": bool(primary.get("merged_candidate_flag")),
            "data_source_note": dsn,
            "why": b,
            "after_this": c,
            "after_this_title": "식사 후 이어가기" if effective_stage == "meal" else "이후 이어가기",
            "score_breakdown": comp,
            "distance_from_prev_km": primary.get("distance_from_prev_km"),
            "drive_minutes_approx": dm,
            "practical_info": {
                "mobility_line": mob,
                "transport_note": (
                    "직선거리 근사입니다. 공식 내비에서 확인해 주세요."
                    if intent_use.get("transport") == "car"
                    else "대중교통 소요는 노선에 따라 다릅니다."
                ),
            },
            "address": primary.get("address"),
            "types": primary.get("types"),
        }
        rf = primary.get("review_features")
        if isinstance(rf, dict) and rf:
            pr_block["review_features"] = {
                k: v for k, v in rf.items() if k != "review_sample_count"
            }
        out["primary_recommendation"] = pr_block
        out["primary_restaurant"] = pr_block
        out["primary_place"] = {
            "name": pr_block.get("name"),
            "why": b,
            "after_this": c,
        }

    decision_mode = (
        "replace_step"
        if replace_step_mode
        else (
            "user_explicit"
            if user_stage_from_hint
            else ("model_assisted" if ml_next_scene.get("model_used") else "rule_time_heuristic")
        )
    )
    out["course_control"] = {
        "applied_user_hint": hint_raw or None,
        "desired_next_scene": (desired_next_scene or "").strip() or None,
        "desired_course_style": (desired_course_style or "").strip() or None,
        "effective_stage": str(effective_stage),
        "decision_mode": decision_mode,
        "next_scene_reason_mode": ml_next_scene.get("next_scene_reason_mode"),
        "ml_model_used": bool(ml_next_scene.get("model_used")),
        "replace_step": replace_step_mode,
        "step_index": replace_step_index if replace_step_mode else None,
        "step_role": (replace_step_role or "").strip() or None if replace_step_mode else None,
        "time_band": tb_resolved,
        "bias": {
            "family": family_bias,
            "scenic": scenic_bias,
            "indoor": indoor_bias,
            "meal": meal_bias,
            "cafe": cafe_bias,
        },
    }

    return out
