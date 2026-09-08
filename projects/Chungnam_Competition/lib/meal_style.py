# -*- coding: utf-8 -*-
"""
식사 스타일(휴리스틱) → 요리 편향(부가 점수) → 식당명·types·오버라이드 클러스터.

한/일/중/서양을 먼저 단정하지 않고, 식사 스타일을 고른 뒤 요리 편향으로만 가산한다.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

MealStyleKey = Literal[
    "warm_comfort_meal",
    "family_relaxed_meal",
    "light_quick_meal",
    "quiet_rest_meal",
    "photo_brunch_meal",
    "hearty_refuel_meal",
    "cafe_rest",
    "indoor_comfort",
    "none",
]

CUISINES = ("korean", "chinese", "japanese", "western")

_ROOT = Path(__file__).resolve().parent.parent
RESTAURANT_STYLE_OVERRIDES_PATH = _ROOT / "data" / "restaurant_style_overrides.json"

_cache_rs: tuple[float, list[dict[str, Any]]] | None = None

MEAL_STYLE_LABELS: dict[str, str] = {
    "warm_comfort_meal": "따뜻하고 편안한 한 끼",
    "family_relaxed_meal": "가족과 무리 없는 편안한 식사",
    "light_quick_meal": "가볍게·빠르게 한 끼",
    "quiet_rest_meal": "조용히 쉬며 회복하기 좋은 식사",
    "photo_brunch_meal": "분위기·브런치에 어울리는 한 끼",
    "hearty_refuel_meal": "든든하게 에너지 보충",
    "cafe_rest": "카페·디저트로 짧게 쉬기",
    "indoor_comfort": "실내에서 부담 적게 쉬기",
    "none": "",
}

# 식사 스타일별 요리 편향(0~1 스케일로 쓰기 위해 상한만 맞춤; 상대 비중이 핵심)
CUISINE_BIAS_TABLE: dict[str, dict[str, float]] = {
    "warm_comfort_meal": {
        "korean": 0.30,
        "chinese": 0.16,
        "japanese": 0.10,
        "western": 0.06,
    },
    "family_relaxed_meal": {
        "korean": 0.26,
        "western": 0.18,
        "japanese": 0.16,
        "chinese": 0.12,
    },
    "light_quick_meal": {
        "japanese": 0.22,
        "western": 0.20,
        "korean": 0.14,
        "chinese": 0.08,
    },
    "quiet_rest_meal": {
        "western": 0.22,
        "japanese": 0.20,
        "korean": 0.16,
        "chinese": 0.07,
    },
    "photo_brunch_meal": {
        "western": 0.28,
        "japanese": 0.18,
        "korean": 0.10,
        "chinese": 0.06,
    },
    "hearty_refuel_meal": {
        "korean": 0.28,
        "chinese": 0.20,
        "japanese": 0.12,
        "western": 0.10,
    },
    "indoor_comfort": {
        "korean": 0.18,
        "western": 0.16,
        "japanese": 0.14,
        "chinese": 0.08,
    },
}

# 구 스타일 태그(오버라이드·이전 데이터) → 신규 키
_LEGACY_MEAL_TAG_MAP: dict[str, str] = {
    "warm_soup": "warm_comfort_meal",
    "korean_comfort": "family_relaxed_meal",
    "family_meal": "family_relaxed_meal",
    "light_meal": "light_quick_meal",
    "quick_meal": "light_quick_meal",
}

# 장소 힌트(이름·키워드) → 식사 스타일 후보
_STYLE_KEYWORD_BUCKETS: list[tuple[str, frozenset[str]]] = [
    (
        "warm_comfort_meal",
        frozenset(
            "동태 해장 국밥 칼국수 설렁 막국 순대 감자탕 곰탕 우동 라면 된장 부대 찌개 탕 순두부 갈비탕 전골".split()
        ),
    ),
    (
        "family_relaxed_meal",
        frozenset("가족 키즈 유아 아이 패밀리 정식 백반 한정식 전통 놀이방".split()),
    ),
    (
        "light_quick_meal",
        frozenset("김밥 분식 떡볶이 햄버거 버거 포장 테이크아웃 패스트 간식 샌드위치".split()),
    ),
    (
        "quiet_rest_meal",
        frozenset("샐러드 티룸 브런치 카페 베이커리 조용".split()),
    ),
    (
        "photo_brunch_meal",
        frozenset("브런치 파스타 루프탑 뷰 전망 데이트 이탈리안 프렌치".split()),
    ),
    (
        "hearty_refuel_meal",
        frozenset("삼겹 고기 무한 화로 구이 스테이크 한우 갈비 보쌈 족발".split()),
    ),
]

# 요리 클러스터(이름 키워드) — 메뉴명을 단정하지 않고 약한 신호만
_CUISINE_KEYWORDS: dict[str, frozenset[str]] = {
    "korean": frozenset(
        "정식 백반 국밥 해장국 칼국수 설렁탕 순두부 찌개 갈비탕 한우 보쌈 쌈밥 도가니 전골 한식".split()
    ),
    "japanese": frozenset("초밥 우동 돈카츠 라멘 사시미 덮밥 오마카세 일식 돈까스".split()),
    "chinese": frozenset("짜장 짬뽕 마라 탕수육 중화 훠궈 중식 딤섬 양꼬치".split()),
    "western": frozenset(
        "파스타 브럨치 브런치 스테이크 샐러드 리조또 피자 샌드위치 양식 이탈리 프렌치 그릴".split()
    ),
}

_TYPE_CUISINE_HINTS: list[tuple[str, str, float]] = [
    ("korean_restaurant", "korean", 0.55),
    ("japanese_restaurant", "japanese", 0.55),
    ("chinese_restaurant", "chinese", 0.55),
    ("italian_restaurant", "western", 0.45),
    ("french_restaurant", "western", 0.45),
    ("american_restaurant", "western", 0.4),
    ("meal_takeaway", "korean", 0.22),
]

_SOFT_MEAL_COMPAT: dict[str, frozenset[str]] = {
    "warm_comfort_meal": frozenset({"family_relaxed_meal", "hearty_refuel_meal"}),
    "family_relaxed_meal": frozenset({"warm_comfort_meal", "quiet_rest_meal", "light_quick_meal"}),
    "light_quick_meal": frozenset({"quiet_rest_meal", "photo_brunch_meal", "family_relaxed_meal"}),
    "quiet_rest_meal": frozenset({"family_relaxed_meal", "light_quick_meal", "photo_brunch_meal"}),
    "photo_brunch_meal": frozenset({"light_quick_meal", "quiet_rest_meal"}),
    "hearty_refuel_meal": frozenset({"warm_comfort_meal", "family_relaxed_meal"}),
}


def load_restaurant_style_overrides() -> list[dict[str, Any]]:
    global _cache_rs
    if _cache_rs is not None:
        ts, data = _cache_rs
        if time.time() - ts < 300:
            return data
    if not RESTAURANT_STYLE_OVERRIDES_PATH.is_file():
        _cache_rs = (time.time(), [])
        return []
    try:
        with open(RESTAURANT_STYLE_OVERRIDES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = []
    except Exception:
        data = []
    _cache_rs = (time.time(), data)
    return data


def _norm_meal_tag(tag: str) -> str:
    t = str(tag).strip()
    return _LEGACY_MEAL_TAG_MAP.get(t, t)


def infer_place_meal_style_hints(name: str, types: list[str]) -> set[str]:
    """이름·types에서 6가지 식사 스타일 힌트(복수 가능)."""
    out: set[str] = set()
    n = (name or "").lower()
    for style, kws in _STYLE_KEYWORD_BUCKETS:
        for kw in kws:
            if kw in n:
                out.add(style)
                break
    tl = " ".join(str(x).lower() for x in (types or []))
    if "cafe" in tl or "coffee_shop" in tl or "bakery" in tl:
        out.add("quiet_rest_meal")
        out.add("photo_brunch_meal")
    if "korean_restaurant" in tl or "restaurant" in tl:
        out.update({"family_relaxed_meal", "warm_comfort_meal"})
    return out


def infer_cuisine_weights(
    name: str, types: list[str], rs_override: dict[str, Any] | None
) -> dict[str, float]:
    """0~1 근사: 키워드·types·cuisine_cluster 오버라이드로 요리 축 가중."""
    raw: dict[str, float] = {c: 0.0 for c in CUISINES}
    n = (name or "").lower()
    for c, kws in _CUISINE_KEYWORDS.items():
        for kw in kws:
            if kw in n:
                raw[c] += 0.34
                break
    tl = " ".join(str(x).lower() for x in (types or []))
    for ptype, c, bump in _TYPE_CUISINE_HINTS:
        if ptype in tl:
            raw[c] = max(raw[c], bump)
    if not rs_override:
        pass
    else:
        cc = rs_override.get("cuisine_cluster")
        if cc and str(cc).lower() in raw:
            raw[str(cc).lower()] += 0.45
    s = sum(raw.values())
    if s < 1e-6:
        return {c: 0.25 for c in CUISINES}
    return {c: raw[c] / s for c in CUISINES}


def cuisine_bias_vector(meal_style_key: str) -> dict[str, float]:
    """API 노출용: 해당 식사 스타일의 요리 편향 표."""
    row = CUISINE_BIAS_TABLE.get(meal_style_key) or {}
    return {c: round(float(row.get(c, 0.0)), 4) for c in CUISINES}


def compute_cuisine_bonus(meal_style_key: str, cuisine_weights: dict[str, float]) -> float:
    """0~1: 편향표와 장소 요리 힌트의 정렬."""
    bias = CUISINE_BIAS_TABLE.get(meal_style_key)
    if not bias:
        return 0.5
    num = sum(float(bias.get(c, 0.0)) * float(cuisine_weights.get(c, 0.0)) for c in CUISINES)
    mx = max(float(bias.get(c, 0.0)) for c in CUISINES)
    if mx <= 1e-6:
        return 0.5
    return max(0.0, min(1.0, num / mx))


def compute_meal_style_fit(
    primary: str,
    secondary: str | None,
    name: str,
    types: list[str],
    rs_override: dict[str, Any] | None,
) -> float:
    """0~1: 선택된 식사 스타일과 장소 힌트 정합."""
    hints = infer_place_meal_style_hints(name, types)
    if rs_override:
        for t in rs_override.get("meal_tags") or []:
            nt = _norm_meal_tag(str(t))
            if nt in MEAL_STYLE_LABELS and nt not in ("cafe_rest", "none"):
                hints.add(nt)
        mc = rs_override.get("menu_cluster")
        if mc:
            nt = _norm_meal_tag(str(mc))
            if nt in MEAL_STYLE_LABELS and nt not in ("cafe_rest", "none"):
                hints.add(nt)
    if primary == "cafe_rest":
        tl = " ".join(str(x).lower() for x in (types or []))
        if "cafe" in tl or "bakery" in tl or "coffee_shop" in tl:
            return 0.92
        return 0.44

    if primary in hints:
        return 0.94
    if secondary and secondary in hints:
        return 0.82
    soft = _SOFT_MEAL_COMPAT.get(primary, frozenset())
    if hints & soft:
        return 0.72
    tl = " ".join(str(x).lower() for x in (types or []))
    if primary in ("family_relaxed_meal", "warm_comfort_meal", "hearty_refuel_meal") and "korean_restaurant" in tl:
        return 0.56
    if primary == "light_quick_meal" and "meal_takeaway" in tl:
        return 0.62
    if primary == "photo_brunch_meal" and any(x in tl for x in ("restaurant", "cafe", "bakery")):
        return 0.52
    return 0.4


def infer_meal_style_bundle(
    *,
    stage: str,
    spot_meta: dict[str, Any],
    trip_state: dict[str, float],
    hour: int,
    intent: dict[str, str],
    scores: dict[str, Any] | None,
    temp: float,
    precip_prob: float,
) -> dict[str, Any]:
    """식사 단계용 6가지 스타일 + 보조 1개. 카페 단계는 cafe_rest."""
    goal = intent.get("trip_goal", "healing")
    comp = intent.get("companion", "solo")
    dur = intent.get("duration", "half-day")
    cat = (spot_meta.get("category") or "outdoor").lower()
    activity = (spot_meta.get("activity_level") or "moderate").lower()
    avg_stay = float(spot_meta.get("avg_stay_minutes") or 75)
    role_tags = [str(x).lower() for x in (spot_meta.get("role_tags") or [])]
    tags_l = [str(x).lower() for x in (spot_meta.get("tags") or [])]
    photo_fit = float(spot_meta.get("photo_fit", 0.5))
    healing_fit = float(spot_meta.get("healing_fit", 0.55))

    need_meal = float(trip_state.get("need_meal", 0.5))
    need_rest = float(trip_state.get("need_rest", 0.5))
    move_tol = float(trip_state.get("move_tolerance", 0.5))

    kids_stress = any(x in role_tags for x in ("kids", "family")) or comp in ("family", "kids") or goal == "kids"

    fatigue = 0.35
    if activity == "high":
        fatigue += 0.38
    elif activity == "moderate":
        fatigue += 0.2
    if avg_stay >= 100:
        fatigue += 0.14
    elif avg_stay >= 75:
        fatigue += 0.06
    fatigue = max(0.0, min(1.0, fatigue))

    if stage == "cafe_rest":
        return {
            "key": "cafe_rest",
            "label": MEAL_STYLE_LABELS["cafe_rest"],
            "secondary_key": None,
            "secondary_label": None,
            "need_meal": round(need_meal, 3),
            "need_rest": round(need_rest, 3),
            "why": [
                "식사보다 짧게 앉아 쉬는 단계가 지금 흐름에 더 자연스럽습니다.",
                "휴식·힐링 목적을 유지하면서 동선을 크게 바꾸지 않는 선택입니다.",
            ],
        }

    if stage == "indoor_backup":
        return {
            "key": "indoor_comfort",
            "label": MEAL_STYLE_LABELS["indoor_comfort"],
            "secondary_key": None,
            "secondary_label": None,
            "need_meal": round(need_meal, 3),
            "need_rest": round(need_rest, 3),
            "why": [
                "실내 전환 단계는 ‘지금 꼭 한 끼’보다 날씨·동선을 안정화하는 데 가깝습니다.",
                "가벼운 식사·카페·실내 산책형 공간 등 부담 적은 실내 옵션을 넓게 보면 자연스럽습니다.",
            ],
        }

    if stage == "indoor_visit":
        return {
            "key": "none",
            "label": "",
            "secondary_key": None,
            "secondary_label": None,
            "need_meal": round(need_meal, 3),
            "need_rest": round(need_rest, 3),
            "why": [],
        }

    if stage != "meal":
        return {
            "key": "none",
            "label": "",
            "secondary_key": None,
            "secondary_label": None,
            "need_meal": round(need_meal, 3),
            "need_rest": round(need_rest, 3),
            "why": [],
        }

    w: dict[str, float] = {k: 0.0 for k in MEAL_STYLE_LABELS if k not in ("cafe_rest", "none")}

    if temp <= 9 or precip_prob >= 55 or (scores and scores.get("is_raining")):
        w["warm_comfort_meal"] += 1.45
    elif temp <= 14:
        w["warm_comfort_meal"] += 0.55

    if 0.55 <= fatigue <= 0.88:
        w["warm_comfort_meal"] += 0.35
        w["quiet_rest_meal"] += 0.22
    if fatigue >= 0.78:
        w["hearty_refuel_meal"] += 0.95

    if goal == "healing" or healing_fit >= 0.58:
        w["quiet_rest_meal"] += 0.42
        w["warm_comfort_meal"] += 0.22

    if comp in ("family", "kids") or goal == "kids" or kids_stress:
        w["family_relaxed_meal"] += 1.28

    if dur == "2h" or move_tol <= 0.4:
        w["light_quick_meal"] += 1.05

    if goal == "photo" or (comp == "couple" and 10 <= hour <= 15):
        w["photo_brunch_meal"] += 0.72
    if 10 <= hour <= 13 and photo_fit >= 0.55:
        w["photo_brunch_meal"] += 0.38

    if need_meal >= 0.86 and cat == "outdoor" and activity == "high":
        w["hearty_refuel_meal"] += 1.15
    if need_meal >= 0.82 and fatigue >= 0.62:
        w["hearty_refuel_meal"] += 0.55

    if need_rest >= 0.68 and need_meal < 0.75:
        w["quiet_rest_meal"] += 0.35
        w["photo_brunch_meal"] += 0.15

    if cat == "outdoor" and goal in ("healing", "walking"):
        w["family_relaxed_meal"] += 0.35
        w["warm_comfort_meal"] += 0.28

    if 11 <= hour <= 14:
        w["family_relaxed_meal"] += 0.2
        w["light_quick_meal"] += 0.12
    if 17 <= hour <= 21:
        w["hearty_refuel_meal"] += 0.22
        w["warm_comfort_meal"] += 0.18

    best = max(w, key=lambda k: w[k])
    if w[best] < 0.22:
        best = "family_relaxed_meal"

    sorted_keys = sorted(w.keys(), key=lambda k: w[k], reverse=True)
    second = sorted_keys[1] if len(sorted_keys) > 1 else None
    secondary_key: str | None = None
    if second and w[second] >= w[best] - 0.4 and second != best:
        secondary_key = second

    label = MEAL_STYLE_LABELS.get(best, best)
    why_lines: list[str] = []

    if cat == "outdoor" and (activity in ("high", "moderate") or avg_stay >= 75):
        why_lines.append("현재 코스가 야외·활동 위주라 피로 회복이 필요한 상태에 가깝습니다.")
    elif cat == "outdoor":
        why_lines.append("야외·산책형 코스 이후라 자리에 앉아 먹는 식사로 리듬을 나누기 좋습니다.")

    if 11 <= hour <= 14:
        why_lines.append("현재 시간대가 점심 식사 구간에 해당합니다.")
    elif 17 <= hour <= 21:
        why_lines.append("저녁 식사 시간대에 가깝습니다.")

    if comp in ("family", "kids") or goal == "kids":
        why_lines.append("가족 동반 기준으로 무리 없는 식사 흐름이 적합합니다.")

    if best == "warm_comfort_meal":
        why_lines.append("기온·강수 맥락에서 따뜻하고 부담 적은 한 끼가 자연스럽습니다.")
    elif best == "family_relaxed_meal":
        why_lines.append("힐링 목적을 유지하면서 쉬어가기 좋은 식사 유형입니다.")
    elif best == "light_quick_meal":
        why_lines.append("짧은 일정·이동 여유가 작을 때 시간을 덜 쓰는 한 끼가 맞습니다.")
    elif best == "quiet_rest_meal":
        why_lines.append("휴식 무드가 강할 때 자극보다 회복에 가까운 식사 흐름이 어울립니다.")
    elif best == "photo_brunch_meal":
        why_lines.append("사진·분위기 목적에 맞춰 가벼운 브런치·양식류 흐름이 잘 붙습니다.")
    elif best == "hearty_refuel_meal":
        why_lines.append("에너지 보충이 중요한 구간으로 든든한 한 끼 쪽이 적합합니다.")

    why_lines = why_lines[:5]
    if len(why_lines) < 2:
        why_lines.append("동선·동행·날씨를 함께 본 뒤 지금 단계에 맞는 식사 스타일을 골랐습니다.")

    sec_lbl = MEAL_STYLE_LABELS.get(secondary_key, "") if secondary_key else ""

    return {
        "key": best,
        "label": label,
        "secondary_key": secondary_key,
        "secondary_label": sec_lbl or None,
        "need_meal": round(need_meal, 3),
        "need_rest": round(need_rest, 3),
        "why": why_lines[:4],
    }


def explain_restaurant_why(
    meal_style_label: str,
    comp: dict[str, float],
    mobility_line: str,
) -> list[str]:
    """왜 이 식당인가: 거리 + 상위 점수축(요리 편향·스타일·품질 등)."""
    tops = sorted(comp.items(), key=lambda x: x[1], reverse=True)[:4]
    top_keys = {x[0] for x in tops}
    lines: list[str] = [mobility_line]
    if "meal_style_fit" in top_keys:
        lines.append(
            f"식당명·유형·보정 태그 기준으로 「{meal_style_label}」스타일과 잘 맞습니다."
        )
    if "cuisine_bonus" in top_keys:
        lines.append("추천 식사 스타일에 맞춘 요리 편향과 이름 힌트가 서로 잘 맞습니다.")
    if "quality_fit" in top_keys:
        lines.append("주변 후보 중 리뷰 수·평점 조합이 비교적 안정적인 편입니다.")
    if "transition_fit" in top_keys and len(lines) < 4:
        lines.append("직전 관광지 이후 식사 단계로 이어지기 자연스러운 유형입니다.")
    if len(lines) < 2:
        lines.append("거리·스타일·요리 편향·품질·이후 동선을 함께 반영한 순위입니다.")
    return lines[:4]
