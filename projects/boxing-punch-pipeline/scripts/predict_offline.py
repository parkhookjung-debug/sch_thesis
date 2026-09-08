"""Run the canonical SmallSTGCN model on the existing MMPose-extracted CSVs.

This isolates the model+canonical pipeline from the rtmlib live path. If
accuracy here matches LOVO (~75%), the model is fine and the realtime app
problem is in the pose-extraction path (rtmlib output not matching MMPose).
"""
from __future__ import annotations

import sys
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pose_schema import NUM_JOINTS, landmark_columns  # noqa: E402
from preprocessing import canonicalize_facing, normalize_pose_sequence  # noqa: E402
from punch_event import resample_pose_sequence  # noqa: E402
from small_stgcn import SmallSTGCN  # noqa: E402


def load_pose(csv_path: Path):
    df = pd.read_csv(csv_path)
    vid = str(df["video_id"].iloc[0])
    frames = df["frame_index"].to_numpy(dtype=np.int64)
    poses = df[landmark_columns()].to_numpy(dtype=np.float32).reshape(len(df), NUM_JOINTS, 3)
    return vid, frames, poses


def main():
    ckpt = torch.load(ROOT / "models" / "small" / "best_canonical.pt", map_location="cuda", weights_only=False)
    classes = ckpt["classes"]
    model = SmallSTGCN(
        in_channels=ckpt["in_channels"], num_classes=len(classes),
        dropout=ckpt["dropout"], base_channels=ckpt["base_channels"],
    )
    model.load_state_dict(ckpt["model_state"])
    model.to("cuda").eval()
    print(f"Model: SmallSTGCN  LOVO mean reported = {ckpt['lovo_mean']:.3f}")

    labels = pd.read_csv(ROOT / "data" / "labels" / "labels.csv", comment="#")
    raw_dir = ROOT / "data" / "raw"
    window_size = 32
    context = 4

    correct = 0
    total = 0
    per_class = defaultdict(lambda: [0, 0])  # [correct, total]
    confused = Counter()
    for csv_path in sorted(raw_dir.glob("*.pose.csv")):
        vid, frames, poses = load_pose(csv_path)
        vlabels = labels[labels["video_id"] == vid]
        for row in vlabels.itertuples(index=False):
            s = int(row.start_frame) - context
            e = int(row.end_frame) + context
            i_s = max(0, int(np.searchsorted(frames, s, side="left")))
            i_e = min(len(poses) - 1, int(np.searchsorted(frames, e, side="right")) - 1)
            if i_e <= i_s:
                continue
            seg = poses[i_s:i_e + 1]
            window = canonicalize_facing(normalize_pose_sequence(resample_pose_sequence(seg, window_size)))
            x = torch.from_numpy(np.transpose(window, (2, 0, 1))[None]).to("cuda")
            with torch.no_grad():
                probs = torch.softmax(model(x), dim=1).cpu().numpy()[0]
            pred_idx = int(probs.argmax())
            pred = classes[pred_idx]
            true = str(row.label)
            ok = pred == true
            correct += int(ok)
            total += 1
            per_class[true][1] += 1
            per_class[true][0] += int(ok)
            if not ok:
                confused[f"{true}->{pred}"] += 1

    print(f"\nOffline-from-CSV inference on labeled events:")
    print(f"  total events: {total}   accuracy: {correct/max(1,total):.3f}")
    print("\n  per-class recall:")
    for cls in classes:
        c, t = per_class[cls]
        print(f"    {cls:9s} {c:3d}/{t:3d}  {(c/max(1,t)):.3f}")
    print("\n  top confusions:")
    for k, v in confused.most_common(8):
        print(f"    {k:20s}  {v}")


if __name__ == "__main__":
    main()
