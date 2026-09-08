from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from preprocessing import load_pose_csv, normalize_pose_sequence
from st_gcn import STGCN


COLORS = {
    "none": (150, 150, 150),
    "jab": (0, 220, 255),
    "cross": (40, 160, 255),
    "hook": (255, 50, 200),
    "uppercut": (50, 255, 100),
}


def resolve_device(requested: str) -> torch.device:
    if requested.startswith("cuda") and not torch.cuda.is_available():
        print("CUDA was requested, but this venv has CPU-only PyTorch. Falling back to CPU.")
        return torch.device("cpu")
    return torch.device(requested)


def ensure_pose_csv(video_path: Path, raw_dir: Path, pose2d: str, device: str) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    csv_path = raw_dir / f"{video_path.stem}.pose.csv"
    if csv_path.exists():
        return csv_path

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "extract_pose.py"),
        "--input",
        str(video_path),
        "--output",
        str(raw_dir),
        "--pose2d",
        pose2d,
        "--device",
        device,
    ]
    subprocess.run(cmd, check=True)
    return csv_path


def predict_windows(
    model: STGCN,
    poses: np.ndarray,
    frames: np.ndarray,
    classes: list[str],
    window_size: int,
    stride: int,
    threshold: float,
    device: torch.device,
) -> list[dict]:
    predictions = []
    model.eval()

    with torch.no_grad():
        for start in range(0, len(poses) - window_size + 1, stride):
            end = start + window_size
            window = poses[start:end]
            x = np.transpose(window, (2, 0, 1))[None].astype(np.float32)
            logits = model(torch.from_numpy(x).to(device))
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            pred_idx = int(probs.argmax())
            confidence = float(probs[pred_idx])
            label = classes[pred_idx] if confidence >= threshold else "none"
            predictions.append(
                {
                    "start_frame": int(frames[start]),
                    "center_frame": int(frames[start + window_size // 2]),
                    "end_frame": int(frames[end - 1]),
                    "label": label,
                    "raw_label": classes[pred_idx],
                    "confidence": confidence,
                    **{f"prob_{name}": float(probs[i]) for i, name in enumerate(classes)},
                }
            )

    return predictions


def smooth_frame_predictions(predictions: list[dict], total_frames: int) -> list[dict]:
    per_frame = [
        {"frame": idx, "label": "none", "confidence": 0.0, "raw_label": "none"}
        for idx in range(total_frames)
    ]
    for pred in predictions:
        center = pred["center_frame"]
        if 0 <= center < total_frames and pred["confidence"] >= per_frame[center]["confidence"]:
            per_frame[center] = {
                "frame": center,
                "label": pred["label"],
                "confidence": pred["confidence"],
                "raw_label": pred["raw_label"],
            }
    return per_frame


def render_preview(video_path: Path, frame_predictions: list[dict], output_path: Path) -> None:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    frame_idx = 0
    last_active = {"label": "none", "confidence": 0.0, "ttl": 0}

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_idx < len(frame_predictions):
            pred = frame_predictions[frame_idx]
            if pred["label"] != "none":
                last_active = {
                    "label": pred["label"],
                    "confidence": pred["confidence"],
                    "ttl": int(fps * 0.35),
                }

        label = last_active["label"] if last_active["ttl"] > 0 else "none"
        confidence = last_active["confidence"] if last_active["ttl"] > 0 else 0.0
        color = COLORS.get(label, (255, 255, 255))
        if last_active["ttl"] > 0:
            last_active["ttl"] -= 1

        cv2.rectangle(frame, (0, 0), (width, 78), (0, 0, 0), -1)
        text = f"{label.upper()}  {confidence:.2f}" if label != "none" else "NONE"
        cv2.putText(frame, text, (24, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.25, color, 3, cv2.LINE_AA)
        cv2.putText(frame, f"frame {frame_idx}", (width - 220, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (230, 230, 230), 1, cv2.LINE_AA)
        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--checkpoint", default=ROOT / "models" / "stgcn_best.pt", type=Path)
    parser.add_argument("--raw-dir", default=ROOT / "data" / "raw", type=Path)
    parser.add_argument("--output-csv", default=None, type=Path)
    parser.add_argument("--preview", default=None, type=Path)
    parser.add_argument("--window-size", type=int, default=32)
    parser.add_argument("--stride", type=int, default=4)
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--pose2d", default="human")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    device = resolve_device(args.device)
    pose_csv = ensure_pose_csv(args.video, args.raw_dir, args.pose2d, str(device))
    video_id, frames, poses = load_pose_csv(pose_csv)
    poses = normalize_pose_sequence(poses)

    checkpoint = torch.load(args.checkpoint, map_location=device)
    classes = [str(item) for item in checkpoint["classes"]]
    model = STGCN(in_channels=int(checkpoint["in_channels"]), num_classes=len(classes))
    model.load_state_dict(checkpoint["model_state"])
    model.to(device)

    predictions = predict_windows(
        model,
        poses,
        frames,
        classes,
        args.window_size,
        args.stride,
        args.threshold,
        device,
    )

    output_csv = args.output_csv or (ROOT / "data" / "predictions" / f"{args.video.stem}.predictions.csv")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(predictions).to_csv(output_csv, index=False)

    counts = pd.DataFrame(predictions)["label"].value_counts().to_dict() if predictions else {}
    print(f"pose_csv={pose_csv}")
    print(f"predictions={output_csv}")
    print(f"counts={json.dumps(counts, ensure_ascii=False)}")

    if args.preview:
        frame_predictions = smooth_frame_predictions(predictions, int(frames[-1]) + 1)
        render_preview(args.video, frame_predictions, args.preview)
        print(f"preview={args.preview}")


if __name__ == "__main__":
    main()
