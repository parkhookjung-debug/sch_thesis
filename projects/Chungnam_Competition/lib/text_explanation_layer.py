# -*- coding: utf-8 -*-
"""
규칙 엔진 위에 얹는 텍스트 설명 레이어(비-LLM 우선).

- place_identity_summary: 짧은 유형 한 줄
- expectation_points: 1~3 기대 포인트
- enriched_tags: 키워드/태그에서 추출한 시맨틱 태그
"""
from __future__ import annotations

import re
from typing import Any

# ── 시맨틱 태그(관광) ──────────────────────────────────────────
TOURIST_TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "family_friendly": ("가족", "가족여행", "패밀리", "부모", "효도"),
    "kids_friendly": ("어린이", "키즈", "아이", "유아", "놀이", "놀이터", "가족"),
    "healing": ("힐링", "휴식", "숲", "산책", "둘레길", "휴양", "온천", "여유"),
    "scenic": ("전망", "조망", "일출", "일몰", "노을", "경치", "풍경", "드라이브"),
    "photo_friendly": ("사진", "인생샷", "포토", "핫플", "야경", "스냅"),
    "interactive": ("체험", "만들기", "참여", "공방", "체험관", "농촌체험"),
    "quiet": ("고즈넉", "한적", "조용", "산책", "둘레길", "서정"),
    "indoor_comfort": ("실내", "박물관", "전시", "미술관", "체험관"),
    "festival_event": ("축제", "행사", "공연", "페스티벌", "마당", "이벤트"),
}

# 음식·카페(다음 코스·Places 후보용)
FOOD_TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "family_meal": ("가족", "가족모임", "다찌", "상", "뷔페", "한정식"),
    "kids_friendly": ("키즈", "어린이", "유아의자", "아이", "퓨전"),
    "quick_meal": ("분식", "김밥", "빠른", "포장", "테이크"),
    "relaxed_meal": ("브런치", "룸", "카페", "디저트", "와인"),
    "quiet_cafe": ("조용", "북", "빈티지", "힐링", "휴식"),
    "scenic_cafe": ("뷰", "전망", "옥상", "강", "해변", "야외"),
    "warm_comfort_meal": ("국밥", "찌개", "따뜻", "해장", "죽", "해물"),
    "dessert_focus": ("디저트", "빵", "케이크", "베이커", "빙수"),
}

_ARCH_IDENTITY: dict[str, str] = {
    "healing_walk": "숲길·자연 휴식에 가까운 산책·힐링형 방문지예요.",
    "photo_spot": "사진·전망·분위기 포인트가 비교적 뚜렷한 장소예요.",
    "festival_event": "체험·공연·이벤트가 어울릴 수 있는 축제·행사형 분위기예요.",
    "indoor_culture": "실내 전시·문화를 둘러보기에 맞는 유형이에요.",
    "history": "역사·유적·전통 풍경을 느끼기 좋은 곳이에요.",
    "water_relax": "물가·휴양·여유로운 분위기가 강한 편이에요.",
    "generic": "오늘 동선·태그·거리를 기준으로 고른 일반 방문지예요.",
}


def _combined_corpus_lower(dest: dict[str, Any]) -> str:
    parts: list[str] = []
    for k in (
        "name",
        "copy",
        "story_summary",
        "emotional_copy",
        "overview",
        "narrative_enrichment_line",
    ):
        v = dest.get(k)
        if v:
            parts.append(str(v))
    tags = dest.get("tags") or []
    parts.append(" ".join(str(t) for t in tags))
    cat = dest.get("category")
    if cat:
        parts.append(str(cat))
    return " ".join(parts).lower()


def _first_sentence_corpus(text: str, max_len: int = 100) -> str | None:
    t0 = str(text).strip()
    if len(t0) < 12:
        return None
    t = t0
    for sep in (".\n", "\n", ".", "。"):
        if sep in t:
            t = t.split(sep, 1)[0].strip()
            break
    if len(t) < 12:
        t = t0
        if len(t) < 12:
            return None
    if len(t) > max_len:
        return t[: max_len - 1].rstrip() + "…"
    if t.startswith("#") or t.startswith("http"):
        return None
    if not t.endswith((".", "!", "?", "…")):
        t += "."
    return t


def build_place_identity_summary(
    dest: dict[str, Any], narrative_archetype: str
) -> str:
    """짧은 유형 한 문장(휴리스틱)."""
    for key in ("story_summary", "emotional_copy", "copy"):
        raw = dest.get(key)
        if not raw or len(str(raw).strip()) < 15:
            continue
        s = _first_sentence_corpus(str(raw), 96)
        if s:
            return s
    return _ARCH_IDENTITY.get(
        str(narrative_archetype or "generic"), _ARCH_IDENTITY["generic"]
    )


def _add_expectation_from_intent(
    dest: dict[str, Any], intent: dict[str, str], out: list[str]
) -> None:
    comp = (intent.get("companion") or "solo").lower()
    g = (intent.get("trip_goal") or "healing").lower()
    try:
        ch = int(str(intent.get("child_count") or "0").strip() or "0")
    except ValueError:
        ch = 0
    b = _combined_corpus_lower(dest)
    if ch > 0 or g == "kids" or "가족" in b or "어린이" in b or "체험" in b:
        out.append("어린이·가족과 함께하기에 무리가 적은 포인트를 염두에 뒀어요.")
    if g == "photo" or "사진" in b:
        out.append("사진·전망 포인트를 찾기에 무난한 편이에요.")
    if g in ("healing", "walking") and ("산책" in b or "숲" in b or "둘레" in b):
        out.append("천천히 걸으며 쉬어가기 좋은 분위기예요.")


def build_expectation_points(
    dest: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
    base_bullets: list[str],
) -> list[str]:
    """1~3개 기대 문장(결정론, 메타 희소 시 보수적)."""
    out: list[str] = [x for x in base_bullets if str(x).strip()][:2]
    _add_expectation_from_intent(dest, intent, out)
    pp = float(weather.get("precip_prob", 0))
    if (scores.get("is_raining") or pp >= 60) and str(
        dest.get("category") or ""
    ).lower() == "indoor":
        out.append("강수 가능성이 있어 실내 위주로 쉬기에 부담이 덜한 편이에요.")
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        k = re.sub(r"\s+", "", x)[:32]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(x)
    return uniq[:3] if uniq else ["현장에서 분위기를 확인하며 둘러보기 좋아요."]


def enrich_tourist_tags(dest: dict[str, Any]) -> list[str]:
    blob = _combined_corpus_lower(dest)
    hit: list[str] = []
    for tag, kws in TOURIST_TAG_KEYWORDS.items():
        if any(kw.lower() in blob for kw in kws):
            hit.append(tag)
    if str(dest.get("category") or "").lower() == "indoor" and "indoor_comfort" not in hit:
        hit.append("indoor_comfort")
    return list(dict.fromkeys(hit))[:10]


def enrich_food_tags(place: dict[str, Any]) -> list[str]:
    """Google Places/식당 후보 dict: types·name·주소 키워드 기반."""
    name = str(place.get("name") or "").lower()
    types_ = " ".join(str(t).lower() for t in (place.get("types") or []))
    addr = str(place.get("address") or "").lower()
    blob = f"{name} {types_} {addr}"
    out: list[str] = []
    for tag, kws in FOOD_TAG_KEYWORDS.items():
        if any(kw in blob for kw in kws):
            out.append(tag)
    if "cafe" in types_ or "cafe" in name or "카페" in name:
        if "quiet_cafe" not in out and "dessert_focus" not in out:
            out.append("quiet_cafe")
    if "restaurant" in types_ and "relaxed_meal" not in out and "family_meal" not in out:
        out.append("relaxed_meal")
    return list(dict.fromkeys(out))[:8]


def build_explanation_extras(
    dest: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
    narr: dict[str, Any],
) -> dict[str, Any]:
    """recommend_ui에서 place_narrative 결과 narr와 합쳐 쓴다."""
    arch = str(narr.get("narrative_archetype") or "generic")
    pid = build_place_identity_summary(dest, arch)
    exp = build_expectation_points(
        dest, weather, scores, intent, list(narr.get("expectation_bullets") or [])
    )
    tags = enrich_tourist_tags(dest)
    return {
        "place_identity_summary": pid,
        "expectation_points": exp,
        "enriched_tags": tags,
    }
