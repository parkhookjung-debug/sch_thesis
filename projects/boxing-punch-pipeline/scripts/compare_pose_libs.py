"""Compare rtmlib pose output vs the stored MMPose CSV pose on the same frame.

We pick LIM 1 at the apex frame of a known labeled punch, extract that exact
frame from the .mp4, run rtmlib Body on it, and compare the resulting 17
COCO keypoints (and the active wrist trajectory across the punch window) to
what MMPose wrote to the pose CSV during training.

If joint order or coordinate convention differs, this prints the smoking gun.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuda_setup  # noqa: F401
from pose_schema import NUM_JOINTS, landmark_columns, COCO_POSE_LANDMARKS  # noqa: E402


def main():
    video_path = ROOT / "videos" / "LIM 1.mp4"
    csv_path = ROOT / "data" / "raw" / "LIM 1.pose.csv"
    target_frame = 30  # apex of first labeled jab (16..30)

    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit(f"Could not read frame {target_frame} from {video_path}")
    print(f"Frame shape: {frame.shape}  (target_frame={target_frame})")

    # ---- MMPose stored CSV ----
    df = pd.read_csv(csv_path)
    row = df[df["frame_index"] == target_frame].iloc[0]
    mm_pose = np.array(row[landmark_columns()].tolist(), dtype=np.float32).reshape(NUM_JOINTS, 3)

    # ---- rtmlib live extraction ----
    from rtmlib import Body
    body = Body(mode="balanced", to_openpose=False, backend="onnxruntime", device="cuda")
    kps, scores = body(frame)
    if len(kps) == 0:
        raise SystemExit("rtmlib detected no person")
    # pick largest
    best = int(np.argmax([(k[:, 0].max() - k[:, 0].min()) * (k[:, 1].max() - k[:, 1].min()) for k in kps]))
    rt_pose = np.concatenate([kps[best][:, :2], scores[best][:, None]], axis=1).astype(np.float32)

    # ---- side-by-side print ----
    print(f"\n{'joint':18s}  {'MMPose (x,y,s)':>30s}  {'rtmlib (x,y,s)':>30s}  {'dx':>8s} {'dy':>8s}")
    print("-" * 110)
    for i, name in enumerate(COCO_POSE_LANDMARKS):
        mm = mm_pose[i]
        rt = rt_pose[i]
        dx = float(rt[0] - mm[0])
        dy = float(rt[1] - mm[1])
        print(f"{name:18s}  ({mm[0]:7.1f},{mm[1]:7.1f},{mm[2]:.2f})  "
              f"({rt[0]:7.1f},{rt[1]:7.1f},{rt[2]:.2f})  {dx:8.1f} {dy:8.1f}")

    # ---- summary statistics ----
    xy_diff = np.linalg.norm(rt_pose[:, :2] - mm_pose[:, :2], axis=1)
    print(f"\nKeypoint position diff (pixels):")
    print(f"  median = {np.median(xy_diff):.2f}")
    print(f"  mean   = {np.mean(xy_diff):.2f}")
    print(f"  max    = {np.max(xy_diff):.2f}  at joint '{COCO_POSE_LANDMARKS[int(np.argmax(xy_diff))]}'")

    print(f"\nScore range:")
    print(f"  MMPose: min={mm_pose[:, 2].min():.3f}  max={mm_pose[:, 2].max():.3f}  mean={mm_pose[:, 2].mean():.3f}")
    print(f"  rtmlib: min={rt_pose[:, 2].min():.3f}  max={rt_pose[:, 2].max():.3f}  mean={rt_pose[:, 2].mean():.3f}")

    # Check if rtmlib gives the joint order we expect
    # Heuristic: in a normally-standing person, nose.y < shoulder.y < hip.y < knee.y < ankle.y
    print(f"\nRtmlib joint-order sanity (y should grow head->ankle):")
    for i, name in enumerate(["nose", "left_shoulder", "left_hip", "left_knee", "left_ankle"]):
        idx = COCO_POSE_LANDMARKS.index(name)
        print(f"  {name:14s} idx={idx}  rtmlib_y={rt_pose[idx, 1]:.1f}")


if __name__ == "__main__":
    main()
