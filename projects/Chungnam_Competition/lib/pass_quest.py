# -*- coding: utf-8 -*-
"""패스퀘스트 조립: 기존 코스 뷰를 미션형으로 투영하고, 향후 Pass Quest Reranker 연결을 위해 메타를 남깁니다."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from lib.pass_scoring import (
    avg_review_score_from_steps,
    distance_burden_proxy,
    indoor_ratio_from_steps,
    meal_timing_fit_score,
    score_benefit_row,
    score_local_spend,
    score_pass_completion_ease,
    score_pass_fit_row,
    score_pass_route_efficiency,
    score_time_ticket_fit,
)
from lib.tourpass_catalog import catalog_row_for_place, load_tourpass_rules, merge_pass_fields_into_place

RERANK_FEATURES = [
    "pass_fit",
    "weather_fit",
    "time_ticket_fit_score",
    "distance_burden",
    "meal_timing_fit",
    "indoor_ratio",
    "local_spend_score",
    "review_score",
    "completion_ease",
    "ticket_type",
    "party_type",
    "duration",
    "transport",
]


def _truthy(v: Any) -> bool:
    if v is True:
        return True
    if v in (False, None, "", 0):
        return False
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "on")


def pass_context_active(pass_context: dict[str, Any] | None) -> bool:
    return _truthy((pass_context or {}).get("tourpass_mode"))


def _infer_pass_goal(trip_goal: str) -> str:
    m = {
        "indoor": "rainy_day_safe",
        "kids": "family_friendly",
        "culture": "experience_focused",
        "photo": "short_trip",
        "walking": "food_cafe_linked",
    }
    return m.get(str(trip_goal).strip(), "food_cafe_linked")


def _rec_map(recommendations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in recommendations:
        nm = str(r.get("name") or "").strip()
        if nm:
            out[nm] = r
    return out


def _step_for_name(steps: list[dict[str, Any]], name: str | None) -> dict[str, Any] | None:
    if not name:
        return None
    for s in steps:
        if str(s.get("name") or "").strip() == str(name).strip():
            return s
    return None


def _mission_slots_from_steps(
    steps: list[dict[str, Any]],
) -> list[tuple[str, str, str, dict[str, Any] | None]]:
    if not steps:
        return []

    def pick_first(roles: set[str]) -> dict[str, Any] | None:
        for s in steps:
            if str(s.get("step_role") or "") in roles:
                return s
        return None

    mains = pick_first({"main_spot", "secondary_spot"}) or steps[0]
    cafe = pick_first({"cafe_rest"})
    meal = pick_first({"meal"})

    second = cafe
    if not second:
        for s in steps:
            if s is mains:
                continue
            if str(s.get("step_role") or "") != "meal":
                second = s
                break

    third = meal
    if not third:
        for s in reversed(steps):
            if s is not mains and s is not second:
                third = s
                break

    slots: list[tuple[str, str, str, dict[str, Any] | None]] = [
        ("main_attraction", "관광·체험", "main", mains),
        ("cafe_or_experience", "카페·휴식·체험", "cafe", second if second is not mains else None),
        (
            "meal_or_local_spend",
            "식사·지역상권",
            "meal",
            third if third not in (None, mains, second) else meal,
        ),
    ]

    seen_ids: set[int] = set()
    cleaned: list[tuple[str, str, str, dict[str, Any] | None]] = []
    for role, label, rk, st in slots:
        if st is None:
            cleaned.append((role, label, rk, None))
            continue
        oid = id(st)
        if oid in seen_ids:
            cleaned.append((role, label, rk, None))
            continue
        seen_ids.add(oid)
        cleaned.append((role, label, rk, st))
    return cleaned


def _reason_for_mission(
    kind: str,
    weather: dict[str, Any],
    precip_prob: float,
    pass_goal: str,
) -> str:
    if kind == "main":
        if precip_prob >= 48:
            return "비 가능성을 고려해 실내·이동 부나가 덜한 순서를 우선했습니다."
        if pass_goal == "experience_focused":
            return "체험·관람 축을 앞에 두어 시간권 안에서 호흡을 맞췄습니다."
        return "관광·체험을 먼저 배치해 뒤쪽 이동이 자연스럽게 이어지도록 했습니다."
    if kind == "cafe":
        if pass_goal in ("food_cafe_linked", "rainy_day_safe"):
            return "카페·휴식으로 구간 사이 이동 부담을 나눴습니다."
        return "휴식·카페·가벼운 체험으로 리듬을 조절했습니다."
    if pass_goal == "benefit_first":
        return "혜택 가능성을 한 축으로 두되, 식사·상권 연결을 함께 맞췄습니다."
    return "현재 시간대와 지역상권·끼니 흐름을 함께 고려했습니다."


def _pass_signal_for_row(row: dict[str, Any]) -> str:
    if row.get("tourpass_available") is True:
        return "투어패스 활용 가능성이 있는 후보입니다"
    return "투어패스 활용 가능성을 참고한 후보입니다(방문 전 확인)"


def _build_missions(
    steps: list[dict[str, Any]],
    weather: dict[str, Any],
    pass_goal: str,
) -> list[dict[str, Any]]:
    precip = float(weather.get("precip_prob", 0) or 0)
    slots = _mission_slots_from_steps(steps)
    missions: list[dict[str, Any]] = []
    idx = 1
    for role, label, rk, st in slots:
        if not st:
            continue
        row = catalog_row_for_place(str(st.get("name") or ""))
        place = merge_pass_fields_into_place(dict(st))
        risk = str(row.get("pass_notice") or load_tourpass_rules().get("risk_notice_default") or "")
        missions.append(
            {
                "mission_index": idx,
                "role": role,
                "label": label,
                "place": place,
                "reason": _reason_for_mission(rk, weather, precip, pass_goal),
                "pass_signal": _pass_signal_for_row(row),
                "risk_notice": risk,
            }
        )
        idx += 1
    return missions


def _mission_step_list(missions: list[dict[str, Any]], all_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in missions:
        pl = m.get("place") or {}
        nm = str(pl.get("name") or "").strip()
        st = _step_for_name(all_steps, nm) or {
            "order": pl.get("order"),
            "step_role": pl.get("step_role"),
            "name": nm,
            "rating": pl.get("rating"),
            "review_count": pl.get("review_count"),
        }
        out.append(st)
    return out


def _catalog_rows_for_missions(missions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for m in missions:
        pl = m.get("place") or {}
        rows.append(catalog_row_for_place(str(pl.get("name") or "")))
    return rows


def resolve_quest_type(pass_goal: str, precip_prob: float, rules: dict[str, Any]) -> str:
    mp = rules.get("quest_type_map") or {}
    if pass_goal == "rainy_day_safe" or float(precip_prob or 0) >= 52:
        return "pass_rainy_day"
    return str(mp.get(pass_goal) or "pass_plan_b")


def _quest_title(city: str, ticket: str, pass_goal: str, precip: float) -> str:
    city_l = city if city != "전체" else "충남"
    tk = ticket if ticket not in ("none", "undecided") else "시간권"
    if precip >= 50:
        return f"{city_l} · 비 대비형 {tk} 패스퀘스트"
    if pass_goal == "experience_focused":
        return f"{city_l} · 체험·미식 중심 {tk} 패스퀘스트"
    return f"{city_l} · {tk} 활용 동선 패스퀘스트"


def _quest_summary(course: dict[str, Any], ticket: str, precip: float) -> str:
    dur = str(course.get("estimated_duration") or "").strip()
    w = "비 가능성을 반영했습니다." if precip >= 48 else "날씨·시간대에 맞춰 동선을 잡았습니다."
    t = f" {ticket} 시간권 기준으로" if ticket not in ("none", "undecided") else ""
    return f"{t} {dur + '·' if dur else ''}{w} 패스 활용도는 후보 메타·동선 규칙으로 추정하며, 혜택은 방문 전 확인이 필요합니다.".strip()


def _aggregate_scores_for_quest(
    course: dict[str, Any],
    all_steps: list[dict[str, Any]],
    missions: list[dict[str, Any]],
    pass_context: dict[str, Any],
    weather: dict[str, Any],
    intent: dict[str, str],
    rec_by_name: dict[str, dict[str, Any]],
) -> tuple[dict[str, float], dict[str, float]]:
    """(api_scores 표시용, rerank용 feature 전체)"""
    benefit_priority = str(pass_context.get("benefit_priority") or "none")
    ticket = str(pass_context.get("tourpass_ticket_type") or "none")
    duration_key = str(intent.get("duration") or "half-day")

    ms = _mission_step_list(missions, all_steps)
    rows = _catalog_rows_for_missions(missions)

    pfits = [score_pass_fit_row(r, benefit_priority) for r in rows] or [0.42]
    pass_fit = sum(pfits) / len(pfits)

    bfits = [score_benefit_row(r, benefit_priority) for r in rows] or [0.42]
    benefit_score = sum(bfits) / len(bfits)

    precip = float(weather.get("precip_prob", 0) or 0)
    weather_fit = max(0.0, min(1.0, 1.0 - precip / 100.0))

    time_ticket_fit = score_time_ticket_fit(ticket, duration_key, len(all_steps))
    local_spend = score_local_spend(ms if ms else all_steps, rows if rows else [catalog_row_for_place(None)])

    indoor_r = indoor_ratio_from_steps(all_steps, rec_by_name)
    completion_ease = score_pass_completion_ease(duration_key, len(all_steps), precip, indoor_r)
    route_eff = score_pass_route_efficiency(
        str(course.get("movement_burden") or ""),
        len(all_steps),
        pass_fit,
    )

    review_score = avg_review_score_from_steps(all_steps)
    meal_fit = meal_timing_fit_score(all_steps)
    dist_b = distance_burden_proxy(str(course.get("movement_burden") or ""))

    api_scores = {
        "pass_fit": round(float(pass_fit), 4),
        "weather_fit": round(float(weather_fit), 4),
        "time_ticket_fit": round(float(time_ticket_fit), 4),
        "benefit_score": round(float(benefit_score), 4),
        "local_spend_score": round(float(local_spend), 4),
        "pass_route_efficiency": round(float(route_eff), 4),
        "pass_completion_ease": round(float(completion_ease), 4),
    }

    rerank_features = {
        "pass_fit": pass_fit,
        "weather_fit": weather_fit,
        "time_ticket_fit_score": time_ticket_fit,
        "benefit_score": benefit_score,
        "distance_burden": dist_b,
        "meal_timing_fit": meal_fit,
        "indoor_ratio": indoor_r,
        "local_spend_score": local_spend,
        "review_score": review_score,
        "completion_ease": completion_ease,
        "pass_route_efficiency": route_eff,
        "ticket_type": ticket,
        "party_type": str(intent.get("companion") or ""),
        "duration": duration_key,
        "transport": str(intent.get("transport") or ""),
    }
    return api_scores, rerank_features


def _badges_from_quest(
    quest_type: str,
    missions: list[dict[str, Any]],
    precip: float,
    scores: dict[str, float],
) -> list[str]:
    badges: list[str] = ["패스 활용형"]
    if precip >= 45:
        badges.append("비·강수 대비")
    if quest_type in ("pass_food_cafe_linked", "pass_family_halfday"):
        badges.append("식사·상권 연결")
    if scores.get("local_spend_score", 0) >= 0.72:
        badges.append("지역상권 연결")
    roles = {str(m.get("role") or "") for m in missions}
    if "cafe_or_experience" in roles:
        badges.append("카페·휴식")
    if scores.get("time_ticket_fit", 0) >= 0.8:
        badges.append("시간권 적합")
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for b in badges:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out[:8]


def _quest_id_seed(parts: list[str]) -> str:
    h = hashlib.sha256()
    h.update(json.dumps(parts, ensure_ascii=False).encode("utf-8"))
    return f"pq_{h.hexdigest()[:14]}"


def build_pass_quest_for_course(
    course: dict[str, Any] | None,
    *,
    city: str,
    weather: dict[str, Any],
    intent: dict[str, str],
    pass_context: dict[str, Any],
    rec_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not course:
        return None
    steps = list(course.get("steps") or [])
    if not steps:
        return None

    rules = load_tourpass_rules()
    disclaimer = str(rules.get("pass_quest_disclaimer") or "")

    trip_g = str(intent.get("trip_goal") or "")
    pass_goal = str(pass_context.get("pass_goal") or "").strip() or _infer_pass_goal(trip_g)
    precip = float(weather.get("precip_prob", 0) or 0)
    if pass_goal != "rainy_day_safe" and precip >= 56:
        pass_goal = "rainy_day_safe"

    quest_type = resolve_quest_type(pass_goal, precip, rules)
    ticket = str(pass_context.get("tourpass_ticket_type") or "none")

    missions = _build_missions(steps, weather, pass_goal)
    scores_api, _feat = _aggregate_scores_for_quest(
        course, steps, missions, pass_context, weather, intent, rec_by_name
    )

    quest = {
        "quest_id": _quest_id_seed(
            [str(course.get("id") or ""), str(course.get("title") or ""), pass_goal, ticket]
        ),
        "quest_title": _quest_title(city, ticket, pass_goal, precip),
        "quest_type": quest_type,
        "ticket_type": ticket,
        "summary": _quest_summary(course, ticket, precip),
        "missions": missions,
        "badges": _badges_from_quest(quest_type, missions, precip, scores_api),
        "scores": {
            "pass_fit": scores_api["pass_fit"],
            "weather_fit": scores_api["weather_fit"],
            "time_ticket_fit": scores_api["time_ticket_fit"],
            "local_spend_score": scores_api["local_spend_score"],
            "completion_ease": scores_api["pass_completion_ease"],
        },
        "scores_detail": scores_api,
        "disclaimer": disclaimer,
    }
    return quest


def rule_based_rerank(
    quests: list[dict[str, Any]],
    features_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """가중 합으로 대안 패스퀘스트 순서를 정합니다. 향후 ML reranker 교체 지점."""

    def weight(q: dict[str, Any], feat: dict[str, Any]) -> float:
        # 안전·현실성(날씨·시간권) 우선, 그다음 패스·상권
        return (
            float(feat.get("weather_fit", 0.5)) * 0.22
            + float(feat.get("time_ticket_fit_score", 0.5)) * 0.22
            + float(feat.get("completion_ease", 0.5)) * 0.18
            + float(feat.get("pass_fit", 0.5)) * 0.14
            + float(feat.get("local_spend_score", 0.5)) * 0.12
            + float(feat.get("review_score", 0.5)) * 0.12
        )

    scored = sorted(
        zip(quests, features_list),
        key=lambda z: weight(z[0], z[1]),
        reverse=True,
    )
    rq = [z[0] for z in scored]
    expl = "규칙 기반 가중합으로 재정렬했습니다(모델 미사용)."
    return rq, expl


def enrich_top_course_steps_with_pass(top_course: dict[str, Any] | None) -> None:
    if not top_course:
        return
    steps = list(top_course.get("steps") or [])
    if not steps:
        return
    top_course["steps"] = [merge_pass_fields_into_place(dict(s)) for s in steps]


def attach_pass_quest_to_payload(
    out: dict[str, Any],
    pass_context: dict[str, Any],
    *,
    intent: dict[str, str],
    weather: dict[str, Any],
) -> None:
    """소비자 payload에 pass_quest 블록을 부착. tourpass_mode가 꺼져 있으면 enabled만 False."""

    rules = load_tourpass_rules()
    disclaimer = str(rules.get("pass_quest_disclaimer") or "")

    if not _truthy(pass_context.get("tourpass_mode")):
        out["pass_quest"] = {
            "enabled": False,
            "disclaimer": disclaimer,
        }
        return

    top = out.get("top_course")
    if not top:
        out["pass_quest"] = {
            "enabled": True,
            "ticket_type": str(pass_context.get("tourpass_ticket_type") or "none"),
            "top_pass_quest": None,
            "alternative_pass_quests": [],
            "pass_quest_rerank": {
                "model_used": False,
                "mode": "rule-based-fallback",
                "confidence": None,
                "features_used": RERANK_FEATURES,
                "explanation": "추천 코스가 없어 패스퀘스트를 구성하지 못했습니다.",
            },
            "disclaimer": disclaimer,
        }
        return

    rec_by_name = _rec_map(list(out.get("recommendations") or []))
    city = str(out.get("city") or intent.get("city") or "전체")

    enrich_top_course_steps_with_pass(top)

    top_quest = build_pass_quest_for_course(
        top,
        city=city,
        weather=weather,
        intent=intent,
        pass_context=pass_context,
        rec_by_name=rec_by_name,
    )

    alts_in = list(out.get("alternative_courses") or [])
    alt_quests: list[dict[str, Any]] = []
    alt_feats: list[dict[str, Any]] = []
    for ac in alts_in:
        q = build_pass_quest_for_course(
            ac if isinstance(ac, dict) else None,
            city=city,
            weather=weather,
            intent=intent,
            pass_context=pass_context,
            rec_by_name=rec_by_name,
        )
        if not q:
            continue
        steps = list((ac.get("steps") or [])) if isinstance(ac, dict) else []
        missions = q.get("missions") or []
        _s_api, feat = _aggregate_scores_for_quest(
            ac if isinstance(ac, dict) else {},
            steps,
            missions,
            pass_context,
            weather,
            intent,
            rec_by_name,
        )
        alt_quests.append(q)
        alt_feats.append(feat)

    reranked, expl = rule_based_rerank(alt_quests, alt_feats)

    out["pass_quest"] = {
        "enabled": True,
        "ticket_type": str(pass_context.get("tourpass_ticket_type") or "none"),
        "benefit_priority": str(pass_context.get("benefit_priority") or "none"),
        "pass_goal": str(pass_context.get("pass_goal") or "").strip()
        or _infer_pass_goal(str(intent.get("trip_goal") or "")),
        "purchased_status": str(pass_context.get("purchased_status") or "undecided"),
        "top_pass_quest": top_quest,
        "alternative_pass_quests": reranked,
        "pass_quest_rerank": {
            "model_used": False,
            "mode": "rule-based-fallback",
            "confidence": None,
            "features_used": RERANK_FEATURES,
            "explanation": expl,
        },
        "disclaimer": disclaimer,
        "future_model_env": {
            "PASS_QUEST_RERANK_MODEL": "향후 true 로 모델 경로 활성화",
            "PASS_QUEST_RERANK_MODEL_PATH": "예: 로컬 번들 또는 원격 엔드포인트",
        },
    }


def sync_top_pass_quest_only(
    course: dict[str, Any],
    *,
    weather: dict[str, Any],
    intent: dict[str, str],
    pass_context: dict[str, Any],
    recommendations: list[dict[str, Any]],
    city: str,
) -> dict[str, Any] | None:
    """단계 교체 후 top_course만 갱신됐을 때 패스퀘스트 일부를 재계산."""
    rec_by_name = _rec_map(recommendations)
    return build_pass_quest_for_course(
        course,
        city=city,
        weather=weather,
        intent=intent,
        pass_context=pass_context,
        rec_by_name=rec_by_name,
    )
