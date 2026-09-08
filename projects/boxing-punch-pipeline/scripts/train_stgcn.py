from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from st_gcn import STGCN


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def make_loaders(npz_path: Path, batch_size: int, seed: int):
    data = np.load(npz_path, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    classes = [str(item) for item in data["classes"]]

    indices = np.arange(len(y))
    stratify = y if len(np.unique(y)) > 1 else None
    train_idx, val_idx = train_test_split(
        indices,
        test_size=0.2,
        random_state=seed,
        stratify=stratify,
    )

    train_ds = TensorDataset(torch.from_numpy(X[train_idx]), torch.from_numpy(y[train_idx]))
    val_ds = TensorDataset(torch.from_numpy(X[val_idx]), torch.from_numpy(y[val_idx]))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, drop_last=False)
    return train_loader, val_loader, classes, X.shape[1]


def run_epoch(model, loader, criterion, optimizer, device, train: bool):
    model.train(train)
    total_loss = 0.0
    total_correct = 0
    total_count = 0
    all_preds = []
    all_targets = []

    for X, y in tqdm(loader, leave=False):
        X = X.to(device)
        y = y.to(device)

        with torch.set_grad_enabled(train):
            logits = model(X)
            loss = criterion(logits, y)
            if train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()

        preds = logits.argmax(dim=1)
        total_loss += float(loss.item()) * len(y)
        total_correct += int((preds == y).sum().item())
        total_count += len(y)
        all_preds.extend(preds.detach().cpu().numpy().tolist())
        all_targets.extend(y.detach().cpu().numpy().tolist())

    avg_loss = total_loss / max(1, total_count)
    accuracy = total_correct / max(1, total_count)
    return avg_loss, accuracy, np.asarray(all_targets), np.asarray(all_preds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "models")
    args = parser.parse_args()

    seed_everything(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader, classes, in_channels = make_loaders(args.data, args.batch_size, args.seed)

    model = STGCN(in_channels=in_channels, num_classes=len(classes)).to(device)
    dataset_counts = np.bincount(
        np.concatenate([batch_y.numpy() for _, batch_y in train_loader]),
        minlength=len(classes),
    ).astype(np.float32)
    weights = dataset_counts.sum() / np.maximum(dataset_counts, 1.0)
    weights = weights / weights.mean()
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32, device=device))
    print("class_weights", {classes[i]: round(float(weights[i]), 4) for i in range(len(classes))})
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    best_acc = -1.0
    best_path = args.output_dir / "stgcn_best.pt"

    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc, _, _ = run_epoch(model, train_loader, criterion, optimizer, device, True)
        val_loss, val_acc, y_true, y_pred = run_epoch(model, val_loader, criterion, optimizer, device, False)

        print(
            f"epoch={epoch:03d} "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "classes": classes,
                    "in_channels": in_channels,
                    "val_acc": best_acc,
                },
                best_path,
            )

    print(f"Best checkpoint: {best_path} val_acc={best_acc:.4f}")
    print(classification_report(y_true, y_pred, labels=list(range(len(classes))), target_names=classes, zero_division=0))


if __name__ == "__main__":
    main()
