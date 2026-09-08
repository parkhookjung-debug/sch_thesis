# -*- coding: utf-8 -*-
"""
리뷰 원문은 노출하지 않고, 키워드·평점 패턴으로 구조화된 보조 특성만 만든다.
코스 이어가기/단계 교체 후보 재랭킹·설명 보강에 사용.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

# (feature_key, weight_multiplier_for_bonus) — 보너스 상한은 호출부에서 clamp
_KEYWORD_GROUPS: list[tuple[str, frozenset[str]]] = [
    ("family_friendly", frozenset({"아이", "유아", "아기", "가족", "유모차", "키즈", "어린이"})),
    ("kids_friendly", frozenset({"키즈", "아이", "유아", "놀이", "어린이"})),
    ("photo_friendly", frozenset({"사진", "인생샷", "포토", "뷰", "전망", "예쁘", "풍경"})),
    ("quiet", frozenset({"조용", "한적", "차분", "여유"})),
    ("crowded", frozenset({"붐빔", "웨이팅", "대기", "줄서", "혼잡"})),
    ("quick_meal", frozenset({"빠르", "회전", "점심", "간단", "가볍게", "빨리"})),
    ("long_stay_ok", frozenset({"오래", "여유", "느긋", "오랫동안", "책읽"})),
    ("short_visit_ok", frozenset({"잠깐", "들르", "가볍게", "한바퀴", "짧게"})),
    ("rainy_day_ok", frozenset({"비오", "우천", "실내", "덮여"})),
    ("parking_easy", frozenset({"주차", "주차장", "발렛"})),
    ("view_good", frozenset({"뷰", "전망", "노을", "창가", "루프탑"})),
    ("dessert_good", frozenset({"디저트", "케이크", "빵", "베이커리"})),
]


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def extract_review_features(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """리뷰 객체 리스트(text, rating)에서 0~1 스케일 특성 + 체류 힌트."""
    texts: list[str] = []
    for r in reviews[:14]:
        t = r.get("text")
        if isinstance(t, str) and t.strip():
            texts.append(t.strip())
    combined = _norm_text(" ".join(texts))
    out: dict[str, Any] = {}
    if not combined:
        return {
            "stay_duration_hint": "medium",
            "review_sample_count": 0,
        }

    lower = combined.lower()
    for key, kws in _KEYWORD_GROUPS:
        hit = sum(1 for kw in kws if kw in combined or kw in lower)
        out[key] = round(min(1.0, 0.25 + 0.18 * hit), 3)

    if out.get("long_stay_ok", 0) > out.get("short_visit_ok", 0) + 0.15:
        stay = "long"
    elif out.get("short_visit_ok", 0) > out.get("long_stay_ok", 0) + 0.15:
        stay = "short"
    else:
        stay = "medium"
    out["stay_duration_hint"] = stay
    out["review_sample_count"] = len(texts)
    return out


def review_rank_bonus(
    feats: dict[str, Any],
    intent: dict[str, str],
    *,
    meal_bias: float = 0.0,
    cafe_bias: float = 0.0,
    family_bias: float = 0.0,
    scenic_bias: float = 0.0,
    indoor_bias: float = 0.0,
    hour: int = 12,
) -> float:
    """총점에 더할 소폭 보너스(전체 순위 뒤집지 않음)."""
    b = 0.0
    comp = intent.get("companion", "solo")
    goal = intent.get("trip_goal", "healing")
    if comp in ("family",) or family_bias > 0.2:
        b += 0.035 * float(feats.get("family_friendly") or 0.0)
        b += 0.02 * float(feats.get("kids_friendly") or 0.0)
    if goal == "photo" or scenic_bias > 0.2:
        b += 0.04 * float(feats.get("photo_friendly") or 0.0)
        b += 0.025 * float(feats.get("view_good") or 0.0)
    if indoor_bias > 0.2:
        b += 0.03 * float(feats.get("rainy_day_ok") or 0.0)
    if meal_bias > 0.2 and 11 <= hour <= 14:
        b += 0.035 * float(feats.get("quick_meal") or 0.0)
    if cafe_bias > 0.2:
        b += 0.025 * float(feats.get("dessert_good") or 0.0)
    if float(feats.get("crowded") or 0.0) > 0.55:
        b -= 0.03
    return max(-0.05, min(0.12, b))


def explain_review_signals(feats: dict[str, Any], intent: dict[str, str]) -> list[str]:
    """사용자에게 보여 줄 한 줄 요약(원문 인용 없음)."""
    lines: list[str] = []
    if int(feats.get("review_sample_count") or 0) <= 0:
        return lines
    comp = intent.get("companion", "solo")
    if comp == "family" and float(feats.get("family_friendly") or 0) >= 0.45:
        lines.append("가족 동행 후기에서 동선·분위기가 무난하다는 반응이 있었어요.")
    if float(feats.get("quick_meal") or 0) >= 0.5:
        lines.append("짧게 들르기 좋다는 후기가 있어 일정이 타이트할 때 무난해요.")
    if float(feats.get("photo_friendly") or 0) >= 0.5 or float(feats.get("view_good") or 0) >= 0.5:
        lines.append("사진·전망 만족도가 괜찮다는 평이 있었어요.")
    if float(feats.get("quiet") or 0) >= 0.5:
        lines.append("조용히 쉬기 좋다는 언급이 있었어요.")
    return lines[:3]


def rerank_with_review_text_signals(
    ranked: list[dict[str, Any]],
    intent: dict[str, str],
    ref_lat: float,
    ref_lng: float,
    *,
    hour: int,
    meal_bias: float,
    cafe_bias: float,
    family_bias: float,
    scenic_bias: float,
    indoor_bias: float,
    max_fetch: int = 3,
) -> tuple[list[dict[str, Any]], bool]:
    """
    상위 후보만 리뷰를 불러 특성을 붙이고 가벼운 재정렬.
    반환: (정렬된 리스트, 실제 fetch 시도 여부)
    """
    from lib.places import fetch_place_reviews

    if not ranked:
        return ranked, False
    tried = False
    for p in ranked[:max_fetch]:
        name = str(p.get("name") or "").strip()
        if not name:
            continue
        lat = float(p.get("lat") or ref_lat)
        lng = float(p.get("lng") or ref_lng)
        addr = str(p.get("address") or "")
        tried = True
        raw = fetch_place_reviews(name, lat, lng, addr)
        revs = raw.get("reviews") if isinstance(raw, dict) else None
        if not isinstance(revs, list):
            revs = []
        feats = extract_review_features(revs)
        p["review_features"] = {k: v for k, v in feats.items() if k != "review_sample_count"}
        p["review_features"]["review_sample_count"] = feats.get("review_sample_count", 0)
        bonus = review_rank_bonus(
            feats,
            intent,
            meal_bias=meal_bias,
            cafe_bias=cafe_bias,
            family_bias=family_bias,
            scenic_bias=scenic_bias,
            indoor_bias=indoor_bias,
            hour=hour,
        )
        base = float(p.get("next_course_score") or 0.0)
        p["next_course_score"] = round(min(1.0, max(0.0, base + bonus)), 4)
        p["score_100"] = round(float(p["next_course_score"]) * 100.0, 1)
        ex = explain_review_signals(feats, intent)
        if ex:
            p["review_signal_lines"] = ex
    ranked.sort(key=lambda x: x.get("next_course_score", 0), reverse=True)
    return ranked, tried


def _enrich_one_recommendation_row(
    row: dict[str, Any],
    intent: dict[str, str],
    *,
    hour: int,
    ref_lat: float,
    ref_lng: float,
    meal_bias: float,
    cafe_bias: float,
    family_bias: float,
    scenic_bias: float,
    indoor_bias: float,
) -> dict[str, Any] | None:
    """Google 리뷰 메타 1건 — 메인 스레드에서 row에 merge할 패치."""
    from lib.places import fetch_place_reviews

    name = str(row.get("name") or "").strip()
    if not name:
        return None
    lat = float((row.get("coords") or {}).get("lat") or ref_lat)
    lng = float((row.get("coords") or {}).get("lng") or ref_lng)
    addr = str(row.get("address") or "")
    raw = fetch_place_reviews(name, lat, lng, addr)
    revs = raw.get("reviews") if isinstance(raw, dict) else None
    if not isinstance(revs, list):
        revs = []
    feats = extract_review_features(revs)
    bonus = review_rank_bonus(
        feats,
        intent,
        meal_bias=meal_bias,
        cafe_bias=cafe_bias,
        family_bias=family_bias,
        scenic_bias=scenic_bias,
        indoor_bias=indoor_bias,
        hour=int(hour) % 24,
    )
    bump = min(0.045, max(0.0, bonus * 0.38))
    new_score = round(
        min(1.0, max(0.0, float(row.get("score", 0) or 0) + bump)),
        4,
    )
    patch: dict[str, Any] = {"review_features": dict(feats), "score": new_score}
    if isinstance(raw, dict):
        if raw.get("rating"):
            patch["rating"] = raw.get("rating")
        if raw.get("review_count"):
            patch["review_count"] = raw.get("review_count")
        photo_url = str(raw.get("photo_url") or "").strip()
        if photo_url and not str(row.get("image") or "").strip():
            patch["image"] = photo_url
    ex = explain_review_signals(feats, intent)
    if ex:
        exp = dict(row.get("recommendation_explain") or {})
        lines = list(exp.get("lines") or [])
        for line in ex:
            if line not in lines:
                lines.append(line)
        exp["lines"] = lines[:5]
        patch["recommendation_explain"] = exp
    return patch


def enrich_main_recommendations_shortlist(
    rows: list[dict[str, Any]],
    intent: dict[str, str],
    *,
    hour: int,
    ref_lat: float,
    ref_lng: float,
    precip_prob: float = 0.0,
    max_fetch: int = 3,
) -> None:
    """
    메인 관광지 랭킹: 상위 몇 곳만 Places 리뷰를 불러 점수·설명을 소폭 보정한다.
    전체 후보에 리뷰를 붙이지 않는다(비용·지연).
    동시에 여러 곳을 조회해 응답 지연을 줄인다.
    """
    from lib.config import settings

    if not rows or not settings.google_places_key:
        return

    pp = float(precip_prob or 0.0)
    goal = str(intent.get("trip_goal", "healing") or "healing")
    comp = str(intent.get("companion", "solo") or "solo")
    scenic_bias = 0.35 if goal == "photo" else 0.0
    family_bias = 0.35 if comp == "family" else 0.0
    indoor_bias = 0.42 if goal == "indoor" or pp >= 50 else 0.0
    meal_bias = 0.5 if 11 <= int(hour) % 24 <= 14 else 0.15
    cafe_bias = 0.45 if int(hour) % 24 >= 15 or int(hour) % 24 < 11 else 0.2

    n = min(max_fetch, len(rows))
    indices = [i for i in range(n) if str(rows[i].get("name") or "").strip()]
    if not indices:
        return

    workers = min(5, len(indices))

    def _task(i: int) -> tuple[int, dict[str, Any] | None]:
        patch = _enrich_one_recommendation_row(
            rows[i],
            intent,
            hour=hour,
            ref_lat=ref_lat,
            ref_lng=ref_lng,
            meal_bias=meal_bias,
            cafe_bias=cafe_bias,
            family_bias=family_bias,
            scenic_bias=scenic_bias,
            indoor_bias=indoor_bias,
        )
        return i, patch

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_task, i) for i in indices]
        for fut in as_completed(futs):
            i, patch = fut.result()
            if patch:
                rows[i].update(patch)


def _step_needs_google_meta(step: dict[str, Any]) -> bool:
    img = str(step.get("image") or "")
    if not img.strip() or "/hero-course-placeholder.svg" in img:
        return True
    try:
        r = float(step.get("rating") or 0)
    except (TypeError, ValueError):
        r = 0.0
    return r <= 0


def enrich_consumer_course_steps_google_meta(
    payload: dict[str, Any],
    intent: dict[str, str],
    *,
    hour: int,
    ref_lat: float,
    ref_lng: float,
    max_fetch: int = 6,
) -> None:
    """
    소비자 코스 스텝에 평점·리뷰 수·(플레이스홀더일 때) 사진을 붙인다.
    메인 랭킹 상위 N건만 보강하는 것과 별개로, 동선에 실제 들어간 장소 이름 기준으로 채운다.
    """
    from lib.config import settings
    from lib.course_view import _safe_image_src
    from lib.places import fetch_place_reviews

    if not settings.google_places_key:
        return
    top = payload.get("top_course")
    if not isinstance(top, dict):
        return
    steps_raw = top.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        return
    steps: list[dict[str, Any]] = [dict(s) if isinstance(s, dict) else {} for s in steps_raw]

    need_idx = [i for i, s in enumerate(steps) if _step_needs_google_meta(s)][: max(0, int(max_fetch))]
    if not need_idx:
        return

    _ = intent  # 향후 의도별 필드마스크 분기용 예약
    _ = hour

    def _one(i: int) -> tuple[int, dict[str, Any]]:
        s = steps[i]
        name = str(s.get("name") or "").strip()
        if not name:
            return i, {}
        la, ln = float(ref_lat), float(ref_lng)
        try:
            if s.get("lat") is not None:
                la = float(s["lat"])
            if s.get("lng") is not None:
                ln = float(s["lng"])
        except (TypeError, ValueError):
            pass
        addr = str(s.get("address") or "")
        raw = fetch_place_reviews(name, la, ln, addr)
        patch: dict[str, Any] = {}
        if not isinstance(raw, dict):
            return i, patch
        if raw.get("rating"):
            try:
                patch["rating"] = round(float(raw["rating"]), 2)
            except (TypeError, ValueError):
                pass
        if raw.get("review_count"):
            try:
                patch["review_count"] = int(raw["review_count"])
            except (TypeError, ValueError):
                pass
        pu = str(raw.get("photo_url") or "").strip()
        cur = str(s.get("image") or "")
        if pu and (not cur.strip() or "/hero-course-placeholder.svg" in cur):
            patch["image"] = _safe_image_src(pu)
        return i, patch

    workers = min(5, len(need_idx))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_one, i) for i in need_idx]
        for fut in as_completed(futs):
            i, patch = fut.result()
            if patch:
                steps[i].update(patch)

    top["steps"] = steps
    hero = str(top.get("hero_image") or "")
    if not hero.strip() or "/hero-course-placeholder.svg" in hero:
        for s in steps:
            im = str(s.get("image") or "")
            if im and "/hero-course-placeholder.svg" not in im:
                top["hero_image"] = im
                break
