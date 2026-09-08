# -*- coding: utf-8 -*-
"""
장소별 4층 내러티브(결정론). 날씨·목적·거리 축만 반복하지 않도록
태그·카테고리·스토리 요약·수동 copy·운영 메모를 우선한다.
"""
from __future__ import annotations

import re
from typing import Any

from lib.intent_hints import _COMPANION_HINTS, _GOAL_TAG_HINTS, _tags_lower


def _tag_blob(dest: dict[str, Any]) -> str:
    tags = dest.get("tags") or []
    return " ".join(str(t) for t in tags).lower()


def _pick_archetype(dest: dict[str, Any]) -> str:
    """healing_walk | photo_spot | festival_event | indoor_culture | history | water_relax | generic"""
    cat = str(dest.get("category") or "outdoor").lower()
    tb = _tag_blob(dest)
    story = str(dest.get("story_summary") or "").lower()
    blob = tb + " " + story

    if any(k in blob for k in ("축제", "행사", "공연", "페스티벌", "체험", "마당", "놀이")):
        return "festival_event"
    if cat == "indoor" or any(k in blob for k in ("박물관", "전시", "미술", "실내")):
        return "indoor_culture"
    if any(k in blob for k in ("사진", "야경", "일출", "노을", "전망", "테라스")):
        return "photo_spot"
    if any(k in blob for k in ("온천", "스파", "힐링", "휴양", "숲", "산책", "둘레길", "자연")):
        return "healing_walk"
    if any(k in blob for k in ("역사", "유적", "유네스코", "문화", "전통")):
        return "history"
    if any(k in blob for k in ("해변", "바다", "물놀이")):
        return "water_relax"
    return "generic"


def _identity_sentence(dest: dict[str, Any], arch: str) -> str:
    name = str(dest.get("name") or "이 장소").strip()
    summ = str(dest.get("story_summary") or "").strip()
    if summ and len(summ) >= 12:
        one = summ.split(".")[0].split("\n")[0].strip()
        if 12 <= len(one) <= 120:
            return one if one.endswith(("요", "다", "음", "임")) else one + "."
    copy = str(dest.get("copy") or "").strip()
    if copy and 8 <= len(copy) <= 100:
        return copy if copy.endswith((".", "!", "?", "요")) else copy + "."

    arche_lines = {
        "healing_walk": f"{name}은(는) 숲·산책·휴식에 초점이 맞는 야외형 코스에 가깝습니다.",
        "photo_spot": f"{name}은(는) 사진·전망·분위기 포인트가 분명한 장소입니다.",
        "festival_event": f"{name}은(는) 체험·공연·행사 동선이 어울리는 장소로 보입니다.",
        "indoor_culture": f"{name}은(는) 실내 전시·문화 보기에 맞는 유형입니다.",
        "history": f"{name}은(는) 역사·유적 탐방에 어울리는 장소입니다.",
        "water_relax": f"{name}은(는) 물가·휴양 무드가 강한 편입니다.",
        "generic": f"{name}은(는) 태그와 거리를 기준으로 오늘 동선에 맞춰 골랐습니다.",
    }
    return arche_lines.get(arch, arche_lines["generic"])


def _why_today_lines(
    dest: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
    arch: str,
) -> str:
    dur = intent.get("duration", "half-day")
    goal = intent.get("trip_goal", "healing")
    comp = intent.get("companion", "solo")
    pp = float(weather.get("precip_prob", 0))
    dust = int(weather.get("dust", 1))
    sky = int(weather.get("sky", 1))
    cat = str(dest.get("category") or "outdoor").lower()

    parts: list[str] = []

    if dur == "2h":
        parts.append("짧은 일정이라 핵심만 보고 오기 좋은 타입이에요.")
    elif dur == "full-day":
        parts.append("종일 일정이면 여유 있게 동선을 나누기 좋아요.")
    else:
        parts.append("반나절이면 쉬었다 가기·한 번 더 이어가기 무난한 밸런스예요.")

    if scores.get("is_raining") or pp >= 70:
        if cat == "indoor":
            parts.append("비·강수 가능성이 있어도 실내 비중이라 오늘은 부담이 덜해요.")
        elif arch in ("festival_event", "indoor_culture"):
            parts.append("오늘은 밖이 불안정해도 실내·행사형 프로그램이 있으면 체감이 편해질 수 있어요.")
        else:
            parts.append("비·강수 가능성이 있어 야외는 짧게, 실내 대안을 같이 염두에 두면 좋아요.")
    elif pp >= 45 and cat == "outdoor":
        parts.append("흐리거나 살짝 올 수 있는 날씨라 야외는 짧게 잡고 쉬는 흐름이 편해요.")
    elif sky == 1 and cat == "outdoor" and arch in ("photo_spot", "healing_walk"):
        parts.append("오늘은 하늘이 비교적 맑은 편이라 밖에서 즐기기 무난해요.")

    if dust >= 3 and cat == "outdoor":
        parts.append("미세먼지가 나쁜 편이라 밖은 짧게, 마스크·실내 휴식을 섞으면 좋아요.")

    if goal == "kids" or comp in ("family",):
        if arch == "festival_event":
            parts.append("아이 동반일 때는 체험·휴식 포인트가 같이 있으면 지루함이 덜해요.")
        elif arch == "healing_walk":
            parts.append("가족 동반이면 무리한 거리보다 천천히 걷는 코스가 부담이 적어요.")

    try:
        ch_n = int(str(intent.get("child_count") or "0").strip() or "0")
    except ValueError:
        ch_n = 0
    if ch_n >= 2:
        parts.append("어린이가 둘 이상이면 이동 거리를 짧게 끊고 쉬는 흐름이 편해요.")

    if goal == "photo" and arch == "photo_spot":
        parts.append("사진 목적이면 조명·시간대 변화만 챙기면 만족도가 잘 나오는 편이에요.")

    return " ".join(parts[:2]).strip()


def _expectation_bullets(dest: dict[str, Any], arch: str, goal: str) -> list[str]:
    tags = _tags_lower(dest)
    out: list[str] = []

    if arch == "festival_event":
        out.append("볼거리·체험이 섞여 있으면 아이·가족도 몰입하기 좋아요.")
    elif arch == "photo_spot":
        out.append("사진 포인트가 뚜렷하면 짧게 다녀와도 기록이 남기 좋아요.")
    elif arch == "healing_walk":
        out.append("숲길·휴양 분위기를 느끼며 속도를 늦추기 좋아요.")
    elif arch == "indoor_culture":
        out.append("앉아서 보고 듣는 시간이 길어질 수 있어요. 호흡 고르며 즐기기 좋아요.")
    elif arch == "history":
        out.append("해설·유물 중심이라 천천히 돌아보는 만족이 큰 편이에요.")
    else:
        out.append("태그에 맞는 분위기를 현장에서 확인해 보기 좋아요.")

    if goal == "walking" and any("걷" in t or "산책" in t for t in tags):
        out.append("걷기 목적이면 동선 길이만 미리 정해두면 체력 부담이 줄어요.")

    return out[:2]


def _departure_checks(dest: dict[str, Any], weather: dict[str, Any], scores: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    oh = dest.get("opening_hours_note")
    pk = dest.get("parking_note")
    if oh:
        lines.append(str(oh) + " 공식 안내를 한 번 더 확인해 주세요.")
    if pk:
        lines.append(str(pk))
    pp = float(weather.get("precip_prob", 0))
    if pp >= 40:
        lines.append("강수 가능성이 있으면 우산·대체 실내 동선을 챙기면 좋아요.")
    if int(weather.get("dust", 1)) >= 3:
        lines.append("미세먼지가 나쁠 땐 실내·마스크를 고려해 주세요.")
    if dest.get("golden_hour_bonus") and scores.get("is_golden_hour"):
        lines.append("노을·사진 목적이면 일몰 시각 전후를 한 번 확인해 주세요.")
    if not lines:
        lines.append("운영·휴무는 공식 채널에서 출발 전에 한 번만 확인해 주세요.")
    return lines[:3]


def _duration_conclusion(dur: str, rank_index: int, intent: dict[str, str]) -> str:
    if rank_index > 0:
        return "대안으로 괜찮아요"
    try:
        ch = int(str(intent.get("child_count") or "0").strip() or "0")
    except ValueError:
        ch = 0
    ch = max(0, min(8, ch))
    if dur == "2h":
        return "아이 동반·짧게 다녀오기 좋아요" if ch > 0 else "짧게 다녀오기 좋아요"
    if dur == "full-day":
        if ch > 0:
            return "하루 일정·가족 동선으로 괜찮아요"
        return "하루 일정으로 여유 있게 즐기기 좋아요"
    if ch > 0:
        return "반나절·가족 나들이로 무난해요"
    return "오늘 가기 좋아요"


def _why_bullets_from_narrative(
    dest: dict[str, Any],
    intent: dict[str, str],
    contrib: dict[str, float],
    identity: str,
    why_today: str,
) -> list[str]:
    """점수 축 1개만 보조로 섞고 나머지는 장소·의도 기반."""
    tags = dest.get("tags") or []
    tag_preview = ", ".join(str(t) for t in tags[:3]) if tags else ""
    goal = intent.get("trip_goal", "healing")
    goal_hints = _GOAL_TAG_HINTS.get(goal, ())
    hits = [h for h in goal_hints if any(h.lower() in str(t).lower() for t in tags)]

    bullets: list[str] = []
    if tag_preview:
        bullets.append(
            " ".join(f"#{t.strip()}" for t in tag_preview.split(",") if t.strip())
            + " 키워드와 장소 성격이 맞닿아요."
        )
    if hits:
        bullets.append(f"「{goal}」목표와 {', '.join(hits[:2])} 뉘앙스가 맞습니다.")

    # 가장 기여 큰 축 하나만 짧게
    tops = sorted(contrib.items(), key=lambda x: x[1], reverse=True)
    for key, pt in tops:
        if pt < 0.03:
            continue
        if key == "distance_fit":
            bullets.append("오늘 동선에서 이동 부담을 크게 늘리지 않는 편이에요.")
        elif key == "weather_fit":
            bullets.append("오늘 날씨 맥락에서 실내·야외 균형을 같이 봤어요.")
        elif key == "goal_fit":
            bullets.append("여행 목표와 장소 태그 정합을 우선 봤어요.")
        break

    if len(bullets) < 2:
        bullets.append(identity[:90] + ("…" if len(identity) > 90 else ""))
    if len(bullets) < 3 and why_today:
        bullets.append(why_today[:100] + ("…" if len(why_today) > 100 else ""))

    # 중복·너무 비슷한 줄 제거
    seen: set[str] = set()
    uniq: list[str] = []
    for b in bullets:
        k = re.sub(r"\s+", "", b)[:40]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(b)
    return uniq[:3]


def build_place_narrative(
    dest: dict[str, Any],
    weather: dict[str, Any],
    scores: dict[str, Any],
    intent: dict[str, str],
    *,
    rank_index: int,
    contributions: dict[str, float],
) -> dict[str, Any]:
    arch = _pick_archetype(dest)
    identity = _identity_sentence(dest, arch)
    why_today = _why_today_lines(dest, weather, scores, intent, arch)
    expectation = _expectation_bullets(dest, arch, intent.get("trip_goal", "healing"))
    departure = _departure_checks(dest, weather, scores)
    dur = intent.get("duration", "half-day")
    tagline = _duration_conclusion(dur, rank_index, intent)

    line1 = identity
    line2 = why_today
    bullets = _why_bullets_from_narrative(dest, intent, contributions, identity, why_today)

    return {
        "narrative_archetype": arch,
        "place_identity": line1,
        "why_today": line2,
        "expectation_bullets": expectation,
        "departure_checks": departure,
        "summary_two_lines": [line1, line2],
        "duration_conclusion": tagline,
        "why_recommend_bullets_narrative": bullets,
    }
