"""Use the pre-extracted MMPose CSV as input but build windows with the
PunchEventDetector (the realtime path). Isolates window-construction issues
from pose-extraction issues.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pose_schema import NUM_JOINTS, landmark_columns  # noqa: E402
from preprocessing import canonicalize_facing, normalize_pose_sequence  # noqa: E402
from punch_event import PunchEventDetector, extract_event_window  # noqa: E402
from small_stgcn import SmallSTGCN  # noqa: E402


def main():
    video_id = "LIM 1"
    csv_path = ROOT / "data" / "raw" / f"{video_id}.pose.csv"

    df = pd.read_csv(csv_path)
    poses = df[landmark_columns()].to_numpy(dtype=np.float32).reshape(len(df), NUM_JOINTS, 3)

    ckpt = torch.load(ROOT / "models" / "small" / "best_canonical.pt", map_location="cuda", weights_only=False)
    classes = ckpt["classes"]
    model = SmallSTGCN(
        in_channels=ckpt["in_channels"], num_classes=len(classes),
        dropout=ckpt["dropout"], base_channels=ckpt["base_channels"],
    )
    model.load_state_dict(ckpt["model_state"]); model.to("cuda").eval()

    detector = PunchEventDetector()
    predictions = []
    for pose in poses:
        event, _ = detector.update(pose)
        if event is None:
            continue
        window = extract_event_window(event, 32)
        window = canonicalize_facing(normalize_pose_sequence(window))
        x = torch.from_numpy(np.transpose(window, (2, 0, 1))[None]).to("cuda")
        with torch.no_grad():
            probs = torch.softmax(model(x), dim=1).cpu().numpy()[0]
        predictions.append((event.apex_frame, classes[int(probs.argmax())], float(probs.max()),
                            dict(zip(classes, [round(float(v), 3) for v in probs]))))

    print(f"Source: MMPose CSV for {video_id}")
    print(f"Window: PunchEventDetector (realtime style, with post_roll)")
    print(f"Detected events: {len(predictions)}")
    counts = Counter(p[1] for p in predictions)
    print("Predicted distribution:")
    for c in classes:
        print(f"  {c:9s}  {counts.get(c, 0):3d}")

    labels = pd.read_csv(ROOT / "data" / "labels" / "labels.csv", comment="#")
    vlabels = labels[labels["video_id"] == video_id]
    print(f"\nTrue distribution: {vlabels['label'].value_counts().to_dict()}")

    print("\nFirst 14 events:")
    for apex, pred, conf, probs in predictions[:14]:
        # find which true labels overlap
        nearby = vlabels[(vlabels["apex_frame"].between(apex - 8, apex + 8))]
        true = ",".join(nearby["label"].tolist()) if not nearby.empty else "?"
        ok = "OK " if pred in true else "BAD"
        print(f"  {ok} f={apex:5d}  pred={pred:9s} (conf={conf:.2f})  true_near=[{true}]  {probs}")


if __name__ == "__main__":
    main()
