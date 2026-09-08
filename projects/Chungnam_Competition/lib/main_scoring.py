# -*- coding: utf-8 -*-
"""
메인 관광지 추천: 0~1 부분 점수 → 가중 합산 + 설명 템플릿.

daytrip_planner의 태그·의도 힌트를 재사용하되, 곱하기 모델이 아닌
가산·정규화된 goal_fit 등으로 분해 가능하게 만든다.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from lib.course_flow import infer_venue_kind
from lib.intent_hints import _COMPANION_HINTS, _GOAL_TAG_HINTS, _tags_lower


def _intent_party_size(intent: dict[str, str]) -> tuple[int, int]:
    try:
        a = int(str(intent.get("adult_count") or "1").strip() or "1")
    except ValueError:
        a = 1
    try:
        c = int(str(intent.get("child_count") or "0").strip() or "0")
    except ValueError:
        c = 0
    return max(1, min(10, a)), max(0, min(8, c))


def adjust_main_score_for_party_duration(
    dest: dict[str, Any],
    components: dict[str, float],
    intent: dict[str, str],
    distance_km: float,
) -> dict[str, float]:
    """홈페이지 규칙: 인원·일정 길이에 따른 완만한 보정(투명한 휴리스틱)."""
    out = {k: float(v) for k, v in components.items()}
    adults, children = _intent_party_size(intent)
    party = adults + children
    dur = (intent.get("duration") or "half-day").strip().lower()
    tags_l = _tags_lower(dest)
    km = float(distance_km) if distance_km is not None and distance_km >= 0 else -1.0
    al = str(dest.get("activity_level") or "moderate").lower()
    stay = int(dest.get("avg_stay_minutes") or 0)

    familyish = any(
        k in tg
        for tg in tags_l
        for k in ("가족", "어린이", "키즈", "체험", "family", "kid", "놀이")
    )

    if children > 0:
        if familyish:
            out["goal_fit"] = min(1.0, out.get("goal_fit", 0.5) + 0.07)
        if km > 38:
            out["distance_fit"] = max(0.06, out.get("distance_fit", 0.5) - 0.14)
        elif km > 24:
            out["distance_fit"] = max(0.1, out.get("distance_fit", 0.5) - 0.07)
        if al == "high":
            out["time_fit"] = max(0.18, out.get("time_fit", 0.5) - 0.08)

    if party >= 5:
        out["distance_fit"] = max(0.08, out.get("distance_fit", 0.5) - 0.09)
        out["time_fit"] = max(0.2, out.get("time_fit", 0.5) - 0.05)

    if dur == "2h":
        if stay > 120:
            out["time_fit"] = max(0.2, out.get("time_fit", 0.5) - 0.1)
        if al == "high":
            out["time_fit"] = max(0.22, out.get("time_fit", 0.5) - 0.07)
        if children > 0 and al == "high":
            out["goal_fit"] = max(0.12, out.get("goal_fit", 0.5) - 0.05)

    if dur == "full-day" and al == "low" and children == 0:
        out["time_fit"] = min(1.0, out.get("time_fit", 0.5) + 0.05)

    return {k: round(_clamp01(v), 4) for k, v in out.items()}
from lib.scoring_config import MAIN_WEIGHTS


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_raw_weather_match(
    dest: dict[str, Any],
    scores: dict[str, Any],
) -> float:
    """
    기존 recommend 로직과 동일한 '날씨 적합' 0~1.
    outdoor/indoor 가중·골든아워 보너스 포함.
    """
    w = dest["weather_weights"]
    if dest["category"] == "outdoor":
        weather_score = scores["outdoor"] * w["sunny"]
    else:
        weather_score = scores["indoor"] * w["rainy"]
        outdoor_penalty = scores["outdoor"] * 0.5
        weather_score = max(0.0, weather_score - outdoor_penalty)

    if dest.get("golden_hour_bonus") and scores["is_golden_hour"]:
        weather_score = min(weather_score + 0.3, 1.0)

    return _clamp01(float(weather_score))


def compute_goal_fit(dest: dict[str, Any], intent: dict[str, str]) -> float:
    """목적·동행과 태그 정합 0~1 (결정적)."""
    tags = _tags_lower(dest)
    goal = intent["trip_goal"]
    comp = intent["companion"]
    cat = dest.get("category") or ""

    hits = 0
    for hint in _GOAL_TAG_HINTS.get(goal, ()):
        if any(hint.lower() in tg for tg in tags):
            hits += 1
    g_score = 0.42 + min(0.36, hits * 0.12)
    if goal == "indoor" and cat == "indoor":
        g_score += 0.18
    for hint in _COMPANION_HINTS.get(comp, ()):
        if any(hint.lower() in tg for tg in tags):
            g_score += 0.06
    cf = dest.get("companion_fit")
    if isinstance(cf, list) and comp in cf:
        g_score += 0.08
    return _clamp01(g_score)


def compute_time_fit(
    dest: dict[str, Any],
    intent: dict[str, str],
    scores: dict[str, Any],
    hour: int,
    minute: int = 0,
) -> float:
    """시간대·일정 길이와의 정합 0~1."""
    dur = intent.get("duration", "half-day")
    g = intent["trip_goal"]
    h = int(hour) % 24
    mi = int(minute) % 60
    tod = h * 60 + mi

    t = 0.62
    if g == "photo" and scores.get("is_golden_hour"):
        t = 0.95
    elif g == "photo":
        t = 0.58

    if dur == "2h":
        al = str(dest.get("activity_level") or "moderate")
        if al == "low":
            t += 0.12
        elif al == "high":
            t -= 0.08
    elif dur == "half-day":
        t += 0.06
    elif dur == "full-day":
        t += 0.14

    if 10 * 60 <= tod <= 16 * 60 + 59 and g in ("walking", "healing"):
        t += 0.06

    vk = infer_venue_kind(dest)
    if 11 * 60 + 30 <= tod <= 13 * 60 + 30 and vk == "meal":
        t += 0.1
    if 17 * 60 <= tod <= 19 * 60 + 30 and vk == "meal":
        t += 0.1
    if (tod >= 20 * 60 or tod < 6 * 60) and vk == "cafe":
        t += 0.07
    if (tod >= 20 * 60 or tod < 6 * 60) and (dest.get("category") or "") == "indoor":
        t += 0.05

    return _clamp01(t)


def compute_season_event_bonus(
    dest: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
) -> float:
    """계절·이벤트·골든아워 보너스 채널 0~1 (대부분 중간값)."""
    tags = [str(x) for x in (dest.get("tags") or [])]
    tags_l = [x.lower() for x in tags]
    b = 0.38

    if dest.get("golden_hour_bonus") and scores.get("is_golden_hour"):
        b = 0.92
    if any("축제" in x or "행사" in x for x in tags):
        b = max(b, 0.78)
    if intent["trip_goal"] == "photo" and any(
        k in " ".join(tags_l) for k in ("일출", "야경", "전망", "일몰")
    ):
        b = max(b, 0.72)

    return _clamp01(b)


def compute_main_components(
    dest: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
    distance_fit: float,
    hour: int | None = None,
) -> dict[str, float]:
    """부분 점수 전부 0~1."""
    h = hour if hour is not None else int(weather.get("hour", datetime.now().hour))
    mi = int(weather.get("minute", 0) or 0)

    wf = compute_raw_weather_match(dest, scores)
    gf = compute_goal_fit(dest, intent)
    df = _clamp01(float(distance_fit))
    tf = compute_time_fit(dest, intent, scores, h, minute=mi)
    se = compute_season_event_bonus(dest, scores, intent)

    return {
        "weather_fit": round(wf, 4),
        "goal_fit": round(gf, 4),
        "distance_fit": round(df, 4),
        "time_fit": round(tf, 4),
        "season_event_bonus": round(se, 4),
    }


def adjust_components_for_precip_prob(
    components: dict[str, float],
    dest: dict[str, Any],
    precip_prob: float,
) -> dict[str, float]:
    """강수 확률 구간별로 weather_fit·time_fit을 추가 보정(랭킹이 눈에 띄게 달라지도록)."""
    pp = float(precip_prob)
    out = {k: float(v) for k, v in components.items()}
    cat = str(dest.get("category") or "")
    al = str(dest.get("activity_level") or "moderate").lower()

    if cat == "outdoor":
        if pp >= 60:
            out["weather_fit"] = max(0.02, out.get("weather_fit", 0.5) - 0.38)
        elif pp >= 50:
            out["weather_fit"] = max(0.06, out.get("weather_fit", 0.5) - 0.24)
        elif pp >= 32:
            # 30~50%: 혼합·짧은 동선 구간 — 야외 순위가 너무 붙지 않게
            out["weather_fit"] = max(
                0.1, out.get("weather_fit", 0.5) - 0.24 * (pp - 32) / 18
            )
        if pp >= 50 and al == "high":
            out["time_fit"] = max(0.14, out.get("time_fit", 0.5) - 0.12)
        elif pp >= 45 and al == "high":
            out["time_fit"] = max(0.16, out.get("time_fit", 0.5) - 0.08)
    elif cat == "indoor":
        if pp >= 60:
            out["weather_fit"] = min(
                1.0, out.get("weather_fit", 0.5) + 0.22 + 0.06 * min(1.0, (pp - 60) / 40)
            )
        elif pp >= 50:
            out["weather_fit"] = min(1.0, out.get("weather_fit", 0.5) + 0.14)
        elif pp >= 32:
            out["weather_fit"] = min(
                1.0, out.get("weather_fit", 0.5) + 0.06 + 0.12 * (pp - 32) / 18
            )
        elif pp >= 30:
            out["weather_fit"] = min(1.0, out.get("weather_fit", 0.5) + 0.05)

    return {k: round(_clamp01(v), 4) for k, v in out.items()}


def weighted_main_score(components: dict[str, float]) -> float:
    total = 0.0
    for k, w in MAIN_WEIGHTS.items():
        total += components[k] * (w / 100.0)
    return round(_clamp01(total), 4)


def contribution_points(components: dict[str, float]) -> dict[str, float]:
    """각 축이 만점 대비 기여한 '점'(가중치 반영)."""
    out: dict[str, float] = {}
    for k, w in MAIN_WEIGHTS.items():
        out[k] = round(components[k] * w / 100.0, 4)
    return out


def _top_factors(
    contributions: dict[str, float], limit: int = 3
) -> list[tuple[str, float]]:
    order = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
    return order[:limit]


_LABEL_KO = {
    "weather_fit": "날씨·대기 맥락",
    "goal_fit": "목적·동행",
    "distance_fit": "거리·당일 동선",
    "time_fit": "시간대·일정",
    "season_event_bonus": "시간대 보너스·태그",
}


def explain_main_destination(
    dest: dict[str, Any],
    components: dict[str, float],
    contributions: dict[str, float],
    intent: dict[str, str],
    weather: dict[str, Any],
    scores: dict[str, Any],
) -> dict[str, Any]:
    """상위 기여 요인 2~3개로 결정적 설명 문장 생성."""
    tops = _top_factors(contributions, 3)
    lines: list[str] = []

    for key, _pts in tops:
        if key == "weather_fit":
            pp = float(weather.get("precip_prob", 0))
            dust = int(weather.get("dust", 1))
            if scores.get("is_raining") or pp >= 60:
                lines.append("비 가능성이 있어 실내·우천에 강한 유형을 봤어요.")
            elif dest.get("category") == "outdoor" and pp < 30 and dust <= 2:
                lines.append("오늘은 밖에 나가기 무난한 날씨 맥락이에요.")
            else:
                lines.append("예보와 실내/야외 유형을 함께 반영했어요.")
        elif key == "goal_fit":
            tg = intent["trip_goal"]
            tag_preview = ", ".join([f"#{t}" for t in (dest.get("tags") or [])[:3]])
            lines.append(
                f"목적({tg})이랑 태그({tag_preview or '메타'})가 잘 맞는지 봤어요."
            )
        elif key == "distance_fit":
            lines.append("당일 기준 이동 부담이 지나치지 않게 거리를 봤어요.")
        elif key == "time_fit":
            lines.append("지금 시간·일정 길이를 함께 고려했어요.")
        elif key == "season_event_bonus":
            lines.append("노을·야경 같은 가산 태그가 있으면 반영했어요.")

    # 중복 제거(같은 문장)
    seen: set[str] = set()
    uniq: list[str] = []
    for ln in lines:
        if ln not in seen:
            seen.add(ln)
            uniq.append(ln)

    # 한 줄 요약(카드 중복 최소화): 가장 큰 기여 한 문장만
    summary = uniq[0] if uniq else "날씨·목적·거리를 함께 반영한 휴리스틱 점수입니다."

    return {
        "summary": summary,
        "top_factors": [
            {"key": k, "label": _LABEL_KO.get(k, k), "contribution": contributions[k]}
            for k, _ in tops
        ],
        "lines": uniq[:3],
    }
