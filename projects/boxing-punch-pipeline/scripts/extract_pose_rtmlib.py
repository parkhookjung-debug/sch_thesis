"""Extract per-frame COCO-17 pose CSVs using rtmlib RTMPose-M on the GPU.

Output schema is identical to extract_pose.py (MMPose-based), so the rest of
the pipeline (preprocess_events.py, train_small.py, predict, ...) works
unchanged. The key reason to do this is consistency: the realtime app also
uses rtmlib RTMPose-M, so training and inference share the exact same pose
distribution.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuda_setup  # noqa: F401
from pose_schema import NUM_JOINTS, landmark_columns  # noqa: E402


def pick_primary(kps: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if len(kps) == 1:
        return kps[0], scores[0]
    areas = []
    for k in kps:
        x0, y0 = k[:, 0].min(), k[:, 1].min()
        x1, y1 = k[:, 0].max(), k[:, 1].max()
        areas.append(float((x1 - x0) * (y1 - y0)))
    i = int(np.argmax(areas))
    return kps[i], scores[i]


def extract_one(video_path: Path, out_csv: Path, body, max_frames: int | None) -> None:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  skip {video_path.name}: cannot open")
        return
    n_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    n_target = n_total if max_frames is None else min(n_total, max_frames)

    rows = []
    columns = ["video_id", "frame_index"] + landmark_columns()
    video_id = video_path.stem  # "LIM 1"

    for frame_i in range(n_target):
        ok, frame = cap.read()
        if not ok:
            break
        kps, scores = body(frame)
        if len(kps) == 0:
            kp = np.zeros((NUM_JOINTS, 2), dtype=np.float32)
            sc = np.zeros(NUM_JOINTS, dtype=np.float32)
        else:
            kp, sc = pick_primary(kps, scores)
        row = [video_id, frame_i]
        for j in range(NUM_JOINTS):
            row.append(float(kp[j, 0]))
            row.append(float(kp[j, 1]))
            row.append(float(sc[j]))
        rows.append(row)
        if (frame_i + 1) % 200 == 0:
            print(f"    {frame_i+1}/{n_target} frames", flush=True)

    cap.release()
    df = pd.DataFrame(rows, columns=columns)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"  -> {out_csv}  ({len(df)} frames)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=ROOT / "videos")
    ap.add_argument("--output", type=Path, default=ROOT / "data" / "raw_rtmlib")
    ap.add_argument("--mode", default="balanced", choices=["lightweight", "balanced", "performance"])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--patterns", nargs="+", default=["*.mp4", "*.mov", "*.avi", "*.mkv"])
    args = ap.parse_args()

    from rtmlib import Body
    body = Body(mode=args.mode, to_openpose=False, backend="onnxruntime", device=args.device)
    print(f"Pose model: rtmlib Body (mode={args.mode}, device={args.device})")

    videos: list[Path] = []
    for pat in args.patterns:
        videos.extend(sorted(args.input.glob(pat)))
    print(f"Found {len(videos)} videos in {args.input}")
    for v in videos:
        out_csv = args.output / f"{v.stem}.pose.csv"
        if out_csv.exists():
            print(f"  exists, skip: {out_csv.name}")
            continue
        print(f"Extracting {v.name} ...")
        extract_one(v, out_csv, body, args.max_frames)


if __name__ == "__main__":
    main()
