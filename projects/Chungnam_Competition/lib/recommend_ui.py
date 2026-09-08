# -*- coding: utf-8 -*-
"""
관광 추천 카드용 UI 필드(점수축·짧은 근거·이동 정보). main_scoring과 순환 import 방지용.
"""
from __future__ import annotations

from typing import Any

from lib.place_narrative import build_place_narrative
from lib.scoring_config import MAIN_WEIGHTS
from lib.text_explanation_layer import build_explanation_extras


def contribution_points(components: dict[str, float]) -> dict[str, float]:
    """main_scoring과 동일 공식. daytrip_planner ↔ main_scoring 순환 import를 피하기 위해 여기 둔다."""
    out: dict[str, float] = {}
    for k, w in MAIN_WEIGHTS.items():
        out[k] = round(float(components.get(k, 0.0)) * w / 100.0, 4)
    return out


def _top_contributions(contributions: dict[str, float], limit: int = 3) -> list[tuple[str, float]]:
    return sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:limit]


_AXIS_LABEL_SHORT: dict[str, str] = {
    "weather_fit": "날씨 적합",
    "goal_fit": "목적 적합",
    "distance_fit": "이동 적합",
    "time_fit": "시간 적합",
    "season_event_bonus": "보너스",
}


def build_score_axis_display(components: dict[str, float]) -> list[dict[str, Any]]:
    """만점 대비 획득 점수(종합 100점 환산과 일치)."""
    out: list[dict[str, Any]] = []
    for k, w in MAIN_WEIGHTS.items():
        comp = float(components.get(k, 0.0))
        earned = round(comp * w, 1)
        out.append(
            {
                "key": k,
                "label": _AXIS_LABEL_SHORT.get(k, k),
                "earned": earned,
                "max": float(w),
            }
        )
    return out


def _duration_fit_caption(intent: dict[str, str]) -> str:
    """일정 길이별 한 줄(홈페이지 규칙 설명용, 점수와 분리)."""
    dur = (intent.get("duration") or "half-day").strip().lower()
    if dur == "2h":
        return "약 2시간: 메인 한 곳 중심·이동 부담 적은 편인지 봤어요."
    if dur == "full-day":
        return "종일: 오전·오후 나눠 쉬며 이어가기 좋은지 봤어요."
    return "반나절: 한 번 쉬고 다음 장면까지 무난한지 봤어요."


def approximate_drive_minutes(km: float) -> int:
    if km is None or km < 0 or km > 400:
        return 0
    road_km = float(km) * 1.28
    m = int(round(road_km / 38.0 * 60))
    return max(5, min(m, 180))


def build_practical_info(
    dest: dict[str, Any],
    intent: dict[str, str],
    distance_km: float,
) -> dict[str, Any]:
    km = float(distance_km) if distance_km is not None and distance_km >= 0 else -1.0
    transport = intent.get("transport", "car")
    if km < 0:
        return {
            "distance_km": None,
            "drive_minutes_approx": None,
            "mobility_line": "거리 정보가 없어 이동 시간은 표시하지 않습니다.",
            "mobility_line_distance": None,
            "mobility_line_drive": None,
            "transport_note": "공식 지도·내비에서 실제 소요를 확인해 주세요.",
        }
    if transport == "car":
        dm = approximate_drive_minutes(km)
        return {
            "distance_km": round(km, 2),
            "drive_minutes_approx": dm,
            "mobility_line": f"실제 거리 약 {km:.1f}km · 자가용 기준 약 {dm}분(근사)",
            "mobility_line_distance": f"실제 거리 약 {km:.1f}km",
            "mobility_line_drive": f"자가용 기준 약 {dm}분(근사)",
            "transport_note": "직선거리 근사이며 실제 도로·혼잡과 다를 수 있습니다.",
        }
    return {
        "distance_km": round(km, 2),
        "drive_minutes_approx": None,
        "mobility_line": f"직선거리 약 {km:.1f}km · 대중교통 소요는 노선에 따라 달라집니다",
        "mobility_line_distance": f"직선거리 약 {km:.1f}km",
        "mobility_line_drive": None,
        "transport_note": "환승·배차는 반영하지 않은 거리만 표시합니다.",
    }


def concise_explanation_lines(
    dest: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
    contributions: dict[str, float],
) -> list[str]:
    """짧은 근거(최대 2줄). 상세는 why_recommend_bullets·접기 영역으로."""
    tops = _top_contributions(contributions, 3)
    goal = intent.get("trip_goal", "healing")
    duration = intent.get("duration", "half-day")
    tags = dest.get("tags") or []
    tag_s = [f"#{t}" for t in tags[:3]]
    pp = float(weather.get("precip_prob", 0))
    sky = int(weather.get("sky", 1))
    sky_soft = {1: "맑은 편", 3: "구름 낀 편", 4: "흐린 편"}.get(sky, "예보 기준")
    dur_ko = {"2h": "짧은 일정", "half-day": "반나절", "full-day": "종일"}.get(duration, "일정")
    goal_ko = {
        "healing": "힐링",
        "photo": "사진",
        "walking": "산책",
        "indoor": "실내",
        "culture": "문화",
        "kids": "아이 동반",
    }.get(goal, goal)
    cat = dest.get("category") or "outdoor"
    lines: list[str] = []
    for key, pt in tops:
        if pt < 0.028:
            continue
        if key == "weather_fit":
            if cat == "outdoor" and pp < 40 and not scores.get("is_raining"):
                lines.append(f"오늘은 바깥 활동하기 크게 무리 없는 날씨예요({sky_soft}).")
            elif cat == "indoor":
                lines.append("실내 위주라 날씨가 조금 흔들려도 부담이 적은 편이에요.")
            else:
                lines.append("오늘 날씨 맥락을 반영해 골랐어요.")
        elif key == "goal_fit":
            tw = " ".join(tag_s) if tag_s else "장소 분위기"
            lines.append(f"{goal_ko} 목적이랑 {tw}가 잘 맞아요.")
        elif key == "distance_fit":
            lines.append(f"{dur_ko}로 다녀오기에 이동 부담이 적은 편이에요.")
        elif key == "time_fit":
            lines.append("지금 시간·일정 길이에도 무리가 적어요.")
        elif key == "season_event_bonus":
            lines.append("노을·사진 포인트 같은 가산이 붙은 장소예요.")
        if len(lines) >= 2:
            break
    if not lines:
        lines.append("날씨·목적·거리를 함께 본 추천이에요.")
    return lines[:2]


def why_recommend_bullets(
    dest: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
    contributions: dict[str, float],
) -> list[str]:
    """「왜 추천했나요?」용 짧은 불릿 3개."""
    tops = _top_contributions(contributions, 4)
    goal = intent.get("trip_goal", "healing")
    duration = intent.get("duration", "half-day")
    cat = dest.get("category") or "outdoor"
    pp = float(weather.get("precip_prob", 0))
    goal_ko = {
        "healing": "힐링",
        "photo": "사진",
        "walking": "산책",
        "indoor": "실내",
        "culture": "문화",
        "kids": "아이 동반",
    }.get(goal, goal)
    dur_ko = {"2h": "짧은 일정", "half-day": "반나절", "full-day": "종일"}.get(duration, "일정")
    out: list[str] = []
    for key, pt in tops:
        if pt < 0.022:
            continue
        if key == "weather_fit":
            if scores.get("is_raining") or pp >= 70:
                out.append("비·강수 가능성을 감안해 실내/야외 균형을 봤어요.")
            elif cat == "outdoor":
                out.append("오늘 날씨에 야외 나가기 무난해요.")
            else:
                out.append("날씨 맥락에서 부담 적은 유형이에요.")
        elif key == "goal_fit":
            out.append(f"{goal_ko} 목적과 잘 맞아요.")
        elif key == "distance_fit":
            out.append(f"{dur_ko} 안에 다녀오기 좋아요.")
        elif key == "time_fit":
            out.append("지금 시간대에도 무리가 적어요.")
        elif key == "season_event_bonus":
            out.append("노을·사진 같은 포인트가 있어요.")
        if len(out) >= 3:
            break
    if len(out) < 2:
        out.append("날씨·목적·거리를 함께 반영했어요.")
    try:
        ch = int(str(intent.get("child_count") or "0").strip() or "0")
    except ValueError:
        ch = 0
    if ch > 0 and len(out) < 3:
        out.insert(0, "아이 동반일 때는 이동·쉬는 흐름을 조금 더 봤어요.")
    return out[:3]


def _decision_conclusion_label(
    rank_index: int,
    my_score: float,
    peer_scores: list[float],
) -> str:
    """순위·점수 간격으로 한 줄 결론 라벨(점수 숫자 노출 최소화)."""
    if not peer_scores:
        return "오늘 가기 좋아요"
    s0 = float(peer_scores[0])
    s1 = float(peer_scores[1]) if len(peer_scores) > 1 else s0
    gap_top2 = (s0 - s1) if len(peer_scores) > 1 else 0.05
    if rank_index == 0:
        if gap_top2 >= 0.04:
            return "오늘 가장 추천해요"
        if gap_top2 >= 0.018:
            return "오늘 가기 좋아요"
        return "오늘 가기 좋아요"
    if rank_index == 1:
        if (s0 - my_score) <= 0.012:
            return "무난한 선택이에요"
        return "지금은 대안으로 괜찮아요"
    s_prev = float(peer_scores[rank_index - 1]) if rank_index - 1 < len(peer_scores) else s0
    if (s_prev - my_score) <= 0.015 and (my_score - s0) >= -0.02:
        return "무난한 선택이에요"
    return "대안으로 괜찮아요"


def _lead_pair(
    dest: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
    contributions: dict[str, float],
) -> tuple[str, str]:
    """날씨 한 줄 + 장소 한 줄(부드러운 톤)."""
    tops = _top_contributions(contributions, 2)
    first = tops[0][0] if tops else "weather_fit"
    pp = float(weather.get("precip_prob", 0))
    sky = int(weather.get("sky", 1))
    sky_soft = {1: "맑은 편", 3: "구름 낀 편", 4: "흐린 편"}.get(sky, "예보 기준")
    cat = dest.get("category") or "outdoor"
    name = str(dest.get("name") or "이 장소")
    goal = intent.get("trip_goal", "healing")
    goal_ko = {
        "healing": "힐링",
        "photo": "사진",
        "walking": "산책",
        "indoor": "실내",
        "culture": "문화",
        "kids": "아이 동반",
    }.get(goal, goal)
    dur = intent.get("duration", "half-day")
    dur_ko = {"2h": "짧게", "half-day": "반나절", "full-day": "종일"}.get(dur, "당일")

    if scores.get("is_raining") or pp >= 70:
        wline = "오늘은 비 가능성이 있어, 실내·야외를 함께 본 추천이에요."
    elif cat == "outdoor" and pp < 45:
        wline = f"오늘은 바깥 활동하기 크게 무리 없는 날씨예요({sky_soft})."
    else:
        wline = f"오늘 날씨({sky_soft})를 반영했어요."

    tags = dest.get("tags") or []
    tag_preview = ", ".join(str(t) for t in tags[:2]) if tags else "장소 성격"
    if first == "goal_fit":
        pline = f"{name}은(는) {goal_ko} 목적이랑 {tag_preview}가 잘 맞는 편이에요."
    elif first == "distance_fit":
        pline = f"{name}은(는) {dur_ko} 코스로 다녀오기 부담이 적은 편이에요."
    elif first == "weather_fit" and cat == "indoor":
        pline = f"{name}은(는) 날씨가 흔들려도 쉬기 좋은 실내형에 가깝습니다."
    else:
        pline = f"{name}은(는) {goal_ko}·{dur_ko} 일정에 어울리게 골랐어요."
    return wline, pline


def default_caution_lines() -> list[str]:
    return [
        "운영·휴무는 공식 채널에서 한 번만 더 확인해 주세요.",
    ]


def build_ui_fields_for_destination(
    dest: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
    *,
    rank_index: int = 0,
    peer_scores: list[float] | None = None,
) -> dict[str, Any]:
    comp = dest.get("score_breakdown") or {}
    contrib = dest.get("score_contributions") or contribution_points(comp)
    km = float(dest.get("distance_km") or -1.0)
    peers = peer_scores if peer_scores is not None else [float(dest.get("score", 0))]
    my_score = float(dest.get("score", 0))
    narr = build_place_narrative(
        dest, weather, scores, intent, rank_index=rank_index, contributions=contrib
    )
    wlead, plead = _lead_pair(dest, weather, scores, intent, contrib)
    # 4층 내러티브: 상단 2줄은 장소 정체성 + 오늘 맥락(날씨·일정만 반복하지 않음)
    line_a, line_b = narr["summary_two_lines"][0], narr["summary_two_lines"][1]
    lead_w = line_a if len(line_a) >= 8 else wlead
    lead_p = line_b if len(line_b) >= 8 else plead

    base_dec = _decision_conclusion_label(rank_index, my_score, peers)
    if rank_index == 0:
        decision = narr["duration_conclusion"]
    else:
        decision = base_dec

    def_caut = default_caution_lines()
    caution_merged = list(narr["departure_checks"])
    for c in def_caut:
        if c and c not in caution_merged and all(c not in x for x in caution_merged):
            caution_merged.append(c)

    pr_info = {**build_practical_info(dest, intent, km), "duration_fit_line": _duration_fit_caption(intent)}

    _extras = build_explanation_extras(dest, weather, scores, intent, narr)
    _exp_points = _extras.get("expectation_points") or narr["expectation_bullets"]

    return {
        "total_score_100": int(round(float(dest.get("score", 0)) * 100)),
        "score_axis_display": build_score_axis_display(comp),
        "top_reason_tokens": [k for k, _ in _top_contributions(contrib, 3)],
        "concise_explanation_lines": [line_a, line_b][:2],
        "why_recommend_bullets": narr["why_recommend_bullets_narrative"],
        "decision_conclusion": decision,
        "lead_weather_sentence": lead_w,
        "lead_place_sentence": lead_p,
        "practical_info": pr_info,
        "caution_lines": caution_merged[:4],
        "place_identity": narr["place_identity"],
        "place_identity_summary": _extras.get("place_identity_summary"),
        "why_today_narrative": narr["why_today"],
        "expectation_bullets": _exp_points,
        "expectation_points": _exp_points,
        "enriched_tags": _extras.get("enriched_tags", []),
        "narrative_archetype": narr["narrative_archetype"],
    }
