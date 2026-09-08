# -*- coding: utf-8 -*-
"""
시나리오 학습 `next_scene` 추론 (선택, 실험용).

- 데이터는 **합성·약지도 시나리오** 전제이며 실사용 개인화를 의미하지 않는다.
- 아티팩트가 없거나 오류 시 **항상 규칙 기반 단계**를 유지한다.
- `/api/course`에서는 `ml_next_scene_assist=true`일 때만 호출 경로에 들어간다.
  홈페이지·기본 클라이언트는 이 플래그를 켜지 않으므로 규칙만 사용한다.
"""
from __future__ import annotations

from typing import Any

import joblib
import numpy as np

from app.ml import feature_builder
from app.ml import model_io
from lib.config import settings

# 규칙 엔진과 동일하게 취급 가능한 단계만 채택 (go_home 등은 별도 매핑)
_ML_ALLOWED = frozenset(
    {"meal", "cafe_rest", "indoor_backup", "short_walk", "sunset_finish", "indoor_visit"}
)


def try_model_stage_override(
    *,
    rule_stage: str,
    spot_meta: dict[str, Any],
    trip_state: dict[str, float],
    hour: int,
    intent: dict[str, str],
    scores: dict[str, Any] | None,
    precip_prob: float,
    dust: int,
    temp: float,
) -> tuple[str, dict[str, Any]]:
    """
    규칙 단계 `rule_stage`를 기준으로, 모델이 켜져 있고 신뢰도가 충분하면 모델 예측으로 덮어쓴다.

    Returns:
        (chosen_stage, ml_meta)
    """
    base_meta: dict[str, Any] = {
        "model_used": False,
        "next_scene_reason_mode": "rule-based",
        "predicted_next_scene": None,
        "rule_based_stage": rule_stage,
        "scene_probs": None,
        "top_features": None,
    }

    if not getattr(settings, "use_next_scene_model", False):
        return rule_stage, base_meta

    if not model_io.bundle_ready():
        return rule_stage, base_meta

    try:
        pipe = joblib.load(model_io.model_path())
        le = joblib.load(model_io.label_encoder_path())
        feature_cols = model_io.load_json_list(model_io.feature_columns_path())
    except Exception:
        return rule_stage, base_meta

    meta_art = model_io.load_metadata()
    schema = str(meta_art.get("feature_schema") or "")
    if schema == "scenario_synthetic_v1" or (
        feature_cols and feature_cols[0] == "duration_type"
    ):
        row = feature_builder.row_from_scenario_context(
            spot_meta=spot_meta,
            trip_state=trip_state,
            hour=hour,
            intent=intent,
            scores=scores,
            precip_prob=precip_prob,
            dust=dust,
            temp=temp,
        )
    else:
        row = feature_builder.row_from_course_context(
            spot_meta=spot_meta,
            trip_state=trip_state,
            hour=hour,
            intent=intent,
            scores=scores,
            precip_prob=precip_prob,
            dust=dust,
            temp=temp,
        )
    try:
        feature_builder.assert_columns_present(row, feature_cols)
    except Exception:
        return rule_stage, base_meta

    import pandas as pd

    X = pd.DataFrame([{c: row[c] for c in feature_cols}])

    try:
        y_idx = pipe.predict(X)[0]
        probs = pipe.predict_proba(X)[0]
    except Exception:
        return rule_stage, base_meta

    classes = [str(x) for x in getattr(le, "classes_", [])]
    if len(classes) != len(probs):
        return rule_stage, base_meta

    scene_probs = {classes[i]: float(probs[i]) for i in range(len(classes))}
    pred_label = str(le.inverse_transform(np.asarray([int(y_idx)], dtype=int))[0])

    if pred_label not in _ML_ALLOWED:
        if pred_label == "go_home":
            pred_label = "cafe_rest"
        else:
            return rule_stage, {**base_meta, "scene_probs": scene_probs, "predicted_next_scene": pred_label}

    max_p = float(max(probs))
    if max_p < float(getattr(settings, "next_scene_model_min_confidence", 0.38)):
        return rule_stage, {
            **base_meta,
            "scene_probs": scene_probs,
            "predicted_next_scene": pred_label,
            "next_scene_reason_mode": "rule-based",
        }

    top_hits = _top_feature_hits(pipe, X) if settings.debug else None

    meta_out = {
        "model_used": True,
        "next_scene_reason_mode": "model-assisted",
        "predicted_next_scene": pred_label,
        "rule_based_stage": rule_stage,
        "scene_probs": scene_probs,
        "top_features": top_hits,
    }
    return pred_label, meta_out


def _top_feature_hits(pipe: Any, X: Any, k: int = 8) -> list[dict[str, Any]] | None:
    try:
        pre = pipe.named_steps.get("pre")
        clf = pipe.named_steps.get("clf")
        if pre is None or clf is None:
            return None
        names = list(pre.get_feature_names_out())
        if hasattr(clf, "feature_importances_") and len(clf.feature_importances_) == len(names):
            imp = clf.feature_importances_
            pairs = sorted(zip(names, imp), key=lambda x: -x[1])[:k]
            return [{"feature": a, "importance": round(float(b), 5)} for a, b in pairs]
    except Exception:
        return None
    return None
