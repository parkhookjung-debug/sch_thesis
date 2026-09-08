"""Build training NPZ using EXACTLY the same window shape as the realtime
PunchEventDetector. For each labeled punch, we find the detector event whose
apex frame is closest, and use that event's window as the training sample.

This eliminates the train-vs-inference window distribution mismatch which
otherwise causes the realtime model to collapse to one class.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pose_schema import NUM_JOINTS, landmark_columns, CLASS_NAMES  # noqa: E402
from preprocessing import canonicalize_facing, normalize_pose_sequence  # noqa: E402
from punch_event import PunchEventDetector, extract_event_window  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw_rtmlib")
    ap.add_argument("--labels", type=Path, default=ROOT / "data" / "labels" / "labels.csv")
    ap.add_argument("--output", type=Path, default=ROOT / "data" / "processed" / "boxing_punch_detector_events.npz")
    ap.add_argument("--window-size", type=int, default=32)
    ap.add_argument("--apex-tolerance", type=int, default=10,
                    help="Max distance (frames) between detector apex and labeled apex to count as a match.")
    args = ap.parse_args()

    labels = pd.read_csv(args.labels, comment="#")
    has_none = bool((labels["label"] == "none").any())
    class_names = CLASS_NAMES if has_none else [c for c in CLASS_NAMES if c != "none"]
    class_to_idx = {c: i for i, c in enumerate(class_names)}
    print(f"Classes: {class_names}")

    X, y, meta = [], [], []
    stats = Counter()

    for csv_path in sorted(args.raw_dir.glob("*.pose.csv")):
        df = pd.read_csv(csv_path)
        video_id = str(df["video_id"].iloc[0])
        frames = df["frame_index"].to_numpy(dtype=np.int64)
        poses = df[landmark_columns()].to_numpy(dtype=np.float32).reshape(len(df), NUM_JOINTS, 3)

        # 1. run the realtime detector on the full pose sequence
        detector = PunchEventDetector()
        events = []
        for pose in poses:
            ev, _ = detector.update(pose)
            if ev is not None:
                events.append(ev)
        print(f"  {video_id:10s}  poses={len(poses):4d}  detector_events={len(events)}")

        # 2. match each labeled punch to the closest detector event by apex frame
        vlabels = labels[labels["video_id"] == video_id]
        used_events = set()
        for row in vlabels.itertuples(index=False):
            label = str(row.label)
            if label not in class_to_idx:
                continue
            apex = int(row.apex_frame)
            best_i = -1
            best_dist = 10 ** 9
            for i, ev in enumerate(events):
                if i in used_events:
                    continue
                d = abs(int(ev.apex_frame) - apex)
                if d < best_dist:
                    best_dist = d
                    best_i = i
            if best_i < 0 or best_dist > args.apex_tolerance:
                stats[f"{video_id}:unmatched"] += 1
                continue
            ev = events[best_i]
            used_events.add(best_i)
            window = extract_event_window(ev, args.window_size)
            window = canonicalize_facing(normalize_pose_sequence(window))
            X.append(np.transpose(window, (2, 0, 1)))
            y.append(class_to_idx[label])
            meta.append({
                "video_id": video_id,
                "start_frame": int(ev.start_frame),
                "apex_frame": int(ev.apex_frame),
                "end_frame": int(ev.end_frame),
                "label": label,
                "label_apex": apex,
                "match_distance": int(best_dist),
            })
            stats[label] += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        X=np.asarray(X, dtype=np.float32),
        y=np.asarray(y, dtype=np.int64),
        classes=np.asarray(class_names),
        meta=np.asarray([json.dumps(m, ensure_ascii=True) for m in meta]),
    )
    print(f"\nWrote {args.output}")
    print(f"  total matched samples: {len(X)}")
    print(f"  per-class: {dict(stats)}")


if __name__ == "__main__":
    main()
