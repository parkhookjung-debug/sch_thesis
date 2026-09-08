# -*- coding: utf-8 -*-
"""
코스 단위 후보 재정렬(선택 ML 레이어).

- 규칙 엔진이 만든 **완성 코스 후보** 목록을 입력으로 받는다.
- 학습된 코스 재정렬 번들이 없으면 **순서를 바꾸지 않고** rule-based 메타만 반환한다.
- next_scene(단계 예측) 모델과 역할이 다르다 — 혼용하지 않는다.
"""
from __future__ import annotations

from typing import Any

from lib.config import settings


def _bundle_path_configured() -> bool:
    d = getattr(settings, "course_rerank_model_dir", None)
    return bool(d and str(d).strip())


def apply_course_rerank(
    candidates: list[dict[str, Any]],
    *,
    intent: dict[str, str],
    weather: dict[str, Any],
    scores: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    코스 후보 순서를 결정한다.

    현재 저장소에는 코스 단위 재학습 번들이 없으므로 항상 규칙이 만든 순서를 유지하고,
    `model_used=False` 로 명시한다. 번들 연동은 이 함수 내부에만 추가하면 된다.

    Returns:
        (ordered_candidates, course_rerank_meta)
    """
    _ = intent, weather, scores
    if not candidates:
        return [], {
            "enabled": True,
            "model_used": False,
            "rerank_mode": "rule-based",
            "fallback_reason": "no_course_candidates",
        }

    # --- 향후: COURSE_RERANK_MODEL_DIR 아티팩트 로드 후 점수·순서 재배열 ---
    # if course_rerank_bundle_ready(): ...
    _configured = _bundle_path_configured()
    fallback = (
        "no_trained_course_rerank_bundle"
        if not _configured
        else "course_rerank_bundle_not_implemented"
    )

    meta: dict[str, Any] = {
        "enabled": True,
        "model_used": False,
        "rerank_mode": "rule-based",
        "fallback_reason": fallback,
    }
    return list(candidates), meta
