# -*- coding: utf-8 -*-
"""
스토리텔링 레코드 ↔ destinations 수동 메타 매칭(경량).
랭킹 신호 아님. 설명·내러티브 보강만.
"""
from __future__ import annotations

import re
from typing import Any

from lib.distance import haversine


def _norm_name(s: str) -> str:
    s = str(s or "").lower().strip()
    s = re.sub(r"\s+", "", s)
    return s


def _contains(a: str, b: str) -> bool:
    a, b = _norm_name(a), _norm_name(b)
    if not a or not b:
        return False
    return a in b or b in a


def match_storytelling_for_destination(
    dest: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """최고 매칭 1건 또는 None. confidence 0~1."""
    if not records:
        return None

    dname = str(dest.get("name") or "")
    dcity = str(dest.get("city") or "").strip()
    dlat = dest.get("coords") or {}
    try:
        plat = float(dlat.get("lat")) if dlat.get("lat") is not None else None
        plng = float(dlat.get("lng")) if dlat.get("lng") is not None else None
    except (TypeError, ValueError):
        plat = plng = None

    best: tuple[float, dict[str, Any]] | None = None

    for rec in records:
        pname = str(rec.get("place_name") or "")
        title = str(rec.get("title") or "")
        rcity = str(rec.get("city") or "").strip()

        conf = 0.0
        if dname and pname and _norm_name(dname) == _norm_name(pname):
            conf = 1.0
        elif dname and pname and _contains(dname, pname):
            conf = 0.88
        elif dname and title and _contains(dname, title):
            conf = 0.78
        elif pname and _contains(dname, pname):
            conf = 0.72
        elif title and _contains(dname, title):
            conf = 0.65

        if conf > 0 and dcity and rcity and (dcity in rcity or rcity in dcity):
            conf = min(1.0, conf + 0.06)
        elif conf > 0 and dcity and rcity and dcity != rcity:
            conf *= 0.85

        if plat is not None and plng is not None:
            rlat, rlng = rec.get("lat"), rec.get("lng")
            if rlat is not None and rlng is not None:
                try:
                    km = haversine(plat, plng, float(rlat), float(rlng))
                    if km <= 1.5:
                        conf = min(1.0, conf + 0.12)
                    elif km <= 4.0:
                        conf = min(1.0, conf + 0.05)
                except (TypeError, ValueError):
                    pass

        if conf < 0.32:
            continue
        if best is None or conf > best[0]:
            best = (conf, rec)

    if best is None:
        return None
    conf, rec = best
    tags = list(dict.fromkeys((rec.get("atmosphere_tags") or []) + (rec.get("theme_tags") or [])))
    summary = str(rec.get("summary_text") or "").strip()
    story = str(rec.get("story_text") or "").strip()

    emotional = ""
    if conf >= 0.55 and tags:
        emotional = f"스토리텔링 태그 기준으로 {', '.join(tags[:3])} 분위기가 두드러집니다."
    elif conf >= 0.55 and summary:
        emotional = "관광 스토리텔링 요약에 따르면 이 장소에 서사·분위기 설명이 붙어 있습니다."

    narrative = ""
    if conf >= 0.4:
        if summary:
            narrative = (
                "관광 스토리텔링 정보 기준으로, 단순 방문지를 넘어 분위기·이야기 맥락이 정리된 장소로 분류됩니다. "
                f"({summary[:90]}{'…' if len(summary) > 90 else ''})"
            )
        else:
            narrative = (
                "관광 스토리텔링 정보가 연결되어 있어, 현장 분위기를 글로 미리 짚어볼 수 있습니다."
            )

    return {
        "story_record": rec,
        "story_summary": summary or (story[:120] + ("…" if len(story) > 120 else "") if story else ""),
        "story_tags": tags[:12],
        "emotional_copy": emotional or None,
        "narrative_enrichment_line": narrative or None,
        "storytelling_match_confidence": round(conf, 3),
    }


def storytelling_fields_for_api(match: dict[str, Any] | None) -> dict[str, Any]:
    """API에 붙일 필드만(원본 raw_row 제외)."""
    if not match:
        return {}
    out = {
        "story_summary": match.get("story_summary") or None,
        "story_tags": match.get("story_tags") or [],
        "emotional_copy": match.get("emotional_copy"),
        "narrative_enrichment_line": match.get("narrative_enrichment_line"),
        "storytelling_match_confidence": match.get("storytelling_match_confidence"),
    }
    return {k: v for k, v in out.items() if v not in (None, "", [])}
