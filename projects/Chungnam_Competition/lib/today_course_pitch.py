# -*- coding: utf-8 -*-
"""
오늘 코스 한 덩어리 ‘피치’(2~3문장). 랭킹은 이미 끝난 뒤, 구조화 사실만 자연어로.
"""
from __future__ import annotations

from typing import Any

from lib.ollama_client import ollama_available, ollama_chat

_SYS = """당신은 한국어 여행 안내 문구를 짧고 따뜻하게 다듬는 보조다.
다음 JSON에 있는 사실만 사용하라. 새로운 수치·영업·실시간·혼잡 정보를 지어내지 마라.
2~3문장, 과장·시 권하지 말고 담백하게."""


def _dur_ko(d: str) -> str:
    m = {
        "2h": "약 2시간",
        "half-day": "반나절",
        "full-day": "종일",
    }
    return m.get(d, d)


def _goal_ko(g: str) -> str:
    m = {
        "healing": "힐링",
        "photo": "사진",
        "walking": "걷기",
        "indoor": "실내",
        "culture": "문화",
        "kids": "아이 동반",
    }
    return m.get(g, g)


def _dust_line(dust: int) -> str:
    if dust >= 3:
        return "미세먼지가 나쁜 편"
    if dust == 2:
        return "미세먼지는 보통"
    return "미세먼지는 괜찮은 편"


def build_pitch_from_struct(s: dict[str, Any]) -> str:
    """완전 결정론 템플릿(항상 사용 가능)."""
    name = s.get("place_name") or "이 장소"
    dur = _dur_ko(str(s.get("duration") or "half-day"))
    g = _goal_ko(str(s.get("trip_goal") or "healing"))
    a = int(s.get("adult_count") or 1)
    c = int(s.get("child_count") or 0)
    t = s.get("temp_c")
    pp = s.get("precip_prob")
    sky = s.get("sky_text") or "예보"
    dline = _dust_line(int(s.get("dust") or 1))
    pp_f = float(pp or 0)
    rainy = bool(s.get("is_rainy") or pp_f >= 60)
    soft_mix = 30 <= pp_f < 50
    why = s.get("rule_reasons") or []
    w1 = why[0] if why else f"{g} 목적과 거리·날씨 맥락을 함께 봤어요."
    ident = s.get("place_identity_summary") or f"오늘 일정에 맞게 {name}를 추천했어요."
    ex = s.get("expectation_points") or []
    e1 = ex[0] if ex else "현장에서 분위기를 확인하며 둘러보기 좋아요."
    p0 = f"{name}—{ident} {dur}·{g} 목적에 맞게 골랐어요."
    if c > 0 or s.get("companion") == "family":
        p0 += f" (성인 {a}·어린이 {c} 동선을 염두에 뒀어요.)"
    p1 = f"오늘 기온 {t}°쯤, {sky}, 강수 {pp}%, {dline}."
    if pp_f < 30:
        p1 += " 강수 가능성은 낮아 맑은 날 가볍게 둘러보기 좋아요."
    elif soft_mix:
        p1 += " 강수가 잡힐 수 있어 짧은 동선·실내를 섞기 좋아요."
    elif rainy or pp_f >= 50:
        p1 += " 비 가능성을 고려해 실내·짧은 동선 위주로 골랐어요."
    p2 = f"추천 근거: {w1} 기대 포인트: {e1}"
    ca = s.get("departure_check")
    c0 = (ca[0] if ca else "운영·휴무는 공식 안내로 한 번만 더 확인해 주세요.")[:90]
    p3 = f"출발 전: {c0}"
    return "\n\n".join([p0, p1, p2, p3])


def _i(v: Any, default: int) -> int:
    try:
        return int(str(v).strip() or str(default))
    except ValueError:
        return default


def build_struct_from_top_recommendation(
    row: dict[str, Any], weather: dict[str, Any], scores: dict[str, Any], intent: dict[str, str]
) -> dict[str, Any]:
    w = list(row.get("why_recommend_bullets") or row.get("concise_explanation_lines") or [])
    return {
        "place_name": str(row.get("name") or ""),
        "adult_count": _i(intent.get("adult_count"), 1),
        "child_count": _i(intent.get("child_count"), 0),
        "companion": intent.get("companion"),
        "duration": intent.get("duration", "half-day"),
        "trip_goal": intent.get("trip_goal", "healing"),
        "place_identity_summary": str(row.get("place_identity_summary") or ""),
        "expectation_points": list(row.get("expectation_points") or row.get("expectation_bullets") or []),
        "departure_check": list(row.get("caution_lines") or [])[:2],
        "rule_reasons": w[:2],
        "temp_c": weather.get("temp"),
        "precip_prob": weather.get("precip_prob"),
        "sky_text": {1: "맑은 편", 3: "구름이 많은 편", 4: "흐린 편"}.get(
            int(weather.get("sky") or 1), "예보 기준"
        ),
        "sky": int(weather.get("sky") or 1),
        "dust": int(weather.get("dust") or 1),
        "is_rainy": bool(
            (scores or {}).get("is_raining")
            or int(weather.get("precip_prob", 0) or 0) >= 60
        ),
    }


def generate_today_course_pitch(
    struct: dict[str, Any]
) -> tuple[str, str]:
    """
    Returns: (text, source) source in template | ollama | ollama_failed
    """
    t_base = build_pitch_from_struct(struct)
    if not ollama_available():
        return t_base, "template"

    blob = "\n".join(
        [
            f"이름: {struct.get('place_name')}",
            f"짧은 정체성: {struct.get('place_identity_summary')}",
            f"의도/일정: {struct.get('trip_goal')}, {struct.get('duration')}, "
            f"인원(성인/어린이): {struct.get('adult_count')}/{struct.get('child_count')}",
            f"날씨(참고): {struct.get('temp_c')}°C, 강수확률 {struct.get('precip_prob')}%, "
            f"하늘: {struct.get('sky_text')}, 미세: {struct.get('dust')}",
            f"규칙 근거: {', '.join(struct.get('rule_reasons') or [])}",
            f"기대: {'; '.join(struct.get('expectation_points') or [])}",
            f"출발 전: {'; '.join(struct.get('departure_check') or [])}",
        ]
    )
    o = ollama_chat(
        _SYS,
        "아래 사실만으로 2~3문장 한국어. 따뜻·담백. JSON 밖 사실 금지.\n\n" + blob,
    )
    if o and 40 <= len(o) <= 900:
        return o.strip(), "ollama"
    return t_base, "ollama_failed"
