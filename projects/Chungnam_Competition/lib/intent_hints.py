# -*- coding: utf-8 -*-
"""
의도 → 태그 키워드 힌트. daytrip_planner / place_narrative / main_scoring 공용.
(recommend_ui → place_narrative 경로에서 daytrip_planner를 import하면 순환 의존이 생기므로 분리)
"""
from __future__ import annotations

from typing import Any

_GOAL_TAG_HINTS: dict[str, tuple[str, ...]] = {
    "healing": ("힐링", "온천", "자연", "산책", "조용"),
    "photo": ("사진", "일출", "야경", "전망", "테라스"),
    "walking": ("산책", "걷기", "트레킹", "둘레길", "성곽"),
    "indoor": ("실내", "전시", "박물관", "미술"),
    "culture": ("역사", "문화", "유적", "박물관", "전통", "유네스코"),
    "kids": ("가족", "체험", "아이", "키즈", "놀이"),
}

_COMPANION_HINTS: dict[str, tuple[str, ...]] = {
    "solo": ("산책", "사진", "전망", "조용"),
    "couple": ("로맨틱", "카페", "야경", "온천"),
    "family": ("가족", "체험", "아이", "박물관"),
    "friends": ("레저", "체험", "해변", "캠핑"),
}


def _tags_lower(dest: dict[str, Any]) -> list[str]:
    return [str(x).lower() for x in dest.get("tags") or []]
