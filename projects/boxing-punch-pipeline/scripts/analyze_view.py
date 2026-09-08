"""Estimate camera view (front vs side) per video from pose statistics.

Heuristics (all robust, no learning required):
  * shoulder_width_ratio   = |L_shoulder - R_shoulder| / |shoulder_mid - hip_mid|
                              ~1.3 front, drops sharply for side view
  * hip_width_ratio        = |L_hip - R_hip|         / |shoulder_mid - hip_mid|
                              ~0.9 front, drops for side view
  * shoulder_dx_share      = |L_shoulder.x - R_shoulder.x| / shoulder_distance
                              ~1.0 frontal (shoulders are horizontal),
                              ~0.0 side (one shoulder hides behind the other)

Output: per-video median of these, plus a guessed view label.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pose_schema import (  # noqa: E402
    LEFT_HIP, LEFT_SHOULDER, RIGHT_HIP, RIGHT_SHOULDER, NUM_JOINTS, landmark_columns,
)


def load(csv_path: Path):
    df = pd.read_csv(csv_path)
    cols = landmark_columns()
    poses = df[cols].to_numpy(dtype=np.float32).reshape(len(df), NUM_JOINTS, 3)
    vid = str(df["video_id"].iloc[0])
    return vid, poses


def stats(poses: np.ndarray, min_score: float = 0.3) -> dict:
    # poses: (T, V, 3) where channel 2 is score
    ls = poses[:, LEFT_SHOULDER]
    rs = poses[:, RIGHT_SHOULDER]
    lh = poses[:, LEFT_HIP]
    rh = poses[:, RIGHT_HIP]
    score_ok = (
        (ls[:, 2] > min_score) & (rs[:, 2] > min_score) &
        (lh[:, 2] > min_score) & (rh[:, 2] > min_score)
    )
    if not score_ok.any():
        return {"frames": 0}

    ls, rs, lh, rh = ls[score_ok], rs[score_ok], lh[score_ok], rh[score_ok]
    shoulder_mid = (ls[:, :2] + rs[:, :2]) * 0.5
    hip_mid = (lh[:, :2] + rh[:, :2]) * 0.5
    torso_len = np.linalg.norm(shoulder_mid - hip_mid, axis=1)
    torso_len = np.maximum(torso_len, 1e-3)

    shoulder_dist = np.linalg.norm(ls[:, :2] - rs[:, :2], axis=1)
    hip_dist = np.linalg.norm(lh[:, :2] - rh[:, :2], axis=1)

    # share of shoulder vector that is horizontal (x) - frontal => high
    shoulder_dx = np.abs(ls[:, 0] - rs[:, 0])
    horiz_share = shoulder_dx / np.maximum(shoulder_dist, 1e-3)

    return {
        "frames": int(score_ok.sum()),
        "shoulder_ratio": float(np.median(shoulder_dist / torso_len)),
        "hip_ratio": float(np.median(hip_dist / torso_len)),
        "horiz_share": float(np.median(horiz_share)),
    }


def guess_view(s: dict) -> str:
    if s.get("frames", 0) < 10:
        return "unknown"
    # Thresholds tuned for COCO-17 normal standing poses. Side view -> shoulder
    # ratio drops because shoulders project closer together in 2D.
    sr = s["shoulder_ratio"]
    if sr >= 0.90:
        return "front"
    if sr <= 0.55:
        return "side"
    return "angled"


def main() -> None:
    raw = ROOT / "data" / "raw"
    labels_path = ROOT / "data" / "labels" / "labels.csv"
    labels = pd.read_csv(labels_path, comment="#")

    print(f"{'video':10s}  {'frames':>7s}  {'sh_ratio':>9s}  {'hip_ratio':>10s}  {'horiz':>6s}  view     labels  per-class")
    print("-" * 100)
    rows = []
    for csv_path in sorted(raw.glob("*.pose.csv")):
        vid, poses = load(csv_path)
        s = stats(poses)
        view = guess_view(s)
        n_labels = int((labels["video_id"] == vid).sum())
        per_cls = labels[labels["video_id"] == vid]["label"].value_counts().to_dict()
        rows.append({"video_id": vid, "view": view, **s, "n_labels": n_labels})
        per_cls_str = " ".join(f"{k[:4]}:{v}" for k, v in per_cls.items())
        print(f"{vid:10s}  {s.get('frames', 0):7d}  "
              f"{s.get('shoulder_ratio', 0):9.3f}  "
              f"{s.get('hip_ratio', 0):10.3f}  "
              f"{s.get('horiz_share', 0):6.3f}  "
              f"{view:8s}  {n_labels:4d}   {per_cls_str}")

    # cluster summary
    print("\nView grouping:")
    df = pd.DataFrame(rows)
    for v in ["front", "angled", "side", "unknown"]:
        sub = df[df["view"] == v]
        if not sub.empty:
            print(f"  {v:8s}: {list(sub['video_id'])}  (total labels = {int(sub['n_labels'].sum())})")


if __name__ == "__main__":
    main()
