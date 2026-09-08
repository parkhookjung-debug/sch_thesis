"""Detect whether the boxer faces left or right of the camera, per video.

In hip-centered pose data:
  * if the active (jabbing) wrist tends to land on the +x side of the hip center,
    the boxer is facing toward +x  (e.g. camera sees their back-right side)
  * if it lands on -x, facing toward -x
A boxer's jab+cross both extend in the same direction (the lead direction).
If facing direction flips between videos, the model has to learn two mirrored
versions of every punch from a tiny dataset -- which is exactly the LOVO
variance signature we are seeing.

We measure: median x-coordinate of the active wrist at apex frame, per video,
restricted to jab and cross labels.
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
from punch_event import LEFT_WRIST, RIGHT_WRIST  # noqa: E402


def load_poses(csv_path: Path):
    df = pd.read_csv(csv_path)
    cols = landmark_columns()
    poses = df[cols].to_numpy(dtype=np.float32).reshape(len(df), NUM_JOINTS, 3)
    frames = df["frame_index"].to_numpy(dtype=np.int64)
    vid = str(df["video_id"].iloc[0])
    return vid, frames, poses


def hip_center(pose: np.ndarray) -> np.ndarray:
    return (pose[LEFT_HIP, :2] + pose[RIGHT_HIP, :2]) * 0.5


def shoulder_width(pose: np.ndarray) -> float:
    return float(max(1.0, np.linalg.norm(pose[LEFT_SHOULDER, :2] - pose[RIGHT_SHOULDER, :2])))


def main() -> None:
    raw = ROOT / "data" / "raw"
    labels = pd.read_csv(ROOT / "data" / "labels" / "labels.csv", comment="#")

    print(f"{'video':10s}  {'jab_dx':>7s}  {'cross_dx':>8s}  {'hook_dx':>7s}  {'upp_dx':>7s}  facing")
    print("-" * 70)
    rows = []
    for csv_path in sorted(raw.glob("*.pose.csv")):
        vid, frames, poses = load_poses(csv_path)
        frame_to_idx = {int(f): i for i, f in enumerate(frames)}
        vlabels = labels[labels["video_id"] == vid]

        per_class_dx = {"jab": [], "cross": [], "hook": [], "uppercut": []}
        for row in vlabels.itertuples(index=False):
            apex = int(row.apex_frame)
            idx = frame_to_idx.get(apex)
            if idx is None:
                idx = int(np.searchsorted(frames, apex, side="left"))
                if idx >= len(poses):
                    continue
            pose = poses[idx]
            hc = hip_center(pose)
            sw = shoulder_width(pose)
            # Use the wrist with larger displacement at apex (active hand)
            l_dx = (pose[LEFT_WRIST, 0] - hc[0]) / sw
            r_dx = (pose[RIGHT_WRIST, 0] - hc[0]) / sw
            active_dx = l_dx if abs(l_dx) > abs(r_dx) else r_dx
            if row.label in per_class_dx:
                per_class_dx[row.label].append(active_dx)

        meds = {k: (float(np.median(v)) if v else float("nan")) for k, v in per_class_dx.items()}
        # facing direction by sign of median jab/cross dx (straight punches are most reliable)
        straights = per_class_dx["jab"] + per_class_dx["cross"]
        if not straights:
            facing = "?"
        else:
            m = float(np.median(straights))
            facing = "+x (right)" if m > 0.05 else ("-x (left)" if m < -0.05 else "ambiguous")
        rows.append({"video_id": vid, "facing": facing, **meds})
        print(f"{vid:10s}  {meds['jab']:7.2f}  {meds['cross']:8.2f}  {meds['hook']:7.2f}  {meds['uppercut']:7.2f}  {facing}")

    print("\nFacing groups:")
    df = pd.DataFrame(rows)
    for f in sorted(df["facing"].unique()):
        sub = df[df["facing"] == f]
        print(f"  {f:14s}: {list(sub['video_id'])}")


if __name__ == "__main__":
    main()
