"""Build event dataset using APEX-CENTERED fixed-length windows.

Window definition: exactly `window_size` frames, with the apex frame placed
at index `apex_offset` (default = window_size // 2). No temporal resampling.

This way the model trains on windows that have the punch peak at a fixed
position. At inference, we build the same shape window from a rolling buffer
centered on the detector's detected apex, which removes the temporal-warp
mismatch between training (label start/end) and inference (detector cutoffs).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pose_schema import NUM_JOINTS, landmark_columns, CLASS_NAMES  # noqa: E402
from preprocessing import canonicalize_facing, normalize_pose_sequence  # noqa: E402


def apex_window(poses: np.ndarray, frames: np.ndarray, apex_frame: int,
                window_size: int, apex_offset: int) -> np.ndarray | None:
    apex_idx = int(np.searchsorted(frames, apex_frame, side="left"))
    if apex_idx >= len(poses):
        apex_idx = len(poses) - 1
    start = apex_idx - apex_offset
    end = start + window_size
    if start < 0 or end > len(poses):
        # pad by clamping (replicate edge frames)
        clamped = np.empty((window_size, NUM_JOINTS, poses.shape[-1]), dtype=poses.dtype)
        for i in range(window_size):
            src = max(0, min(len(poses) - 1, start + i))
            clamped[i] = poses[src]
        return clamped
    return poses[start:end]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw_rtmlib")
    ap.add_argument("--labels", type=Path, default=ROOT / "data" / "labels" / "labels.csv")
    ap.add_argument("--output", type=Path, default=ROOT / "data" / "processed" / "apex_events_rtmlib.npz")
    ap.add_argument("--window-size", type=int, default=32)
    ap.add_argument("--apex-offset", type=int, default=16,
                    help="Index within the window where the apex frame is placed (default = window_size/2).")
    ap.add_argument("--shift-radius", type=int, default=3,
                    help="Generate this many shifted copies on each side per label (training augmentation).")
    args = ap.parse_args()

    labels = pd.read_csv(args.labels, comment="#")
    classes = [c for c in CLASS_NAMES if c != "none" or (labels["label"] == "none").any()]
    class_to_idx = {c: i for i, c in enumerate(classes)}

    X, y, meta = [], [], []
    for csv_path in sorted(args.raw_dir.glob("*.pose.csv")):
        df = pd.read_csv(csv_path)
        video_id = str(df["video_id"].iloc[0])
        frames = df["frame_index"].to_numpy(dtype=np.int64)
        poses = df[landmark_columns()].to_numpy(dtype=np.float32).reshape(len(df), NUM_JOINTS, 3)
        vlabels = labels[labels["video_id"] == video_id]
        for row in vlabels.itertuples(index=False):
            label = str(row.label)
            if label not in class_to_idx:
                continue
            apex_frame = int(row.apex_frame)
            # temporal jitter: shift apex position +/- shift_radius
            shifts = range(-args.shift_radius, args.shift_radius + 1) if args.shift_radius > 0 else [0]
            for shift in shifts:
                w = apex_window(poses, frames, apex_frame + shift,
                                args.window_size, args.apex_offset)
                if w is None:
                    continue
                w = canonicalize_facing(normalize_pose_sequence(w))
                X.append(np.transpose(w, (2, 0, 1)))
                y.append(class_to_idx[label])
                meta.append({
                    "video_id": video_id,
                    "apex_frame": apex_frame,
                    "shift": shift,
                    "label": label,
                })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        X=np.asarray(X, dtype=np.float32),
        y=np.asarray(y, dtype=np.int64),
        classes=np.asarray(classes),
        meta=np.asarray([json.dumps(m, ensure_ascii=True) for m in meta]),
    )
    print(f"Wrote {args.output}")
    print(f"  total samples: {len(X)}")
    print(f"  per-class: {dict(zip(classes, np.bincount(y, minlength=len(classes)).tolist()))}")


if __name__ == "__main__":
    main()
