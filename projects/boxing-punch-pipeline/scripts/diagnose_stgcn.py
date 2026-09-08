from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from st_gcn import STGCN


def resolve_device(requested: str) -> torch.device:
    if requested.startswith("cuda") and not torch.cuda.is_available():
        print("CUDA was requested, but this venv has CPU-only PyTorch. Falling back to CPU.")
        return torch.device("cpu")
    return torch.device(requested)


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, n: int) -> np.ndarray:
    matrix = np.zeros((n, n), dtype=np.int64)
    for actual, pred in zip(y_true, y_pred):
        matrix[int(actual), int(pred)] += 1
    return matrix


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect ST-GCN class bias on an NPZ dataset.")
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    data = np.load(args.data, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)

    device = resolve_device(args.device)
    checkpoint = torch.load(args.checkpoint, map_location=device)
    classes = [str(item) for item in checkpoint["classes"]]
    model = STGCN(in_channels=int(checkpoint["in_channels"]), num_classes=len(classes))
    model.load_state_dict(checkpoint["model_state"])
    model.to(device).eval()

    probs_all = []
    with torch.no_grad():
        for start in range(0, len(X), args.batch_size):
            batch = torch.from_numpy(X[start : start + args.batch_size]).to(device)
            probs_all.append(torch.softmax(model(batch), dim=1).cpu().numpy())

    probs = np.concatenate(probs_all, axis=0)
    pred = probs.argmax(axis=1)
    conf = probs.max(axis=1)
    matrix = confusion_matrix(y, pred, len(classes))

    print(f"data={args.data}")
    print(f"checkpoint={args.checkpoint}")
    print(f"samples={len(y)} accuracy={(pred == y).mean():.4f}")
    print()
    print("true_counts")
    for idx, name in enumerate(classes):
        print(f"  {name:10s} {int((y == idx).sum()):5d}")
    print()
    print("pred_counts")
    for idx, name in enumerate(classes):
        mask = pred == idx
        avg_conf = float(conf[mask].mean()) if mask.any() else 0.0
        print(f"  {name:10s} {int(mask.sum()):5d}  avg_conf={avg_conf:.3f}")
    print()
    print("confusion rows=true cols=pred")
    print(" " * 12 + " ".join(f"{name[:8]:>8s}" for name in classes))
    for idx, name in enumerate(classes):
        cells = " ".join(f"{int(value):8d}" for value in matrix[idx])
        row_acc = matrix[idx, idx] / max(1, matrix[idx].sum())
        print(f"{name[:10]:>10s}  {cells}  acc={row_acc:.3f}")


if __name__ == "__main__":
    main()
