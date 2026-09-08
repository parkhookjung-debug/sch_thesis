# -*- coding: utf-8 -*-
"""
/api/recommend 소비자용 — 완성 코스 단위 뷰 모델 (summary, top_course, alternative_courses, notice).

추천 단위는 **장소 1곳**이 아니라 **완성 코스(동선 단계 묶음)** 이다.
선택적 코스 재정렬은 lib.course_rerank 에서 처리한다(next_scene 단계 예측과 별개).
"""
from __future__ import annotations

import re
from typing import Any

from lib.course_rerank import apply_course_rerank
from lib.course_flow import consumer_label_for_role, flow_pitch_reasons
from lib.course_units import movement_burden_label, weather_fit_label

_SKY = {1: "맑음", 3: "구름 많음", 4: "흐림"}

_DEFAULT_COURSE_HERO = "/hero-course-placeholder.svg"

# destinations 자동태그·리뷰 특성 키 등 영문 snake_case → 카드용 한글
_TAG_LABEL_KO: dict[str, str] = {
    # 동행·유형
    "family_friendly": "가족 동행",
    "kids_friendly": "아이와 함께",
    "kids": "키즈",
    "couple": "연인",
    "solo": "혼자",
    "friends": "친구",
    # 경험
    "photo_friendly": "사진·포토",
    "healing": "힐링",
    "quiet": "조용함",
    "crowded": "붐빌 수 있음",
    "nature": "자연",
    "history": "역사",
    "culture": "문화",
    "festival": "축제",
    "experience": "체험",
    "leisure": "레저",
    "sports": "스포츠",
    "shopping": "쇼핑",
    # 식음·카페
    "quick_meal": "빠른 식사",
    "dessert_good": "디저트",
    "cafe": "카페",
    "food": "맛집",
    "korean_food": "한식",
    # 시간·체류
    "long_stay_ok": "여유 있게",
    "short_visit_ok": "짧게 들르기",
    "golden_hour": "노을·골든아워",
    # 날씨·환경
    "rainy_day_ok": "우천에도 무난",
    "indoor": "실내",
    "outdoor": "야외",
    # 편의
    "parking_easy": "주차 편함",
    "view_good": "전망·뷰",
    "walking": "걷기",
    "drive": "드라이브",
    "scenic": "경치",
    # 리뷰 기반 신호
    "trending": "요즘 인기",
    "high_rated": "평점 높음",
    "low_rated": "평점 낮음",
    "recently_reviewed": "최근 리뷰 있음",
}


def _ko_duration(d: str) -> str:
    return {"2h": "2시간", "half-day": "반나절", "full-day": "하루"}.get(d, d)


def _ko_companion(c: str) -> str:
    return {
        "solo": "1인",
        "couple": "커플",
        "family": "가족",
        "friends": "친구",
    }.get(c, c)


def _ko_goal(g: str) -> str:
    return {
        "healing": "힐링",
        "photo": "사진",
        "walking": "걷기",
        "indoor": "실내",
        "culture": "문화",
        "kids": "키즈",
    }.get(g, g)


def _ko_transport(t: str) -> str:
    return {"car": "자가용", "public": "대중교통"}.get(t, t)


def _step_labels(n: int, duration: str) -> list[str]:
    if n <= 1:
        return ["오늘의 핵심"]
    if n == 2:
        return ["핵심 코스", "가볍게 마무리"]
    if n == 3:
        return ["첫 방문", "이어서", "여유롭게 마무리"]
    return ["첫 방문", "쉬었다 가기", "오후", "마무리"][:n]


def _one_liner_from_pitch(pitch: str) -> str:
    t = (pitch or "").strip()
    if not t:
        return "가볍게 다녀오기 좋은 코스예요."
    first = re.split(r"[\n\r]+", t, maxsplit=1)[0].strip()
    if len(first) > 96:
        return first[:94] + "…"
    return first


def _reasons_three(first_place: dict[str, Any]) -> list[str]:
    bullets = first_place.get("why_recommend_bullets")
    if isinstance(bullets, list) and bullets:
        out = [str(x).strip() for x in bullets if str(x).strip()][:3]
    else:
        w = first_place.get("why") or first_place.get("concise_explanation_lines")
        if isinstance(w, str) and w.strip():
            out = [w.strip()][:3]
        elif isinstance(w, list) and w:
            out = [str(x).strip() for x in w if str(x).strip()][:3]
        else:
            out = []
    while len(out) < 3:
        out.append("오늘 조건에 맞게 골랐어요.")
    return out[:3]


def _shorten(s: str, n: int = 72) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _safe_image_src(value: Any) -> str:
    s = str(value or "").strip()
    if not s:
        return _DEFAULT_COURSE_HERO
    if "places.googleapis.com" in s and "/media" in s:
        m = re.search(r"/v1/(places/[^?]+?)/media", s)
        if m:
            from urllib.parse import quote

            return f"/api/place-photo?name={quote(m.group(1), safe='')}&maxHeightPx=720"
    return s


def _intro_paragraph(rec: dict[str, Any], cap: int = 900) -> str:
    """소개 문단(스토어 리뷰 아님 — 큐레이션·요약 필드)."""
    for key in (
        "copy",
        "recommendation_summary",
        "place_identity_summary",
        "lead_place_sentence",
        "story_summary",
    ):
        s = str(rec.get(key) or "").strip()
        if len(s) > 24:
            return s[:cap]
    w = rec.get("why_today_narrative")
    if isinstance(w, str) and w.strip():
        return w.strip()[:cap]
    return ""


def _merge_detail_bullets(rec: dict[str, Any], max_n: int = 8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for key in (
        "expectation_bullets",
        "expectation_points",
        "why_recommend_bullets",
        "concise_explanation_lines",
    ):
        v = rec.get(key)
        if isinstance(v, list):
            for x in v:
                s = str(x).strip()
                if s and s not in seen:
                    seen.add(s)
                    out.append(s)
        elif isinstance(v, str) and v.strip():
            s = v.strip()
            if s not in seen:
                seen.add(s)
                out.append(s)
        if len(out) >= max_n:
            return out[:max_n]
    return out[:max_n]


def _tag_labels(rec: dict[str, Any], max_n: int = 8) -> list[str]:
    t = rec.get("enriched_tags") or rec.get("tags") or []
    if isinstance(t, list):
        out: list[str] = []
        for x in t:
            s = str(x).strip()
            if not s:
                continue
            out.append(_TAG_LABEL_KO.get(s, s))
            if len(out) >= max_n:
                break
        return out
    return []


def _place_name_set(places: list[dict[str, Any]]) -> frozenset[str]:
    return frozenset(str(p.get("name") or "") for p in places if p.get("name"))


def _step_lat_lng(pl: dict[str, Any], merged: dict[str, Any]) -> tuple[float | None, float | None]:
    """추천·플랜 병합 행에서 좌표 추출(Google 리뷰 search 용)."""
    for src in (merged, pl):
        c = src.get("coords")
        if isinstance(c, dict):
            try:
                la = float(c.get("lat"))
                ln = float(c.get("lng"))
                if abs(la) > 1e-6 and abs(ln) > 1e-6:
                    return la, ln
            except (TypeError, ValueError):
                pass
        try:
            la = float(src.get("lat"))
            ln = float(src.get("lng"))
            if abs(la) > 1e-6 and abs(ln) > 1e-6:
                return la, ln
        except (TypeError, ValueError):
            pass
    return None, None


def _build_steps_for_places(
    places: list[dict[str, Any]],
    recs: list[dict[str, Any]],
    inp: dict[str, Any],
) -> list[dict[str, Any]]:
    n = len(places)
    labels = _step_labels(n, str(inp.get("duration", "half-day")))
    steps: list[dict[str, Any]] = []
    for i, p in enumerate(places):
        pl = p if isinstance(p, dict) else {}
        nm = str(pl.get("name", "") or "")
        rec_row = next((r for r in recs if str(r.get("name", "") or "") == nm), {}) or {}
        merged = {**rec_row, **pl}
        one_line = _shorten(
            str(
                pl.get("place_identity_summary")
                or pl.get("decision_conclusion")
                or pl.get("lead_place_sentence")
                or ""
            ),
            88,
        )
        if pl.get("meal_data_insufficient"):
            one_line = "식사 장소 데이터가 부족해요. 지도 앱에서 주변 식당을 검색해 주세요."
        elif not one_line:
            one_line = f"{_ko_goal(str(inp.get('trip_goal', 'healing')))}에 어울리는 곳이에요."
        intro = _intro_paragraph(merged)
        d_bullets = _merge_detail_bullets(merged)
        tags = _tag_labels(merged)
        img_src = _safe_image_src(
            pl.get("image")
            or rec_row.get("image")
            or merged.get("image")
            or ""
        )
        try:
            r_raw = merged.get("rating")
            rating_f = float(r_raw) if r_raw is not None else 0.0
        except (TypeError, ValueError):
            rating_f = 0.0
        try:
            rev_n = int(merged.get("review_count") or 0)
        except (TypeError, ValueError):
            rev_n = 0
        role = str(pl.get("step_role") or "").strip()
        step_label = (
            consumer_label_for_role(role)
            if role
            else (labels[i] if i < len(labels) else f"{i + 1}번")
        )
        la_v, ln_v = _step_lat_lng(pl, merged)
        step_row: dict[str, Any] = {
                "order": i + 1,
                "step_label": step_label,
                "step_role": role or None,
                "name": pl.get("name", ""),
                "one_line": one_line,
                "image": img_src or None,
                "address": pl.get("address", ""),
                "detail_intro": intro,
                "detail_bullets": d_bullets,
                "tag_labels": tags,
                "rating": round(rating_f, 2) if rating_f > 0 else None,
                "review_count": rev_n,
        }
        if la_v is not None and ln_v is not None:
            step_row["lat"] = la_v
            step_row["lng"] = ln_v
        steps.append(step_row)
    return steps


def _build_full_course_unit(
    *,
    course_id: str,
    title: str,
    places: list[dict[str, Any]],
    recs: list[dict[str, Any]],
    inp: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    user_lat: float,
    user_lng: float,
    pitch: str,
    reasons_title: str,
    reasons_override: list[str] | None,
    reason_tags: list[str],
    course_shape_reason: str | None = None,
) -> dict[str, Any]:
    if not places:
        return {}
    first_name = str(places[0].get("name") or "")
    first_e = next((r for r in recs if r.get("name") == first_name), recs[0] if recs else {})
    hero_img = _safe_image_src(places[0].get("image") or first_e.get("image") or "")
    if not hero_img:
        for p in places:
            im = _safe_image_src(p.get("image"))
            if im and im != _DEFAULT_COURSE_HERO:
                hero_img = im
                break
    if not hero_img:
        hero_img = _DEFAULT_COURSE_HERO
    reasons = (
        reasons_override
        if reasons_override is not None
        else _reasons_three({**(first_e or {}), **places[0]})
    )
    steps = _build_steps_for_places(places, recs, inp)
    raw_pitch = (pitch or "").strip()
    pitch_f = raw_pitch[:600] if raw_pitch else _one_liner_from_pitch("")
    if not pitch_f and steps:
        pitch_f = _one_liner_from_pitch(str(steps[0].get("one_line", "") or ""))
    plc_names = [str(p.get("name") or "") for p in places if p.get("name")]
    return {
        "course_id": course_id,
        "id": course_id,
        "title": title,
        "pitch": pitch_f,
        "reasons_title": reasons_title,
        "reasons": reasons,
        "reason_tags": reason_tags,
        "steps": steps,
        "hero_image": hero_img,
        "hero_name": str(places[0].get("name") or ""),
        "estimated_duration": _ko_duration(str(inp.get("duration", "half-day"))),
        "movement_burden": movement_burden_label(places, user_lat, user_lng),
        "weather_fit": weather_fit_label(weather, scores),
        "place_names": plc_names,
        "one_liner": _one_liner_from_pitch(pitch_f),
        "course_shape_reason": course_shape_reason,
    }


def _single_stop_course(
    *,
    course_id: str,
    title: str,
    one_liner: str,
    place_row: dict[str, Any],
    inp: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    user_lat: float,
    user_lng: float,
    reason_tags: list[str],
) -> dict[str, Any]:
    pl = {
        "name": place_row.get("name", ""),
        "place_identity_summary": place_row.get("place_identity_summary"),
        "decision_conclusion": place_row.get("decision_conclusion"),
        "lead_place_sentence": place_row.get("lead_place_sentence"),
        "image": _safe_image_src(place_row.get("image")),
        "address": place_row.get("address", ""),
        "category": place_row.get("category"),
        "coords": place_row.get("coords"),
        "score": place_row.get("score"),
    }
    unit = _build_full_course_unit(
        course_id=course_id,
        title=title,
        places=[pl],
        recs=[place_row],
        inp=inp,
        weather=weather,
        scores=scores,
        user_lat=user_lat,
        user_lng=user_lng,
        pitch=one_liner,
        reasons_title="이 코스는",
        reasons_override=[one_liner, "같은 조건에서 다른 장소를 엮었어요.", "짧게 둘러보기에 무난해요."],
        reason_tags=reason_tags,
    )
    return unit


def build_consumer_course_view(payload: dict[str, Any]) -> dict[str, Any]:
    """규칙 기반 완성 코스 후보 → (선택) 재정렬 → top_course / alternative_courses."""
    inp = payload.get("input_summary") or {}
    weather = payload.get("weather") or {}
    scores_ctx: dict[str, Any] = payload.get("scores") or {}
    recs: list[dict[str, Any]] = list(payload.get("recommendations") or [])
    plan_a = payload.get("plan_a") or {}
    plan_b = payload.get("plan_b") or {}
    plan_c = payload.get("plan_c") or {}
    places_a: list[dict[str, Any]] = list(plan_a.get("places") or [])
    places_b: list[dict[str, Any]] = list(plan_b.get("places") or [])
    places_c: list[dict[str, Any]] = list(plan_c.get("places") or [])

    city = str(inp.get("city") or payload.get("city") or "충남")
    pitch = str(payload.get("today_course_pitch") or "").strip()
    one = _one_liner_from_pitch(pitch)

    temp = weather.get("temp")
    sky = int(weather.get("sky", 1) or 1)
    sky_text = _SKY.get(sky, "맑음")
    w_line = f"{temp}° · {sky_text} · 강수 {float(weather.get('precip_prob', 0) or 0):.0f}%"

    badges: list[dict[str, str]] = [
        {"key": "region", "label": "지역", "value": "충남" if city == "전체" else city},
        {"key": "duration", "label": "일정", "value": _ko_duration(str(inp.get("duration", "half-day")))},
        {"key": "companion", "label": "동행", "value": _ko_companion(str(inp.get("companion", "solo")))},
        {"key": "goal", "label": "목적", "value": _ko_goal(str(inp.get("trip_goal", "healing")))},
        {"key": "transport", "label": "이동", "value": _ko_transport(str(inp.get("transport", "car")))},
        {"key": "weather", "label": "날씨", "value": w_line},
    ]

    if not places_a and recs:
        p0 = recs[0]
        places_a = [
            {
                "name": p0.get("name", ""),
                "place_identity_summary": p0.get("place_identity_summary"),
                "decision_conclusion": p0.get("decision_conclusion"),
                "lead_place_sentence": p0.get("lead_place_sentence"),
                "image": _safe_image_src(p0.get("image")),
                "address": p0.get("address", ""),
                "category": p0.get("category"),
                "coords": p0.get("coords"),
                "why": p0.get("why_recommend_bullets")
                or p0.get("concise_explanation_lines")
                or p0.get("why"),
            }
        ]

    uc = payload.get("user_coords") or {}
    ulat = float(uc.get("lat") or 0)
    ulng = float(uc.get("lng") or 0)
    if ulat == 0 and ulng == 0 and recs:
        c0 = recs[0].get("coords") or {}
        ulat = float(c0.get("lat") or 36.5)
        ulng = float(c0.get("lng") or 127.0)

    intent = {
        "companion": str(inp.get("companion", "solo")),
        "trip_goal": str(inp.get("trip_goal", "healing")),
        "duration": str(inp.get("duration", "half-day")),
        "transport": str(inp.get("transport", "car")),
        "adult_count": str(inp.get("adult_count", "1")),
        "child_count": str(inp.get("child_count", "0")),
        "meal_preference": str(inp.get("meal_preference", "none")),
    }

    cs_meta = (payload.get("meta") or {}).get("course_shape") or {}
    plan_a_reason = cs_meta.get("plan_a_reason")
    roles_from_meta: list[str] = list(cs_meta.get("plan_a_step_roles") or [])
    if not roles_from_meta and places_a:
        roles_from_meta = [
            str(p.get("step_role") or "main_spot") for p in places_a
        ]
    flow_headline, flow_bullets = flow_pitch_reasons(
        str(inp.get("duration", "half-day")),
        roles_from_meta,
        plan_a_reason,
        trip_band_detail=str(cs_meta.get("time_band_detail") or "") or None,
    )

    candidates: list[dict[str, Any]] = []

    main_unit = _build_full_course_unit(
        course_id="course_main",
        title="오늘 가장 추천해요",
        places=places_a,
        recs=recs,
        inp=inp,
        weather=weather,
        scores=scores_ctx,
        user_lat=ulat,
        user_lng=ulng,
        pitch=pitch if pitch else one,
        reasons_title="이 코스 동선을 추천한 이유",
        reasons_override=flow_bullets,
        reason_tags=[
            "보고 · 먹고 · 쉬는 흐름",
            f"일정·{_ko_duration(str(inp.get('duration', 'half-day')))}",
            f"목적·{_ko_goal(intent['trip_goal'])}",
        ],
        course_shape_reason=plan_a_reason,
    )
    if main_unit:
        candidates.append(main_unit)

    if places_b:
        b_indoor = all((p.get("category") or "") == "indoor" for p in places_b)
        b_pitch = (
            "실내·가까운 동선을 섞어 봤어요."
            if b_indoor
            else "다른 느낌으로 가볼 만한 조합이에요."
        )
        alt_b = _build_full_course_unit(
            course_id="course_weather_alt",
            title="다른 코스도 볼까요? · 날씨·동선 대안",
            places=places_b,
            recs=recs,
            inp=inp,
            weather=weather,
            scores=scores_ctx,
            user_lat=ulat,
            user_lng=ulng,
            pitch=b_pitch,
            reasons_title="이 코스는",
            reasons_override=[
                b_pitch,
                "같은 날씨·이동 조건에서 다른 동선을 제안한 코스예요.",
                "실내 비중이 높으면 비·미세먼지에 더 여유 있을 수 있어요." if b_indoor else "첫 코스와 겹치지 않게 장소를 바꿔 봤어요.",
            ],
            reason_tags=["날씨·동선 대안", "실내 위주" if b_indoor else "야외·실내 혼합", "비교용 코스"],
        )
        if alt_b:
            candidates.append(alt_b)

    set_a = _place_name_set(places_a)
    set_b = _place_name_set(places_b)
    set_c = _place_name_set(places_c)
    add_c = bool(
        places_c
        and len(places_c) >= 2
        and set_c
        and set_c != set_a
        and (not places_b or set_c != set_b)
    )
    if add_c:
        c_unit = _build_full_course_unit(
            course_id="course_variant",
            title="또 다른 동선 · 둘러보기 조합",
            places=places_c,
            recs=recs,
            inp=inp,
            weather=weather,
            scores=scores_ctx,
            user_lat=ulat,
            user_lng=ulng,
            pitch="순위·거리를 달리해 묶은 또 다른 당일 코스예요.",
            reasons_title="이 코스는",
            reasons_override=[
                "첫 코스와 다른 후보 풀에서 동선을 잡았어요.",
                "시간이 비슷해도 장소 조합이 달라요.",
                "비교 후 마음에 드는 쪽을 골라 보세요.",
            ],
            reason_tags=["대안 동선", "조합 변경", "비교용 코스"],
        )
        if c_unit:
            candidates.append(c_unit)

    used_names: set[str] = set()
    for c in candidates:
        for nm in c.get("place_names") or []:
            used_names.add(nm)

    idx = 0
    max_singles = min(2, max(0, 5 - len(candidates)))
    for r in recs[1:8]:
        if idx >= max_singles:
            break
        nm = r.get("name")
        if not nm or nm in used_names:
            continue
        used_names.add(str(nm))
        mini = _single_stop_course(
            course_id=f"course_spot_{idx}",
            title=f"짧게 둘러보기 · {nm}",
            one_liner="한 곳만 가볍게 잡은 짧은 코스예요.",
            place_row=r,
            inp=inp,
            weather=weather,
            scores=scores_ctx,
            user_lat=ulat,
            user_lng=ulng,
            reason_tags=["한 정거장", "가벼운 일정", "비교용"],
        )
        if mini:
            candidates.append(mini)
            idx += 1

    ranked, rerank_meta = apply_course_rerank(
        [c for c in candidates if c],
        intent=intent,
        weather=weather,
        scores=scores_ctx,
    )

    top_course = ranked[0] if ranked else {}
    alternative_courses = ranked[1:][:3]

    itinerary = list(payload.get("itinerary") or [])
    meal_ctx_payload = payload.get("meal_context") or {}
    basis = str(meal_ctx_payload.get("basis_line") or "").strip()
    meta_all = payload.get("meta") or {}
    time_banner = str(meta_all.get("time_based_banner") or "").strip()

    if top_course:
        if itinerary:
            top_course["itinerary"] = itinerary
        if time_banner:
            top_course["time_based_banner"] = time_banner
        if basis:
            rcur = list(top_course.get("reasons") or [])
            if not any(basis[:16] in str(x) for x in rcur):
                top_course["reasons"] = [basis] + rcur[:4]

    pp_w = float(weather.get("precip_prob", 0) or 0)
    if pp_w >= 60:
        headline_w = "비 가능성을 고려한 추천 코스"
        one_w = "비 가능성을 고려해 실내·짧은 동선 위주로 골랐어요."
    elif pp_w >= 50:
        headline_w = "강수를 염두에 둔 추천 코스"
        one_w = "강수 확률이 있어 실내·혼합 코스를 우선했어요."
    elif pp_w >= 30:
        headline_w = "오늘의 추천 코스"
        one_w = "가끔 비가 올 수 있어 짧은 동선·실내를 섞었어요."
    else:
        headline_w = "오늘의 추천 코스"
        one_w = one

    if flow_headline and pp_w < 50:
        one_w = flow_headline

    summary: dict[str, Any] = {
        "headline": headline_w,
        "one_liner": one_w,
        "badges": badges,
        "city": "충남" if city == "전체" else city,
        "duration": _ko_duration(str(inp.get("duration", "half-day"))),
        "companion": _ko_companion(str(inp.get("companion", "solo"))),
        "goal": _ko_goal(str(inp.get("trip_goal", "healing"))),
        "weather_label": w_line,
        "pitch": pitch[:800] if pitch else one,
        "schedule_intro": time_banner or None,
    }

    notice: dict[str, Any] = {
        "disclaimer": "일부 정보는 실제와 다를 수 있어요. 운영시간·휴무는 방문 전에 확인해 주세요.",
        "details": [
            "날씨는 당일 단기예보 기준이에요.",
            "장소·혼잡·주차는 현장 상황과 다를 수 있어요.",
            "추천은 규칙·공공 데이터를 바탕으로 한 코스 단위 제안이에요.",
        ],
        "short": [
            "날씨는 당일 단기예보 기준이에요.",
            "코스는 여러 동선 후보 중 하나를 골라 보시면 돼요.",
        ],
    }

    out: dict[str, Any] = {
        "summary": summary,
        "top_course": top_course,
        "alternative_courses": alternative_courses,
        "course_rerank": rerank_meta,
        "notice": notice,
    }
    if not top_course:
        out["top_course"] = None
    return out
