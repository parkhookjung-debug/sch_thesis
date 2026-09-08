"""Train SmallSTGCN with proper Leave-One-Video-Out validation.

Why a new trainer:
  Existing train_stgcn.py does random window-level train/val split. Windows from
  the same video leak into both sides, giving val_acc=1.0 that doesn't reflect
  real generalization. This script splits by *video* and reports per-video
  performance.

Usage:
  python scripts/train_small.py --data data/processed/boxing_punch_events.npz \\
      --epochs 60 --augment --val-mode lovo

val-mode:
  lovo            run leave-one-video-out cross-validation, print per-fold accuracy
  holdout         hold out a single video for validation (--holdout-video LIM 8)
  random          random window split (old behavior, for comparison)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report
from torch import nn
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from augment import PoseAugment  # noqa: E402
from small_stgcn import SmallSTGCN  # noqa: E402


def make_augment(no_mirror: bool) -> PoseAugment:
    """When data is already facing-canonicalized, random mirror would undo it."""
    return PoseAugment(mirror_p=0.0 if no_mirror else 0.5)


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class PoseDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray, augment: PoseAugment | None = None):
        self.X = X
        self.y = y
        self.augment = augment

    def __len__(self) -> int:
        return len(self.y)

    def __getitem__(self, i: int):
        x = torch.from_numpy(self.X[i]).float()
        if self.augment is not None:
            x = self.augment(x)
        return x, int(self.y[i])


def load_npz(path: Path):
    data = np.load(path, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    classes = [str(c) for c in data["classes"]]
    metas = [json.loads(s) for s in data["meta"]]
    video_ids = np.array([m["video_id"] for m in metas])
    return X, y, classes, video_ids


def run_epoch(model, loader, criterion, optimizer, device, train: bool):
    model.train(train)
    total_loss = 0.0
    correct = 0
    count = 0
    preds_all: list[int] = []
    targets_all: list[int] = []
    for X, y in loader:
        X = X.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        with torch.set_grad_enabled(train):
            logits = model(X)
            loss = criterion(logits, y)
            if train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
        preds = logits.argmax(dim=1)
        total_loss += float(loss.item()) * len(y)
        correct += int((preds == y).sum().item())
        count += len(y)
        preds_all.extend(preds.detach().cpu().tolist())
        targets_all.extend(y.detach().cpu().tolist())
    return (
        total_loss / max(1, count),
        correct / max(1, count),
        np.asarray(targets_all),
        np.asarray(preds_all),
    )


def train_one_fold(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    X_va: np.ndarray,
    y_va: np.ndarray,
    classes: list[str],
    args,
    device: torch.device,
    fold_label: str,
):
    train_aug = make_augment(no_mirror=args.canonical) if args.augment else None
    train_ds = PoseDataset(X_tr, y_tr, augment=train_aug)
    val_ds = PoseDataset(X_va, y_va, augment=None)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              drop_last=False, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                            drop_last=False, num_workers=0)

    in_c = X_tr.shape[1]
    model = SmallSTGCN(in_channels=in_c, num_classes=len(classes),
                       dropout=args.dropout, base_channels=args.base_channels).to(device)

    counts = np.bincount(y_tr, minlength=len(classes)).astype(np.float32)
    inv = counts.sum() / np.maximum(counts, 1.0)
    inv = inv / inv.mean()
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(inv, dtype=torch.float32, device=device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val = -1.0
    best_state = None
    history: list[dict] = []
    for epoch in range(1, args.epochs + 1):
        tr_loss, tr_acc, _, _ = run_epoch(model, train_loader, criterion, optimizer, device, True)
        va_loss, va_acc, va_y, va_p = run_epoch(model, val_loader, criterion, optimizer, device, False)
        scheduler.step()
        history.append({"epoch": epoch, "train_acc": tr_acc, "val_acc": va_acc,
                        "train_loss": tr_loss, "val_loss": va_loss})
        if va_acc > best_val:
            best_val = va_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch % args.print_every == 0 or epoch == 1 or epoch == args.epochs:
            print(f"  [{fold_label}] ep={epoch:03d}  tr_loss={tr_loss:.3f} tr_acc={tr_acc:.3f}  "
                  f"va_loss={va_loss:.3f} va_acc={va_acc:.3f}  (best {best_val:.3f})")

    # restore best for final report
    if best_state is not None:
        model.load_state_dict(best_state)
    va_loss, va_acc, va_y, va_p = run_epoch(model, val_loader, criterion, optimizer, device, False)
    return {
        "fold": fold_label,
        "best_val_acc": float(best_val),
        "final_val_acc": float(va_acc),
        "y_true": va_y,
        "y_pred": va_p,
        "model_state": best_state,
        "n_train": int(len(y_tr)),
        "n_val": int(len(y_va)),
        "history": history,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--val-mode", choices=["lovo", "holdout", "random"], default="lovo")
    p.add_argument("--holdout-video", type=str, default=None)
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--weight-decay", type=float, default=5e-4)
    p.add_argument("--dropout", type=float, default=0.4)
    p.add_argument("--base-channels", type=int, default=32)
    p.add_argument("--augment", action="store_true")
    p.add_argument("--canonical", action="store_true",
                   help="Disable random mirror in augment because data is already facing-canonicalized.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", default="cuda")
    p.add_argument("--print-every", type=int, default=10)
    p.add_argument("--output-dir", type=Path, default=ROOT / "models" / "small")
    args = p.parse_args()

    seed_everything(args.seed)
    device = torch.device(args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu")
    print(f"Device: {device}")

    X, y, classes, video_ids = load_npz(args.data)
    print(f"Data: X={X.shape} y={y.shape} classes={classes}")
    print(f"Videos: {sorted(set(video_ids.tolist()))}")
    print(f"Augmentation: {'ON' if args.augment else 'off'}")

    sample_model = SmallSTGCN(in_channels=X.shape[1], num_classes=len(classes),
                              dropout=args.dropout, base_channels=args.base_channels)
    n_params = sum(p.numel() for p in sample_model.parameters())
    print(f"Model params: {n_params:,}")
    del sample_model

    args.output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    if args.val_mode == "random":
        from sklearn.model_selection import train_test_split
        idx = np.arange(len(y))
        tr, va = train_test_split(idx, test_size=0.2, random_state=args.seed,
                                  stratify=y if len(set(y)) > 1 else None)
        fold = train_one_fold(X[tr], y[tr], X[va], y[va], classes, args, device, "random")
        torch.save({
            "model_state": fold["model_state"],
            "classes": classes,
            "in_channels": X.shape[1],
            "val_acc": fold["best_val_acc"],
            "arch": "SmallSTGCN",
            "base_channels": args.base_channels,
            "dropout": args.dropout,
        }, args.output_dir / "best_random.pt")
        print(f"\nRandom split val_acc = {fold['best_val_acc']:.4f}")

    elif args.val_mode == "holdout":
        target = args.holdout_video or sorted(set(video_ids.tolist()))[-1]
        mask = video_ids == target
        if not mask.any():
            raise SystemExit(f"holdout video '{target}' not found in dataset")
        fold = train_one_fold(X[~mask], y[~mask], X[mask], y[mask], classes, args, device, f"holdout={target}")
        print(f"\nHoldout '{target}' val_acc = {fold['best_val_acc']:.4f}  (n_val={fold['n_val']})")
        print(classification_report(fold["y_true"], fold["y_pred"],
                                    labels=list(range(len(classes))), target_names=classes, zero_division=0))
        torch.save({
            "model_state": fold["model_state"],
            "classes": classes,
            "in_channels": X.shape[1],
            "val_acc": fold["best_val_acc"],
            "arch": "SmallSTGCN",
            "base_channels": args.base_channels,
            "dropout": args.dropout,
            "holdout_video": target,
        }, args.output_dir / f"best_holdout_{target}.pt".replace(" ", "_"))

    else:  # lovo
        videos = sorted(set(video_ids.tolist()))
        all_results = []
        for held in videos:
            mask = video_ids == held
            print(f"\n--- LOVO fold: holding out '{held}' ({int(mask.sum())} val samples) ---")
            fold = train_one_fold(X[~mask], y[~mask], X[mask], y[mask], classes, args, device, held)
            all_results.append(fold)
        accs = [f["best_val_acc"] for f in all_results]
        print("\n" + "=" * 70)
        print("LEAVE-ONE-VIDEO-OUT SUMMARY")
        print("=" * 70)
        for f in all_results:
            print(f"  {f['fold']:8s}  n_val={f['n_val']:4d}  best_val_acc={f['best_val_acc']:.4f}")
        print(f"\n  mean = {np.mean(accs):.4f}   std = {np.std(accs):.4f}   "
              f"min = {np.min(accs):.4f}   max = {np.max(accs):.4f}")

        # Aggregate confusion across folds
        y_true_all = np.concatenate([f["y_true"] for f in all_results])
        y_pred_all = np.concatenate([f["y_pred"] for f in all_results])
        print("\nAggregate classification report (across all held-out videos):")
        print(classification_report(y_true_all, y_pred_all,
                                    labels=list(range(len(classes))),
                                    target_names=classes, zero_division=0))

        # Train one final model on ALL data with augmentation, save it
        print("\nTraining final model on ALL data (for deployment)...")
        final = train_one_fold(X, y, X[:1], y[:1], classes, args, device, "FINAL-ALL")
        torch.save({
            "model_state": final["model_state"],
            "classes": classes,
            "in_channels": X.shape[1],
            "val_acc": float(np.mean(accs)),  # honest LOVO mean
            "arch": "SmallSTGCN",
            "base_channels": args.base_channels,
            "dropout": args.dropout,
            "lovo_per_fold": {f["fold"]: f["best_val_acc"] for f in all_results},
        }, args.output_dir / "best_lovo_final.pt")
        print(f"Saved -> {args.output_dir / 'best_lovo_final.pt'}")

    print(f"\nTotal time: {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
