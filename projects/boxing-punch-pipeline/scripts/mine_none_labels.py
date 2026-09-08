"""Auto-mine 'none' labels from rest periods between labeled punches.

For each video:
  * Load the pose CSV.
  * Find frame gaps between consecutive labeled punches AND the head/tail of the
    video that are at least `--min-gap` frames wide.
  * Inside each gap, pick the lowest-motion contiguous `--window` frames and add
    one `none` label for that window.

This produces realistic guard/rest negatives without manual labeling. The user
can review them after with label_video.py and drop bad ones.

Original labels.csv is backed up to data/labels/backups before writing.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pose_schema import NUM_JOINTS, landmark_columns  # noqa: E402
from punch_event import (  # noqa: E402
    LEFT_WRIST,
    RIGHT_WRIST,
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
)


def load_pose(csv_path: Path) -> tuple[str, np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path)
    video_id = str(df["video_id"].iloc[0])
    frames = df["frame_index"].to_numpy(dtype=np.int64)
    cols = landmark_columns()
    poses = df[cols].to_numpy(dtype=np.float32).reshape(len(df), NUM_JOINTS, 3)
    return video_id, frames, poses


def per_frame_energy(poses: np.ndarray) -> np.ndarray:
    """Wrist-motion energy normalized by shoulder width. Low => idle."""
    if len(poses) < 2:
        return np.zeros(len(poses), dtype=np.float32)
    shoulder = np.linalg.norm(
        poses[:, LEFT_SHOULDER, :2] - poses[:, RIGHT_SHOULDER, :2], axis=1
    )
    scale = np.maximum(shoulder, 1.0)
    lw = poses[:, LEFT_WRIST, :2]
    rw = poses[:, RIGHT_WRIST, :2]
    lw_speed = np.linalg.norm(np.diff(lw, axis=0), axis=1)
    rw_speed = np.linalg.norm(np.diff(rw, axis=0), axis=1)
    energy = np.maximum(lw_speed, rw_speed) / scale[:-1]
    return np.concatenate([[0.0], energy]).astype(np.float32)


def lowest_motion_window(
    energy: np.ndarray,
    start: int,
    end: int,
    window: int,
) -> tuple[int, int, float] | None:
    """Return (best_start, best_end, mean_energy) inside [start, end)."""
    if end - start < window:
        return None
    seg = energy[start:end]
    # cumulative sum trick for rolling mean
    cs = np.concatenate([[0.0], np.cumsum(seg)])
    means = (cs[window:] - cs[:-window]) / window
    best_off = int(np.argmin(means))
    best_start = start + best_off
    return best_start, best_start + window, float(means[best_off])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    p.add_argument("--labels", type=Path, default=ROOT / "data" / "labels" / "labels.csv")
    p.add_argument("--out-labels", type=Path, default=None,
                   help="Defaults to overwriting --labels (with backup).")
    p.add_argument("--window", type=int, default=32,
                   help="Frame length of each none segment (match event window).")
    p.add_argument("--min-gap", type=int, default=40,
                   help="Required gap between adjacent punches to mine from.")
    p.add_argument("--padding", type=int, default=8,
                   help="Frames to keep clear of any adjacent punch.")
    p.add_argument("--max-per-video", type=int, default=20,
                   help="Cap mined none segments per video to avoid imbalance.")
    p.add_argument("--max-energy", type=float, default=0.06,
                   help="Reject windows whose mean energy exceeds this (motion is too high).")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be added without writing.")
    args = p.parse_args()

    labels = pd.read_csv(args.labels, comment="#")
    print(f"Loaded {len(labels)} existing labels from {args.labels}")
    print("  per-class:", labels["label"].value_counts().to_dict())

    new_rows: list[dict] = []
    for csv_path in sorted(args.raw_dir.glob("*.pose.csv")):
        video_id, frames, poses = load_pose(csv_path)
        energy = per_frame_energy(poses)

        video_labels = labels[labels["video_id"] == video_id].sort_values("start_frame")
        # build occupied intervals (in frame-number space) with padding
        occupied: list[tuple[int, int]] = []
        for row in video_labels.itertuples(index=False):
            occupied.append((int(row.start_frame) - args.padding, int(row.end_frame) + args.padding))

        # candidate gaps in frame-number space
        first_frame = int(frames[0])
        last_frame = int(frames[-1])
        gaps: list[tuple[int, int]] = []
        cursor = first_frame
        for s, e in occupied:
            if s > cursor:
                gaps.append((cursor, s))
            cursor = max(cursor, e)
        if cursor < last_frame:
            gaps.append((cursor, last_frame))

        # map frame-number gaps to row indices in `frames`
        added_here: list[dict] = []
        for gap_s, gap_e in gaps:
            if gap_e - gap_s < args.min_gap:
                continue
            i_s = int(np.searchsorted(frames, gap_s, side="left"))
            i_e = int(np.searchsorted(frames, gap_e, side="right"))
            picked = lowest_motion_window(energy, i_s, i_e, args.window)
            if picked is None:
                continue
            ws, we, mean_e = picked
            if mean_e > args.max_energy:
                continue
            start_frame = int(frames[ws])
            end_frame = int(frames[we - 1])
            apex_frame = int(frames[(ws + we - 1) // 2])
            added_here.append(
                dict(
                    video_id=video_id,
                    start_frame=start_frame,
                    apex_frame=apex_frame,
                    end_frame=end_frame,
                    label="none",
                    _energy=mean_e,
                )
            )

        # sort by energy ascending, keep cap
        added_here.sort(key=lambda r: r["_energy"])
        added_here = added_here[: args.max_per_video]
        for r in added_here:
            r.pop("_energy", None)
        new_rows.extend(added_here)
        print(f"  {video_id:8s}: {len(added_here):3d} none segments mined "
              f"(gaps={len([g for g in gaps if g[1]-g[0]>=args.min_gap])})")

    if not new_rows:
        print("No none segments produced. Try lowering --min-gap or raising --max-energy.")
        return

    print(f"\nTotal mined 'none' rows: {len(new_rows)}")
    if args.dry_run:
        print("Dry run — not writing.")
        for r in new_rows[:5]:
            print(" ", r)
        return

    out_path = args.out_labels or args.labels
    if out_path == args.labels:
        backups = args.labels.parent / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backups / f"labels_{stamp}_premine.csv"
        shutil.copy2(args.labels, backup_path)
        print(f"Backup -> {backup_path}")

    merged = pd.concat([labels, pd.DataFrame(new_rows)], ignore_index=True)
    merged = merged.sort_values(["video_id", "start_frame"]).reset_index(drop=True)
    merged.to_csv(out_path, index=False)
    print(f"Wrote {len(merged)} labels -> {out_path}")
    print("  new per-class:", merged["label"].value_counts().to_dict())


if __name__ == "__main__":
    main()
