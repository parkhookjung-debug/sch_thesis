"""Run the EXACT realtime pipeline (rtmlib + PunchEventDetector + canonical
+ SmallSTGCN) on a recorded video file, no camera needed. Reports the
predicted-class distribution vs the labeled distribution for that video.

If the realtime path is healthy, predictions should roughly match the
LOVO accuracy of the held-out video. If predictions collapse to one
class (like 'all uppercut'), this script makes it instantly visible.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuda_setup  # noqa: F401
from pose_schema import NUM_JOINTS  # noqa: E402
from preprocessing import canonicalize_facing, normalize_pose_sequence  # noqa: E402
from punch_event import PunchEventDetector, extract_event_window  # noqa: E402
from small_stgcn import SmallSTGCN  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path,
                    default=ROOT / "models" / "small" / "best_canonical.pt")
    ap.add_argument("--threshold", type=float, default=0.45)
    ap.add_argument("--margin", type=float, default=0.04)
    ap.add_argument("--window-size", type=int, default=32)
    ap.add_argument("--pose-mode", default="balanced")
    ap.add_argument("--max-frames", type=int, default=None)
    args = ap.parse_args()

    ckpt = torch.load(args.checkpoint, map_location="cuda", weights_only=False)
    classes = ckpt["classes"]
    model = SmallSTGCN(
        in_channels=ckpt["in_channels"], num_classes=len(classes),
        dropout=ckpt["dropout"], base_channels=ckpt["base_channels"],
    )
    model.load_state_dict(ckpt["model_state"])
    model.to("cuda").eval()
    print(f"Model loaded: SmallSTGCN  classes={classes}")

    from rtmlib import Body
    body = Body(mode=args.pose_mode, to_openpose=False, backend="onnxruntime", device="cuda")
    print(f"Pose: rtmlib Body (mode={args.pose_mode})")

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open {args.video}")
    print(f"Video: {args.video}  fps={cap.get(cv2.CAP_PROP_FPS):.1f}  "
          f"frames={int(cap.get(cv2.CAP_PROP_FRAME_COUNT))}")

    detector = PunchEventDetector()
    predictions: list[tuple[int, str, float, dict]] = []

    frame_i = -1
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_i += 1
        if args.max_frames and frame_i >= args.max_frames:
            break

        kps, scores = body(frame)
        if len(kps) == 0:
            pose = np.zeros((NUM_JOINTS, 3), dtype=np.float32)
        else:
            best = int(np.argmax([(k[:, 0].max() - k[:, 0].min()) * (k[:, 1].max() - k[:, 1].min()) for k in kps]))
            pose = np.concatenate([kps[best][:, :2], scores[best][:, None]], axis=1).astype(np.float32)

        event, _ = detector.update(pose)
        if event is None:
            continue
        window = extract_event_window(event, args.window_size)
        window = canonicalize_facing(normalize_pose_sequence(window))
        x = torch.from_numpy(np.transpose(window, (2, 0, 1))[None]).to("cuda")
        with torch.no_grad():
            probs = torch.softmax(model(x), dim=1).cpu().numpy()[0]
        pred = classes[int(probs.argmax())]
        predictions.append((
            event.apex_frame,
            pred,
            float(probs.max()),
            dict(zip(classes, [round(float(v), 3) for v in probs])),
        ))

    cap.release()

    if not predictions:
        print("No punch events detected. Adjust event-detector thresholds.")
        return

    print(f"\nDetected events: {len(predictions)}")
    counts = Counter(p[1] for p in predictions)
    print("Predicted distribution:")
    for c in classes:
        print(f"  {c:9s}  {counts.get(c, 0):3d}  ({counts.get(c, 0)/len(predictions)*100:.1f}%)")

    # If labels exist for this video, compare
    video_id = args.video.stem  # "LIM 1"
    labels_path = ROOT / "data" / "labels" / "labels.csv"
    if labels_path.exists():
        labels = pd.read_csv(labels_path, comment="#")
        vlabels = labels[labels["video_id"] == video_id]
        if not vlabels.empty:
            true_counts = vlabels["label"].value_counts().to_dict()
            print(f"\nTrue label distribution for {video_id}:")
            for c in classes:
                print(f"  {c:9s}  {true_counts.get(c, 0):3d}")

    # Show first 12 events in detail
    print("\nFirst 12 events (apex_frame -> pred  conf  probs):")
    for apex, pred, conf, probs in predictions[:12]:
        print(f"  f={apex:5d}  {pred:9s}  conf={conf:.2f}  {probs}")


if __name__ == "__main__":
    main()
