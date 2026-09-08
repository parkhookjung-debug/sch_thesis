# -*- coding: utf-8 -*-
"""아티팩트 경로·로드 (학습 파이프라인과 추론 공용)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lib.config import settings

DEFAULT_REL = Path("data/scenario_ml/artifacts/next_scene_model")


def artifact_dir() -> Path:
    raw = getattr(settings, "next_scene_model_dir", None)
    if raw:
        p = Path(str(raw))
        return p if p.is_absolute() else settings.project_root / p
    return settings.project_root / DEFAULT_REL


def model_path() -> Path:
    return artifact_dir() / "model.joblib"


def label_encoder_path() -> Path:
    return artifact_dir() / "label_encoder.joblib"


def feature_columns_path() -> Path:
    return artifact_dir() / "feature_columns.json"


def metadata_path() -> Path:
    return artifact_dir() / "metadata.json"


def bundle_ready() -> bool:
    d = artifact_dir()
    return (
        d.is_dir()
        and model_path().is_file()
        and label_encoder_path().is_file()
        and feature_columns_path().is_file()
    )


def load_json_list(path: Path) -> list[str]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("feature_columns.json must be a JSON list")
    return [str(x) for x in data]


def load_metadata() -> dict[str, Any]:
    p = metadata_path()
    if not p.is_file():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)
