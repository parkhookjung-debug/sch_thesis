"""
자세 DNA 계산 — LIM master average.py 의 메트릭 정의를 함수화.

입력: full_data CSV 들 (RTMPose COCO 17 normalized).
출력: 17개 파생 메트릭의 avg/std (한 행짜리 dict).
"""
from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from typing import Iterable

from ..config import VISIBILITY_MIN_DNA

# 메트릭 키 정의 — 순서 고정 (DNA CSV 열 순서와 매칭에 사용)
DNA_METRICS = [
    "guard_l_ydiff",
    "guard_r_ydiff",
    "guard_l_zdiff",
    "guard_r_zdiff",
    "guard_l_elbow_y",
    "guard_r_elbow_y",
    "stance_3d_ratio",
    "stance_step_x",
    "knee_bend_l",
    "knee_bend_r",
    "guard_l_xfwd",
    "guard_r_xfwd",
    "guard_lr_xdiff",
    "lean_forward",
    "head_y_ratio",
    "head_fwd_z",
    "shoulder_tilt",
]

NEEDED_KEYPOINTS = [
    "left_shoulder", "right_shoulder",
    "left_wrist",    "right_wrist",
    "left_elbow",    "right_elbow",
    "left_hip",      "right_hip",
    "left_knee",     "right_knee",
    "left_ankle",    "right_ankle",
    "nose",
]


def _angle3(ax, ay, bx, by, cx, cy):
    bax, bay = ax - bx, ay - by
    bcx, bcy = cx - bx, cy - by
    dot = bax * bcx + bay * bcy
    mag = math.sqrt(bax**2 + bay**2) * math.sqrt(bcx**2 + bcy**2) + 1e-9
    return math.degrees(math.acos(max(-1, min(1, dot / mag))))


def _v(row, name):
    return float(row[f"{name}_v"])


def _xyz(row, name):
    return float(row[f"{name}_x"]), float(row[f"{name}_y"]), float(row[f"{name}_z"])


def compute_frame_metrics(row: dict) -> dict | None:
    """Compute one-frame metrics dict, or None if visibility insufficient."""
    if any(_v(row, n) < VISIBILITY_MIN_DNA for n in NEEDED_KEYPOINTS):
        return None

    l_sh_x, l_sh_y, l_sh_z = _xyz(row, "left_shoulder")
    r_sh_x, r_sh_y, r_sh_z = _xyz(row, "right_shoulder")
    sh_cx = (l_sh_x + r_sh_x) / 2
    sh_cy = (l_sh_y + r_sh_y) / 2
    sh_cz = (l_sh_z + r_sh_z) / 2
    sw = math.sqrt((r_sh_x - l_sh_x) ** 2 + (r_sh_z - l_sh_z) ** 2) + 1e-6

    nose_x, nose_y, nose_z = _xyz(row, "nose")
    l_wr_x, l_wr_y, l_wr_z = _xyz(row, "left_wrist")
    r_wr_x, r_wr_y, r_wr_z = _xyz(row, "right_wrist")
    l_el_x, l_el_y, _ = _xyz(row, "left_elbow")
    r_el_x, r_el_y, _ = _xyz(row, "right_elbow")
    l_hi_x, l_hi_y, _ = _xyz(row, "left_hip")
    r_hi_x, r_hi_y, _ = _xyz(row, "right_hip")
    hi_cx = (l_hi_x + r_hi_x) / 2
    l_kn_x, l_kn_y, _ = _xyz(row, "left_knee")
    r_kn_x, r_kn_y, _ = _xyz(row, "right_knee")
    l_an_x, l_an_y, l_an_z = _xyz(row, "left_ankle")
    r_an_x, r_an_y, r_an_z = _xyz(row, "right_ankle")

    ankle_3d = math.sqrt((r_an_x - l_an_x) ** 2 + (r_an_z - l_an_z) ** 2)

    return {
        "guard_l_ydiff":   (l_wr_y - l_sh_y) / sw,
        "guard_r_ydiff":   (r_wr_y - r_sh_y) / sw,
        "guard_l_zdiff":   (l_wr_z - l_sh_z) / sw,
        "guard_r_zdiff":   (r_wr_z - r_sh_z) / sw,
        "guard_l_elbow_y": (l_el_y - l_sh_y) / sw,
        "guard_r_elbow_y": (r_el_y - r_sh_y) / sw,
        "stance_3d_ratio": ankle_3d / sw,
        "stance_step_x":   abs(r_an_x - l_an_x) / sw,
        "knee_bend_l":     _angle3(l_hi_x, l_hi_y, l_kn_x, l_kn_y, l_an_x, l_an_y),
        "knee_bend_r":     _angle3(r_hi_x, r_hi_y, r_kn_x, r_kn_y, r_an_x, r_an_y),
        "guard_l_xfwd":    (l_wr_x - sh_cx) / sw,
        "guard_r_xfwd":    (r_wr_x - sh_cx) / sw,
        "guard_lr_xdiff":  abs(l_wr_x - r_wr_x) / sw,
        "lean_forward":    (sh_cx - hi_cx) / sw,
        "head_y_ratio":    (nose_y - sh_cy) / sw,
        "head_fwd_z":      (nose_z - sh_cz) / sw,
        "shoulder_tilt":   (r_sh_y - l_sh_y) / sw,
    }


def aggregate_dna_from_csvs(csv_paths: Iterable[str | Path]) -> dict:
    """Aggregate full_data CSVs into a single DNA dict (avg + std per metric)."""
    buckets: dict[str, list[float]] = {k: [] for k in DNA_METRICS}
    used = total = 0

    for path in csv_paths:
        path = Path(path)
        if not path.exists():
            print(f"[dna] skip missing: {path.name}")
            continue
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                total += 1
                m = compute_frame_metrics(row)
                if m is None:
                    continue
                for k, v in m.items():
                    buckets[k].append(v)
                used += 1

    dna: dict[str, float] = {}
    for key in DNA_METRICS:
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


def save_dna_csv(dna: dict, out_path: str | Path) -> None:
    """Write DNA dict as single-row CSV (skip internal underscore keys)."""
    keys = [k for k in dna.keys() if not k.startswith("_")]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerow({k: dna[k] for k in keys})


def load_dna_csv(path: str | Path) -> dict:
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return {k: float(v) for k, v in row.items()}
    raise ValueError(f"empty DNA csv: {path}")
