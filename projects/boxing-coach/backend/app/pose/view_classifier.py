"""
정면/측면 자동 분류.

단일 지표(어깨X폭/몸통Y길이)만으론 사선 측면 영상이 정면처럼 보이는 경우가
많아서, 다음 두 지표를 결합한다:

  ratio      = |L_shoulder_x - R_shoulder_x| / |shoulder_center_y - hip_center_y|
  ear_diff   = |left_ear_v - right_ear_v|     (측면은 한쪽 귀가 가려지는 경향)

판정 규칙
  ear_diff >= EAR_DIFF_SIDE                 → side    (가장 확실한 측면)
  ratio    >= FRONT_THRESH and ear_diff < EAR_DIFF_FRONT → front
  ratio    <  SIDE_THRESH                   → side
  else                                       → ambiguous (양쪽 DNA 모두에 포함)
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

ViewMode = Literal["front", "side", "ambiguous"]

SIDE_THRESH      = 0.30
FRONT_THRESH     = 0.55
EAR_DIFF_SIDE    = 0.30   # 한쪽 귀가 거의 안 보이면 측면 확정
EAR_DIFF_FRONT   = 0.15   # 양 귀 visibility 비슷하면 정면 가능


def frame_signals(row: dict) -> tuple[float, float] | None:
    """(ratio, ear_diff) 또는 None (신뢰도 부족)."""
    try:
        ls_v = float(row["left_shoulder_v"]);  rs_v = float(row["right_shoulder_v"])
        lh_v = float(row["left_hip_v"]);       rh_v = float(row["right_hip_v"])
    except KeyError:
        return None
    if min(ls_v, rs_v, lh_v, rh_v) < 0.45:
        return None
    lsx = float(row["left_shoulder_x"]);   rsx = float(row["right_shoulder_x"])
    lsy = float(row["left_shoulder_y"]);   rsy = float(row["right_shoulder_y"])
    lhy = float(row["left_hip_y"]);        rhy = float(row["right_hip_y"])
    sw = abs(lsx - rsx)
    torso = abs((lsy + rsy) / 2 - (lhy + rhy) / 2)
    if torso < 0.05:
        return None
    ratio = sw / torso
    le_v = float(row.get("left_ear_v",  0.0))
    re_v = float(row.get("right_ear_v", 0.0))
    ear_diff = abs(le_v - re_v)
    return ratio, ear_diff


def classify(ratio: float, ear_diff: float) -> ViewMode:
    if ear_diff >= EAR_DIFF_SIDE:
        return "side"
    if ratio >= FRONT_THRESH and ear_diff < EAR_DIFF_FRONT:
        return "front"
    if ratio < SIDE_THRESH:
        return "side"
    return "ambiguous"


def classify_ratio(ratio: float | None) -> ViewMode:
    """ear visibility 정보 없이 ratio만으로 분류 (runtime fallback)."""
    if ratio is None:
        return "ambiguous"
    if ratio < SIDE_THRESH:
        return "side"
    if ratio > FRONT_THRESH:
        return "front"
    return "ambiguous"


def classify_csv(path: str | Path) -> tuple[ViewMode, float | None, float | None, int]:
    """CSV 한 개 → (mode, median_ratio, median_ear_diff, samples)."""
    ratios: list[float] = []
    ears:   list[float] = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            s = frame_signals(row)
            if s is not None:
                ratios.append(s[0]); ears.append(s[1])
    if not ratios:
        return "ambiguous", None, None, 0
    ratios.sort(); ears.sort()
    med_r = ratios[len(ratios) // 2]
    med_e = ears[len(ears) // 2]
    return classify(med_r, med_e), med_r, med_e, len(ratios)
