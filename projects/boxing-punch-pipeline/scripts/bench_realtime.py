"""Headless benchmark: rtmlib RTMPose + SmallSTGCN end-to-end on GPU.

Synthesizes a fake 720p image, measures throughput of:
  (a) pose estimation per frame
  (b) classifier on a 32-frame window
  (c) full pipeline (per-frame pose + per-event classify) at synthetic 30fps
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cuda_setup  # noqa: F401
from pose_schema import NUM_JOINTS  # noqa: E402
from preprocessing import normalize_pose_sequence  # noqa: E402
from small_stgcn import SmallSTGCN  # noqa: E402


def banner(s: str) -> None:
    print("\n" + "=" * 60); print(s); print("=" * 60)


def make_fake_frame(h=720, w=1280) -> np.ndarray:
    """Synthetic image with a vaguely person-shaped blob, just to feed the detector."""
    img = np.full((h, w, 3), 32, dtype=np.uint8)
    cx, cy = w // 2, h // 2
    import cv2
    cv2.ellipse(img, (cx, cy - 100), (50, 70), 0, 0, 360, (200, 180, 160), -1)  # head
    cv2.rectangle(img, (cx - 80, cy - 30), (cx + 80, cy + 150), (180, 150, 120), -1)  # torso
    cv2.rectangle(img, (cx - 100, cy + 150), (cx + 100, cy + 320), (60, 50, 90), -1)  # legs
    return img


def main() -> None:
    banner("1. Load SmallSTGCN")
    ckpt_path = ROOT / "models" / "small" / "best_lovo_final.pt"
    ckpt = torch.load(ckpt_path, map_location="cuda", weights_only=False)
    classes = [str(c) for c in ckpt["classes"]]
    device = torch.device("cuda")
    model = SmallSTGCN(
        in_channels=int(ckpt["in_channels"]),
        num_classes=len(classes),
        dropout=float(ckpt.get("dropout", 0.4)),
        base_channels=int(ckpt.get("base_channels", 32)),
    )
    model.load_state_dict(ckpt["model_state"])
    model.to(device).eval()
    print(f"  classes={classes}  params={sum(p.numel() for p in model.parameters()):,}")

    banner("2. Init rtmlib RTMPose on CUDA (first call downloads model)")
    from rtmlib import Body
    t0 = time.perf_counter()
    pose = Body(mode="balanced", to_openpose=False, backend="onnxruntime", device="cuda")
    print(f"  init+download: {time.perf_counter()-t0:.1f}s")

    frame = make_fake_frame()

    banner("3. Warm up + pose throughput")
    for _ in range(5):
        pose(frame)
    t0 = time.perf_counter()
    n = 60
    for _ in range(n):
        kps, scores = pose(frame)
    dt = time.perf_counter() - t0
    print(f"  pose only: {dt*1000/n:.1f} ms/frame  ({n/dt:.1f} FPS)")
    if len(kps):
        print(f"  detected {len(kps)} person(s), keypoints shape={kps[0].shape}")

    banner("4. Classifier throughput on a 32-frame window")
    window = np.random.randn(32, NUM_JOINTS, 3).astype(np.float32) * 0.3
    window = normalize_pose_sequence(window)
    x = torch.from_numpy(np.transpose(window, (2, 0, 1))[None]).to(device)
    for _ in range(20):
        _ = model(x)
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    n = 500
    for _ in range(n):
        _ = model(x)
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    print(f"  classify: {dt*1000/n:.2f} ms/window  ({n/dt:.0f} events/s)")

    banner("5. Full pipeline budget @30fps (33.3 ms / frame)")
    t0 = time.perf_counter()
    n = 60
    for i in range(n):
        kps, scores = pose(frame)
        # simulate classifying every 20 frames
        if i % 20 == 19:
            _ = model(x)
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    print(f"  end-to-end: {dt*1000/n:.1f} ms/frame  ({n/dt:.1f} FPS effective)")

    banner("DONE.  Real-time pipeline is GPU-accelerated.")


if __name__ == "__main__":
    main()
