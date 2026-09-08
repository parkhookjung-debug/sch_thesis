"""
정면 카메라용 자세 DNA.

측면용(`dna.py`)과의 핵심 차이:
- z 축 의존 메트릭 제거 (단안 카메라이므로 z=0)
- lean_forward (어깨X - 엉덩이X) 제거 — 정면에선 거의 0
- 어깨폭 정규화는 단순 |left_shoulder_x - right_shoulder_x| (X만)
- 새 메트릭: 어깨 tilt, 골반 tilt, 어깨-골반 폭 비율(몸 회전 정도),
            가드 손목의 좌우 위치(얼굴 가드 X), 가드 손목의 Y 위치
"""
from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from typing import Iterable

from ..config import VISIBILITY_MIN_DNA

DNA_FRONT_METRICS = [
    "guard_l_y",          # (left_wrist_y  - left_shoulder_y)  / sw
    "guard_r_y",          # (right_wrist_y - right_shoulder_y) / sw
    "guard_l_elbow_y",    # (left_elbow_y  - left_shoulder_y)  / sw
    "guard_r_elbow_y",    # (right_elbow_y - right_shoulder_y) / sw
    "guard_l_xcenter",    # (left_wrist_x  - shoulder_center_x) / sw  (양수=오른쪽)
    "guard_r_xcenter",    # (right_wrist_x - shoulder_center_x) / sw
    "guard_lr_xdiff",     # |left_wrist_x - right_wrist_x| / sw
    "shoulder_tilt",      # (right_shoulder_y - left_shoulder_y) / sw
    "hip_tilt",           # (right_hip_y - left_hip_y) / sw
    "shoulder_hip_ratio", # shoulder_width / hip_width  (몸 회전·자세 기준)
    "stance_step_x",      # |left_ankle_x - right_ankle_x| / sw
    "knee_bend_l",        # 좌측 무릎 각도 (도)
    "knee_bend_r",        # 우측 무릎 각도 (도)
    "head_y_ratio",       # (nose_y - shoulder_center_y) / sw
    "head_xcenter",       # (nose_x - shoulder_center_x) / sw
]

NEEDED_KEYPOINTS_UPPER = [
    "left_shoulder", "right_shoulder",
    "left_wrist",    "right_wrist",
    "left_elbow",    "right_elbow",
    "left_hip",      "right_hip",
    "nose",
]
NEEDED_KEYPOINTS_LOWER = ["left_knee", "right_knee", "left_ankle", "right_ankle"]


def _angle3(ax, ay, bx, by, cx, cy):
    bax, bay = ax - bx, ay - by
    bcx, bcy = cx - bx, cy - by
    dot = bax * bcx + bay * bcy
    mag = math.sqrt(bax**2 + bay**2) * math.sqrt(bcx**2 + bcy**2) + 1e-9
    return math.degrees(math.acos(max(-1, min(1, dot / mag))))


def _v(row, name):
    return float(row[f"{name}_v"])


def _xy(row, name):
    return float(row[f"{name}_x"]), float(row[f"{name}_y"])


def compute_frame_metrics_front(row: dict) -> dict | None:
    """정면 메트릭 한 프레임. 상체는 필수, 하체는 보이면 평균에 포함."""
    if any(_v(row, n) < VISIBILITY_MIN_DNA for n in NEEDED_KEYPOINTS_UPPER):
        return None

    l_sh_x, l_sh_y = _xy(row, "left_shoulder")
    r_sh_x, r_sh_y = _xy(row, "right_shoulder")
    sw = abs(l_sh_x - r_sh_x) + 1e-6  # 정면 어깨폭 = 단순 X 거리
    sh_cx = (l_sh_x + r_sh_x) / 2
    sh_cy = (l_sh_y + r_sh_y) / 2

    nose_x, nose_y = _xy(row, "nose")
    l_wr_x, l_wr_y = _xy(row, "left_wrist")
    r_wr_x, r_wr_y = _xy(row, "right_wrist")
    l_el_x, l_el_y = _xy(row, "left_elbow")
    r_el_x, r_el_y = _xy(row, "right_elbow")
    l_hi_x, l_hi_y = _xy(row, "left_hip")
    r_hi_x, r_hi_y = _xy(row, "right_hip")
    hip_w = abs(l_hi_x - r_hi_x) + 1e-6

    out: dict[str, float] = {
        "guard_l_y":          (l_wr_y - l_sh_y) / sw,
        "guard_r_y":          (r_wr_y - r_sh_y) / sw,
        "guard_l_elbow_y":    (l_el_y - l_sh_y) / sw,
        "guard_r_elbow_y":    (r_el_y - r_sh_y) / sw,
        "guard_l_xcenter":    (l_wr_x - sh_cx) / sw,
        "guard_r_xcenter":    (r_wr_x - sh_cx) / sw,
        "guard_lr_xdiff":     abs(l_wr_x - r_wr_x) / sw,
        "shoulder_tilt":      (r_sh_y - l_sh_y) / sw,
        "hip_tilt":           (r_hi_y - l_hi_y) / sw,
        "shoulder_hip_ratio": sw / hip_w,
        "head_y_ratio":       (nose_y - sh_cy) / sw,
        "head_xcenter":       (nose_x - sh_cx) / sw,
    }

    # 하체는 보일 때만 계산 (보이지 않으면 None 키로 두고 외부에서 skip)
    if all(_v(row, n) >= VISIBILITY_MIN_DNA for n in NEEDED_KEYPOINTS_LOWER):
        l_kn_x, l_kn_y = _xy(row, "left_knee")
        r_kn_x, r_kn_y = _xy(row, "right_knee")
        l_an_x, l_an_y = _xy(row, "left_ankle")
        r_an_x, r_an_y = _xy(row, "right_ankle")
        out["stance_step_x"] = abs(l_an_x - r_an_x) / sw
        out["knee_bend_l"]   = _angle3(l_hi_x, l_hi_y, l_kn_x, l_kn_y, l_an_x, l_an_y)
        out["knee_bend_r"]   = _angle3(r_hi_x, r_hi_y, r_kn_x, r_kn_y, r_an_x, r_an_y)
    return out


def aggregate_dna_front(csv_paths: Iterable[str | Path]) -> dict:
    buckets: dict[str, list[float]] = {k: [] for k in DNA_FRONT_METRICS}
    used = total = 0

    for path in csv_paths:
        path = Path(path)
        if not path.exists():
            print(f"[dna_front] skip missing: {path.name}")
            continue
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                total += 1
                m = compute_frame_metrics_front(row)
                if m is None:
                    continue
                for k, v in m.items():
                    buckets[k].append(v)
                used += 1

    dna: dict[str, float] = {}
    for key in DNA_FRONT_METRICS:
        vals = buckets[key]
        if vals:
            dna[key] = statistics.mean(vals)
            dna[f"{key}_std"] = statistics.stdev(vals) if len(vals) > 1 else 0.0
        else:
            dna[key] = 0.0
            dna[f"{key}_std"] = 0.0
    dna["_frames_total"] = total
    dna["_frames_used"] = used
    return dna


def save_dna_front_csv(dna: dict, out_path: str | Path) -> None:
    keys = [k for k in dna.keys() if not k.startswith("_")]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerow({k: dna[k] for k in keys})


def load_dna_front_csv(path: str | Path) -> dict:
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            return {k: float(v) for k, v in row.items()}
    raise ValueError(f"empty front DNA: {path}")
