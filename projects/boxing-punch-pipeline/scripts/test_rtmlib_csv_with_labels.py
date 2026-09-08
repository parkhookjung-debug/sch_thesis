"""rtmlib-extracted CSV + LABEL windows (training-style) + best_canonical model.

If this works well, the realtime collapse is purely a window-construction
issue (detector vs labels), not a pose-extractor mismatch.
If this also fails, the rtmlib pose noise itself is the problem.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pose_schema import NUM_JOINTS, landmark_columns  # noqa: E402
from preprocessing import canonicalize_facing, normalize_pose_sequence  # noqa: E402
from punch_event import resample_pose_sequence  # noqa: E402
from small_stgcn import SmallSTGCN  # noqa: E402


def main():
    ckpt = torch.load(ROOT / "models" / "small" / "best_canonical.pt", map_location="cuda", weights_only=False)
    classes = ckpt["classes"]
    model = SmallSTGCN(in_channels=ckpt["in_channels"], num_classes=len(classes),
                       dropout=ckpt["dropout"], base_channels=ckpt["base_channels"])
    model.load_state_dict(ckpt["model_state"]); model.to("cuda").eval()

    labels = pd.read_csv(ROOT / "data" / "labels" / "labels.csv", comment="#")
    raw_dir = ROOT / "data" / "raw_rtmlib"
    context = 4
    window_size = 32

    per_video = defaultdict(lambda: [0, 0, Counter()])
    grand_correct = 0
    grand_total = 0
    for csv_path in sorted(raw_dir.glob("*.pose.csv")):
        df = pd.read_csv(csv_path)
        vid = str(df["video_id"].iloc[0])
        frames = df["frame_index"].to_numpy(dtype=np.int64)
        poses = df[landmark_columns()].to_numpy(dtype=np.float32).reshape(len(df), NUM_JOINTS, 3)
        vlabels = labels[labels["video_id"] == vid]
        for row in vlabels.itertuples(index=False):
            s = max(0, int(row.start_frame) - context)
            e = min(len(poses) - 1, int(row.end_frame) + context)
            if e <= s:
                continue
            seg = poses[s:e + 1]
            window = canonicalize_facing(normalize_pose_sequence(resample_pose_sequence(seg, window_size)))
            x = torch.from_numpy(np.transpose(window, (2, 0, 1))[None]).to("cuda")
            with torch.no_grad():
                probs = torch.softmax(model(x), dim=1).cpu().numpy()[0]
            pred = classes[int(probs.argmax())]
            true = str(row.label)
            ok = pred == true
            per_video[vid][0] += int(ok)
            per_video[vid][1] += 1
            per_video[vid][2][pred] += 1
            grand_correct += int(ok)
            grand_total += 1

    print(f"\nModel: best_canonical (MMPose-trained)")
    print(f"Pose source: rtmlib CSV (data/raw_rtmlib)")
    print(f"Windows: label-based (training-style)\n")
    print(f"{'video':10s}  {'acc':>6s}  predicted distribution")
    for vid, (c, t, dist) in per_video.items():
        print(f"{vid:10s}  {c/max(1,t):.3f}  {dict(dist)}")
    print(f"\noverall accuracy: {grand_correct/max(1, grand_total):.3f}  ({grand_correct}/{grand_total})")


if __name__ == "__main__":
    main()
