# -*- coding: utf-8 -*-
"""
시나리오 CSV로 `next_scene` 멀티클래스 모델 학습.

- 데이터는 **합성·약지도(weak supervision)** 전제이며 실사용 로그가 아니다.
- `--write-demo-data` 는 규칙 엔진 교사로 소량 행을 생성해 파이프라인만 검증한다.

사용 예:
  pip install -r requirements-ml.txt
  python scripts/train_next_scene_model.py --write-demo-data
  python scripts/train_next_scene_model.py --data-dir data/scenario_ml
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def load_feature_roles(path: Path) -> tuple[list[str], list[str], str]:
    """Returns (numeric_cols, categorical_cols, target_col).

    지원 형식:
    - 레거시: column, role in (numeric|categorical|target|exclude)
    - 시나리오 스키마: column_name, role, data_type (chungnam_feature_roles.csv)
    """
    numeric: list[str] = []
    categorical: list[str] = []
    target = "next_scene"
    with open(path, encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        fields = [x.strip().lower().lstrip("\ufeff") for x in (r.fieldnames or [])]
        if "column_name" in fields:
            for row in r:
                col = (row.get("column_name") or "").strip()
                role = (row.get("role") or "").strip().lower()
                dtype = (row.get("data_type") or "").strip().lower()
                if not col:
                    continue
                if role in ("id", "meta", "target_optional", "feature_text"):
                    continue
                if role == "target":
                    target = col
                    continue
                if role == "target_or_feature":
                    continue
                if role != "feature":
                    continue
                if dtype in ("numeric", "binary", "ordinal"):
                    numeric.append(col)
                elif dtype == "categorical":
                    categorical.append(col)
                else:
                    numeric.append(col)
            return numeric, categorical, target

        for row in r:
            col = (row.get("column") or "").strip()
            role = (row.get("role") or "").strip().lower()
            if not col:
                continue
            if role == "target":
                target = col
            elif role == "numeric":
                numeric.append(col)
            elif role == "categorical":
                categorical.append(col)
            elif role == "exclude":
                continue
    return numeric, categorical, target


def write_demo_scenarios(data_dir: Path, n_rows: int = 900, seed: int = 42) -> None:
    """규칙 기반 교사(`decide_next_stage`)로 데모 CSV 생성.

    사용자 시나리오 CSV를 덮어쓰지 않도록 `data/scenario_ml/_demo_rule_teacher/` 에만 씁니다.
    학습 예: python scripts/train_next_scene_model.py --data-dir data/scenario_ml/_demo_rule_teacher
    """
    from lib.course_continuation import decide_next_stage, estimate_trip_state

    random.seed(seed)
    out_dir = data_dir / "_demo_rule_teacher"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    goals = ["healing", "photo", "walking", "indoor", "culture", "kids"]
    comps = ["solo", "couple", "family", "friends"]
    durs = ["2h", "half-day", "full-day"]
    trans = ["car", "public"]
    cats = ["outdoor", "indoor", "outdoor", "outdoor"]
    acts = ["low", "moderate", "high"]

    for _ in range(n_rows):
        hour = random.randint(8, 21)
        precip_prob = random.uniform(0, 100)
        dust = random.randint(1, 4)
        temp = random.uniform(-2, 36)
        intent = {
            "companion": random.choice(comps),
            "trip_goal": random.choice(goals),
            "duration": random.choice(durs),
            "transport": random.choice(trans),
        }
        spot_meta: dict[str, Any] = {
            "category": random.choice(cats),
            "activity_level": random.choice(acts),
            "indoor_ratio": random.uniform(0.05, 0.85),
            "avg_stay_minutes": float(random.choice([45, 60, 75, 90, 120])),
            "photo_fit": random.uniform(0.35, 0.95),
            "healing_fit": random.uniform(0.35, 0.95),
            "golden_hour_bonus": random.random() < 0.15,
        }
        scores = {
            "is_raining": precip_prob >= 65 and random.random() < 0.7,
            "is_dust_bad": dust >= 3,
            "is_golden_hour": 16 <= hour <= 18 and random.random() < 0.4,
        }
        trip_state = estimate_trip_state(
            spot_meta, hour, intent, scores, precip_prob, dust
        )
        st, _, _ = decide_next_stage(
            spot_meta, trip_state, hour, intent, scores, precip_prob, dust
        )
        row = {
            "hour": hour,
            "precip_prob": round(precip_prob, 2),
            "dust": dust,
            "temp": round(temp, 2),
            "companion": intent["companion"],
            "trip_goal": intent["trip_goal"],
            "duration": intent["duration"],
            "transport": intent["transport"],
            "spot_category": spot_meta["category"],
            "activity_level": spot_meta["activity_level"],
            "need_meal": trip_state["need_meal"],
            "need_rest": trip_state["need_rest"],
            "need_indoor": trip_state["need_indoor"],
            "keep_healing_mood": trip_state["keep_healing_mood"],
            "move_tolerance": trip_state["move_tolerance"],
            "indoor_ratio": spot_meta["indoor_ratio"],
            "avg_stay_minutes": spot_meta["avg_stay_minutes"],
            "photo_fit": spot_meta["photo_fit"],
            "healing_fit": spot_meta["healing_fit"],
            "golden_hour_bonus": 1.0 if spot_meta["golden_hour_bonus"] else 0.0,
            "is_raining": 1.0 if scores["is_raining"] else 0.0,
            "is_dust_bad": 1.0 if scores["is_dust_bad"] else 0.0,
            "is_golden_hour": 1.0 if scores["is_golden_hour"] else 0.0,
            "next_scene": st,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    train, rest = train_test_split(df, test_size=0.25, random_state=seed, stratify=df["next_scene"])
    valid, test = train_test_split(rest, test_size=0.5, random_state=seed, stratify=rest["next_scene"])
    train.to_csv(out_dir / "chungnam_scenarios_train.csv", index=False)
    valid.to_csv(out_dir / "chungnam_scenarios_valid.csv", index=False)
    test.to_csv(out_dir / "chungnam_scenarios_test.csv", index=False)
    print(f"[demo] wrote train/valid/test to {out_dir}", file=sys.stderr)


def build_preprocess(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[("imputer", SimpleImputer(strategy="median"))],
                ),
                numeric,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ],
                ),
                categorical,
            ),
        ]
    )


def train_and_eval(
    train: pd.DataFrame,
    valid: pd.DataFrame,
    test: pd.DataFrame,
    numeric: list[str],
    categorical: list[str],
    target: str,
    seed: int,
) -> tuple[Any, LabelEncoder, str, dict[str, Any], dict[str, Any]]:
    feature_cols = [c for c in numeric + categorical if c in train.columns]
    X_train = train[feature_cols]
    y_train = train[target].astype(str)
    le = LabelEncoder()
    y_enc_train = le.fit_transform(y_train)

    X_valid = valid[feature_cols]
    y_valid = le.transform(valid[target].astype(str))
    X_test = test[feature_cols]
    y_test = le.transform(test[target].astype(str))

    candidates: list[tuple[str, Any]] = [
        (
            "hist_gradient_boosting",
            HistGradientBoostingClassifier(
                max_depth=8,
                learning_rate=0.08,
                max_iter=200,
                min_samples_leaf=10,
                random_state=seed,
            ),
        ),
        (
            "logistic_ovr",
            LogisticRegression(
                max_iter=3000,
                multi_class="multinomial",
                solver="lbfgs",
                random_state=seed,
            ),
        ),
    ]

    try:
        import lightgbm as lgb  # type: ignore

        candidates.insert(
            0,
            (
                "lightgbm",
                lgb.LGBMClassifier(
                    objective="multiclass",
                    n_estimators=200,
                    learning_rate=0.06,
                    max_depth=-1,
                    subsample=0.9,
                    colsample_bytree=0.85,
                    random_state=seed,
                    verbosity=-1,
                ),
            ),
        )
    except Exception:
        pass

    best_name = ""
    best_f1 = -1.0
    best_pipe: Pipeline | None = None

    for name, clf in candidates:
        pre_f = build_preprocess(numeric, categorical)
        pipe = Pipeline([("pre", pre_f), ("clf", clf)])
        try:
            pipe.fit(X_train, y_enc_train)
            pred_v = pipe.predict(X_valid)
            f1v = f1_score(y_valid, pred_v, average="macro")
            if f1v > best_f1:
                best_f1 = f1v
                best_name = name
                best_pipe = pipe
        except Exception as e:
            print(f"[train] skip {name}: {e}", file=sys.stderr)

    if best_pipe is None:
        raise RuntimeError("No model trained successfully")

    pred_v = best_pipe.predict(X_valid)
    pred_t = best_pipe.predict(X_test)

    def pack_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
        return {
            "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
            "classification_report": classification_report(
                y_true,
                y_pred,
                labels=np.arange(len(le.classes_)),
                target_names=list(le.classes_),
                zero_division=0,
                output_dict=True,
            ),
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
            "labels": list(le.classes_),
        }

    m_valid = pack_metrics(y_valid, pred_v)
    m_test = pack_metrics(y_test, pred_t)
    return best_pipe, le, best_name, m_valid, m_test


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=_ROOT / "data" / "scenario_ml")
    ap.add_argument(
        "--artifacts-dir",
        type=Path,
        default=_ROOT / "data" / "scenario_ml" / "artifacts" / "next_scene_model",
    )
    ap.add_argument("--roles", type=Path, default=None)
    ap.add_argument("--write-demo-data", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    data_dir: Path = args.data_dir
    art_dir: Path = args.artifacts_dir
    roles_path = args.roles or (data_dir / "chungnam_feature_roles.csv")

    if args.write_demo_data:
        write_demo_scenarios(data_dir, seed=args.seed)

    train_path = data_dir / "chungnam_scenarios_train.csv"
    valid_path = data_dir / "chungnam_scenarios_valid.csv"
    test_path = data_dir / "chungnam_scenarios_test.csv"
    for p in (train_path, valid_path, test_path, roles_path):
        if not p.is_file():
            print(f"Missing required file: {p}", file=sys.stderr)
            sys.exit(1)

    numeric, categorical, target = load_feature_roles(roles_path)
    train = pd.read_csv(train_path)
    valid = pd.read_csv(valid_path)
    test = pd.read_csv(test_path)

    pipe, le, best_name, m_valid, m_test = train_and_eval(
        train, valid, test, numeric, categorical, target, args.seed
    )

    art_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(pipe, art_dir / "model.joblib")
    joblib.dump(le, art_dir / "label_encoder.joblib")
    feature_cols = [c for c in numeric + categorical if c in train.columns]
    with open(art_dir / "feature_columns.json", "w", encoding="utf-8") as f:
        json.dump(feature_cols, f, ensure_ascii=False, indent=2)

    with open(art_dir / "metrics_valid.json", "w", encoding="utf-8") as f:
        json.dump(m_valid, f, ensure_ascii=False, indent=2)
    with open(art_dir / "metrics_test.json", "w", encoding="utf-8") as f:
        json.dump(m_test, f, ensure_ascii=False, indent=2)

    schema = "scenario_synthetic_v1" if "duration_type" in feature_cols else "course_api_v1"
    meta = {
        "best_model": best_name,
        "target": target,
        "feature_schema": schema,
        "feature_columns": feature_cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "data_disclaimer": "Synthetic / weak-supervision scenario data - not real user behavior.",
        "macro_f1_valid": m_valid["macro_f1"],
        "macro_f1_test": m_test["macro_f1"],
    }
    with open(art_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(json.dumps(meta, ensure_ascii=True, indent=2))
    print("\n[valid] macro_f1", m_valid["macro_f1"], file=sys.stderr)
    print("[test] macro_f1", m_test["macro_f1"], file=sys.stderr)
    print("[artifacts]", str(art_dir), file=sys.stderr)


if __name__ == "__main__":
    main()
