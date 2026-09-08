"""End-to-end GPU sanity check.

Confirms (a) CUDA compute actually runs on the device,
(b) the existing ST-GCN model and NPZ dataset load and forward on GPU,
(c) a single training step succeeds without dtype/shape errors.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from st_gcn import STGCN  # noqa: E402


def banner(text: str) -> None:
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def main() -> None:
    banner("1. CUDA / device info")
    print("torch       :", torch.__version__)
    print("cuda        :", torch.cuda.is_available())
    print("cuda ver    :", torch.version.cuda)
    print("device      :", torch.cuda.get_device_name(0))
    print("capability  :", torch.cuda.get_device_capability(0))
    print("vram total  :", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2), "GB")

    device = torch.device("cuda")

    banner("2. Raw CUDA matmul benchmark (fp32)")
    sizes = [(2048, 2048), (4096, 4096)]
    for n, m in sizes:
        a = torch.randn(n, m, device=device)
        b = torch.randn(m, n, device=device)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(20):
            c = a @ b
        torch.cuda.synchronize()
        dt = (time.perf_counter() - t0) / 20
        tflops = (2 * n * m * n) / dt / 1e12
        print(f"  matmul {n}x{m}: {dt*1000:6.2f} ms/iter  ~{tflops:5.1f} TFLOPS")
        del a, b, c
    torch.cuda.empty_cache()

    banner("3. Load existing NPZ dataset")
    npz_path = ROOT / "data" / "processed" / "boxing_punch_dataset.npz"
    if not npz_path.exists():
        print(f"  SKIP (missing {npz_path})")
        X = np.random.randn(32, 3, 64, 17).astype(np.float32)
        y = np.random.randint(0, 5, size=32).astype(np.int64)
        classes = ["none", "jab", "cross", "hook", "uppercut"]
    else:
        data = np.load(npz_path, allow_pickle=True)
        X = data["X"].astype(np.float32)
        y = data["y"].astype(np.int64)
        classes = [str(c) for c in data["classes"]]
        print(f"  X shape    : {X.shape}")
        print(f"  y shape    : {y.shape}")
        print(f"  classes    : {classes}")
        print(f"  class dist :", {classes[i]: int((y == i).sum()) for i in range(len(classes))})

    banner("4. ST-GCN forward + backward on GPU")
    model = STGCN(in_channels=X.shape[1], num_classes=len(classes)).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  params     : {n_params:,}")

    Xb = torch.from_numpy(X[:32]).to(device)
    yb = torch.from_numpy(y[:32]).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    torch.cuda.synchronize()
    t0 = time.perf_counter()
    logits = model(Xb)
    loss = criterion(logits, yb)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) * 1000
    print(f"  batch=32   : {dt:.1f} ms (forward+backward+step)")
    print(f"  logits     : {tuple(logits.shape)}")
    print(f"  loss       : {loss.item():.4f}")

    banner("5. Sustained throughput (batch 64, 50 iters)")
    Xb = torch.from_numpy(X[: min(64, len(X))]).to(device)
    if Xb.shape[0] < 64:
        Xb = Xb.repeat((64 // Xb.shape[0]) + 1, 1, 1, 1)[:64]
    yb = torch.from_numpy(y[: Xb.shape[0]]).to(device) if len(y) >= Xb.shape[0] else torch.zeros(Xb.shape[0], dtype=torch.long, device=device)
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(50):
        logits = model(Xb)
        loss = criterion(logits, yb)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    print(f"  50 iters   : {dt:.2f} s  ({50/dt:.1f} iter/s, {50*Xb.shape[0]/dt:.0f} samples/s)")

    banner("DONE.  GPU pipeline is healthy.")


if __name__ == "__main__":
    main()
