from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from preprocessing import load_pose_csv
from punch_event import PunchEventDetector


def detect_one(csv_path: Path, args: argparse.Namespace) -> list[dict[str, object]]:
    video_id, frames, poses = load_pose_csv(csv_path)
    detector = PunchEventDetector(
        start_threshold=args.start_threshold,
        end_threshold=args.end_threshold,
        min_event_frames=args.min_event_frames,
        max_event_frames=args.max_event_frames,
        pre_roll=args.pre_roll,
        cooldown_frames=args.cooldown_frames,
        smooth=args.event_smooth,
        fall_ratio=args.fall_ratio,
    )

    rows = []
    for pose in poses:
        event, _ = detector.update(pose)
        if event is None:
            continue
        start_idx = max(0, min(len(frames) - 1, event.start_frame))
        apex_idx = max(0, min(len(frames) - 1, event.apex_frame))
        end_idx = max(0, min(len(frames) - 1, event.end_frame))
        rows.append(
            {
                "video_id": video_id,
                "start_frame": int(frames[start_idx]),
                "apex_frame": int(frames[apex_idx]),
                "end_frame": int(frames[end_idx]),
                "peak_energy": round(event.peak_energy, 6),
                "active_side": event.active_side,
                "duration_frames": len(event.poses),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract automatic punch event start/apex/end candidates.")
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--start-threshold", type=float, default=0.17)
    parser.add_argument("--end-threshold", type=float, default=0.09)
    parser.add_argument("--min-event-frames", type=int, default=5)
    parser.add_argument("--max-event-frames", type=int, default=28)
    parser.add_argument("--pre-roll", type=int, default=5)
    parser.add_argument("--cooldown-frames", type=int, default=7)
    parser.add_argument("--event-smooth", type=float, default=0.35)
    parser.add_argument("--fall-ratio", type=float, default=0.45)
    args = parser.parse_args()

    rows = []
    for csv_path in sorted(args.raw_dir.glob("*.pose.csv")):
        rows.extend(detect_one(csv_path, args))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "video_id",
        "start_frame",
        "apex_frame",
        "end_frame",
        "peak_energy",
        "active_side",
        "duration_frames",
    ]
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {args.output} ({len(rows)} events)")


if __name__ == "__main__":
    main()
