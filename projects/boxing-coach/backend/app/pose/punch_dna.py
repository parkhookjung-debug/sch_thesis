"""
펀치 감지 + 분류 + 펀치 DNA 집계.

원본: LIM punch extraction side.py — 함수형으로 재구성.

펀치 타입: jab, cross, hook, uppercut
각 펀치 샘플마다 6개 메트릭: arm_extension, elbow_height, wrist_height,
lean_forward, elbow_angle, dip
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable

import numpy as np

PUNCH_TYPES = ["jab", "cross", "hook", "uppercut"]
PUNCH_METRICS = ["arm_extension", "elbow_height", "wrist_height",
                 "lean_forward", "elbow_angle", "dip"]

VEL_THRESH        = 0.022
MIN_PEAK_GAP      = 12
WINDOW_BEFORE     = 8
WINDOW_AFTER      = 6
HOOK_ELBOW_THRESH = 0.10


def _g(row, name, axis):
    return row[f"{name}_{axis}"]


def _sw(row):
    dx = _g(row, "right_shoulder", "x") - _g(row, "left_shoulder", "x")
    dz = _g(row, "right_shoulder", "z") - _g(row, "left_shoulder", "z")
    return math.sqrt(dx * dx + dz * dz) + 1e-6


def _dist2d(row, a, b):
    dx = _g(row, a, "x") - _g(row, b, "x")
    dy = _g(row, a, "y") - _g(row, b, "y")
    return math.sqrt(dx * dx + dy * dy)


def _angle3(ax, ay, bx, by, cx, cy):
    bax, bay = ax - bx, ay - by
    bcx, bcy = cx - bx, cy - by
    dot = bax * bcx + bay * bcy
    mag = math.sqrt(bax**2 + bay**2) * math.sqrt(bcx**2 + bcy**2) + 1e-9
    return math.degrees(math.acos(max(-1, min(1, dot / mag))))


def _lead_wrist(row) -> tuple[str, str]:
    lx = _g(row, "left_wrist", "x")
    rx = _g(row, "right_wrist", "x")
    return ("left_wrist", "right_wrist") if lx < rx else ("right_wrist", "left_wrist")


def read_full_data_csv(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({k: float(v) for k, v in row.items()})
    return rows


def compute_velocities(rows: list[dict]) -> tuple[list[float], list[float]]:
    vel_l = [0.0]
    vel_r = [0.0]
    for i in range(1, len(rows)):
        dlx = _g(rows[i], "left_wrist", "x")  - _g(rows[i-1], "left_wrist", "x")
        dly = _g(rows[i], "left_wrist", "y")  - _g(rows[i-1], "left_wrist", "y")
        drx = _g(rows[i], "right_wrist", "x") - _g(rows[i-1], "right_wrist", "x")
        dry = _g(rows[i], "right_wrist", "y") - _g(rows[i-1], "right_wrist", "y")
        vel_l.append(math.sqrt(dlx**2 + dly**2))
        vel_r.append(math.sqrt(drx**2 + dry**2))
    return vel_l, vel_r


def find_peaks(vels: list[float], thresh: float, min_gap: int) -> list[int]:
    peaks = []
    for i in range(2, len(vels) - 2):
        if (vels[i] >= thresh
                and vels[i] >= vels[i-1] and vels[i] >= vels[i+1]
                and vels[i] >= vels[i-2] and vels[i] >= vels[i+2]):
            if not peaks or i - peaks[-1] >= min_gap:
                peaks.append(i)
    return peaks


def classify_punch(rows: list[dict], peak_idx: int, moving_wrist: str) -> str:
    start = max(0, peak_idx - WINDOW_BEFORE)
    end   = min(len(rows) - 1, peak_idx + WINDOW_AFTER)
    row_p = rows[peak_idx]
    sw    = _sw(row_p)
    sh_cy = (_g(row_p, "left_shoulder", "y") + _g(row_p, "right_shoulder", "y")) / 2

    elbow_name = moving_wrist.replace("wrist", "elbow")
    elbow_y_rel = (_g(row_p, elbow_name, "y") - sh_cy) / sw

    wy_s = _g(rows[start], moving_wrist, "y")
    wy_e = _g(rows[end],   moving_wrist, "y")
    wx_s = _g(rows[start], moving_wrist, "x")
    wx_e = _g(rows[end],   moving_wrist, "x")
    dy = wy_s - wy_e
    dx = abs(wx_e - wx_s)

    if dy > dx * 1.1 and dy > 0.025:
        return "uppercut"
    if elbow_y_rel < HOOK_ELBOW_THRESH:
        return "hook"
    front_w, _rear = _lead_wrist(row_p)
    return "jab" if moving_wrist == front_w else "cross"


def _find_extension_peak(rows, peak_idx, wrist_name) -> int:
    shoulder_name = wrist_name.replace("wrist", "shoulder")
    end = min(len(rows) - 1, peak_idx + WINDOW_AFTER * 2)
    best_idx, best_dist = peak_idx, _dist2d(rows[peak_idx], shoulder_name, wrist_name)
    for i in range(peak_idx + 1, end + 1):
        d = _dist2d(rows[i], shoulder_name, wrist_name)
        if d > best_dist:
            best_dist, best_idx = d, i
    return best_idx


def extract_punch_metrics(rows, peak_idx, wrist_name, punch_type) -> dict:
    ext_idx = _find_extension_peak(rows, peak_idx, wrist_name)
    row = rows[ext_idx]
    sw = _sw(row)
    sh_cy = (_g(row, "left_shoulder", "y") + _g(row, "right_shoulder", "y")) / 2
    sh_cx = (_g(row, "left_shoulder", "x") + _g(row, "right_shoulder", "x")) / 2
    hi_cx = (_g(row, "left_hip", "x")      + _g(row, "right_hip", "x"))      / 2

    elbow_name    = wrist_name.replace("wrist", "elbow")
    shoulder_name = wrist_name.replace("wrist", "shoulder")

    arm_ext   = _dist2d(row, shoulder_name, wrist_name) / sw
    elbow_h   = (_g(row, elbow_name, "y") - sh_cy) / sw
    wrist_h   = (_g(row, wrist_name, "y") - sh_cy) / sw
    lean      = (sh_cx - hi_cx) / sw
    elbow_ang = _angle3(
        _g(row, shoulder_name, "x"), _g(row, shoulder_name, "y"),
        _g(row, elbow_name, "x"),    _g(row, elbow_name, "y"),
        _g(row, wrist_name, "x"),    _g(row, wrist_name, "y"),
    )
    dip = 0.0
    if punch_type == "uppercut":
        hip_ys = [_g(rows[max(0, peak_idx - i)], "left_hip", "y") for i in range(WINDOW_BEFORE)]
        dip = (max(hip_ys) - min(hip_ys)) / sw

    return {
        "arm_extension": round(arm_ext, 4),
        "elbow_height":  round(elbow_h, 4),
        "wrist_height":  round(wrist_h, 4),
        "lean_forward":  round(lean, 4),
        "elbow_angle":   round(elbow_ang, 2),
        "dip":           round(dip, 4),
    }


def detect_punches_in_csv(csv_path: str | Path) -> list[dict]:
    """Detect all punches in one full_data csv → list of dicts with type+metrics+frame."""
    rows = read_full_data_csv(csv_path)
    if len(rows) < 5:
        return []
    vel_l, vel_r = compute_velocities(rows)
    peaks = ([(p, "left_wrist") for p in find_peaks(vel_l, VEL_THRESH, MIN_PEAK_GAP)]
             + [(p, "right_wrist") for p in find_peaks(vel_r, VEL_THRESH, MIN_PEAK_GAP)])

    out = []
    used: set[int] = set()
    for peak_idx, wrist in peaks:
        if peak_idx in used:
            continue
        used.add(peak_idx)
        pt = classify_punch(rows, peak_idx, wrist)
        m = extract_punch_metrics(rows, peak_idx, wrist, pt)
        m["punch_type"] = pt
        m["wrist"] = wrist
        m["frame"] = int(rows[peak_idx]["frame_number"])
        out.append(m)
    return out


def aggregate_punch_dna(csv_paths: Iterable[str | Path]) -> list[dict]:
    """Aggregate punches across multiple CSVs into one row per punch type."""
    by_type: dict[str, list[dict]] = {t: [] for t in PUNCH_TYPES}
    for path in csv_paths:
        path = Path(path)
        if not path.exists():
            print(f"[punch_dna] skip missing: {path.name}")
            continue
        for p in detect_punches_in_csv(path):
            by_type[p["punch_type"]].append(p)

    out_rows = []
    for ptype in PUNCH_TYPES:
        samples = by_type[ptype]
        row: dict = {"punch_type": ptype, "count": len(samples)}
        if not samples:
            for k in PUNCH_METRICS:
                row[f"{k}_avg"] = 0.0
                row[f"{k}_std"] = 0.0
        else:
            for k in PUNCH_METRICS:
                vals = [s[k] for s in samples]
                row[f"{k}_avg"] = round(float(np.mean(vals)), 4)
                row[f"{k}_std"] = round(float(np.std(vals)), 4)
        out_rows.append(row)
    return out_rows


def save_punch_dna_csv(rows: list[dict], out_path: str | Path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["punch_type", "count"] + [f"{k}_avg" for k in PUNCH_METRICS] + [f"{k}_std" for k in PUNCH_METRICS]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def load_punch_dna_csv(path: str | Path) -> dict[str, dict]:
    """Return {punch_type: {metric_avg, metric_std, count}}."""
    result: dict[str, dict] = {}
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pt = row["punch_type"]
            result[pt] = {k: float(v) for k, v in row.items() if k != "punch_type"}
    return result
