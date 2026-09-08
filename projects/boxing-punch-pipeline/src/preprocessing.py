from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pose_schema import (
    CLASS_NAMES,
    LEFT_HIP,
    LEFT_SHOULDER,
    NUM_JOINTS,
    RIGHT_HIP,
    RIGHT_SHOULDER,
    landmark_columns,
)
from punch_event import resample_pose_sequence

# COCO-17 left/right joint pairs, used for the L/R swap during a horizontal flip.
_COCO_MIRROR_PAIRS = [
    (1, 2),   # eyes
    (3, 4),   # ears
    (5, 6),   # shoulders
    (7, 8),   # elbows
    (9, 10),  # wrists
    (11, 12), # hips
    (13, 14), # knees
    (15, 16), # ankles
]

_NOSE = 0


def detect_facing(poses: np.ndarray) -> int:
    """Return +1 if the boxer faces toward +x in image coords, -1 if -x.

    Uses median sign of (nose.x - hip_center.x) across the window. For
    side-view boxing footage this is a stable proxy for which way the
    boxer is oriented relative to the camera.
    Expects normalized (hip-centered) poses, but also works on raw poses.
    """
    if len(poses) == 0:
        return -1
    nose_x = poses[:, _NOSE, 0]
    hip_x = (poses[:, LEFT_HIP, 0] + poses[:, RIGHT_HIP, 0]) * 0.5
    return 1 if float(np.median(nose_x - hip_x)) > 0.0 else -1


def canonicalize_facing(poses: np.ndarray) -> np.ndarray:
    """Flip horizontally so the boxer always faces -x (canonical).

    Mutates and returns a copy. Channel layout assumed: index 0=x, 1=y,
    2=score (or any pass-through field).
    """
    if detect_facing(poses) != 1:
        return poses.copy() if poses.flags.writeable is False else poses
    out = poses.copy()
    out[..., 0] = -out[..., 0]
    for a, b in _COCO_MIRROR_PAIRS:
        tmp = out[:, a].copy()
        out[:, a] = out[:, b]
        out[:, b] = tmp
    return out


def load_pose_csv(path: Path) -> tuple[str, np.ndarray, np.ndarray]:
    df = pd.read_csv(path)
    video_id = str(df["video_id"].iloc[0])
    frames = df["frame_index"].to_numpy(dtype=np.int64)
    columns = landmark_columns()
    coords = df[columns].to_numpy(dtype=np.float32)
    channels = len(columns) // NUM_JOINTS
    poses = coords.reshape(len(df), NUM_JOINTS, channels)
    return video_id, frames, poses


def normalize_pose_sequence(poses: np.ndarray, min_scale: float = 1e-4) -> np.ndarray:
    out = poses.copy()
    xy = out[..., :2]

    left_hip = xy[:, LEFT_HIP]
    right_hip = xy[:, RIGHT_HIP]
    center = (left_hip + right_hip) * 0.5
    xy -= center[:, None, :]

    shoulder_width = np.linalg.norm(
        xy[:, LEFT_SHOULDER] - xy[:, RIGHT_SHOULDER], axis=1
    )
    hip_width = np.linalg.norm(xy[:, LEFT_HIP] - xy[:, RIGHT_HIP], axis=1)
    scale = np.maximum(shoulder_width, hip_width)
    valid_scale = scale[scale > min_scale]
    fallback = float(np.median(valid_scale)) if len(valid_scale) else 1.0
    scale = np.where(scale > min_scale, scale, fallback)
    xy /= scale[:, None, None]

    out[..., :2] = np.nan_to_num(xy, nan=0.0, posinf=0.0, neginf=0.0)
    out[..., 2] = np.nan_to_num(out[..., 2], nan=0.0, posinf=0.0, neginf=0.0)
    return out


def read_labels(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Label file not found: {path}")
    labels = pd.read_csv(path, comment="#")
    required = {"video_id", "start_frame", "end_frame", "label"}
    missing = required.difference(labels.columns)
    if missing:
        raise ValueError(f"Missing label columns: {sorted(missing)}")
    labels = labels.dropna(subset=["video_id", "start_frame", "end_frame", "label"])
    labels["video_id"] = labels["video_id"].astype(str)
    labels["start_frame"] = labels["start_frame"].astype(int)
    labels["end_frame"] = labels["end_frame"].astype(int)
    if "apex_frame" in labels.columns:
        labels["apex_frame"] = labels["apex_frame"].fillna(
            ((labels["start_frame"] + labels["end_frame"]) // 2)
        ).astype(int)
    else:
        labels["apex_frame"] = ((labels["start_frame"] + labels["end_frame"]) // 2).astype(int)
    labels["label"] = labels["label"].astype(str)
    return labels


def choose_window_label(
    video_labels: pd.DataFrame,
    start_frame: int,
    end_frame: int,
    min_overlap: float,
) -> str:
    if video_labels.empty:
        return "none"

    best_label = "none"
    best_overlap = 0.0
    window_len = max(1, end_frame - start_frame + 1)

    for row in video_labels.itertuples(index=False):
        overlap_start = max(start_frame, int(row.start_frame))
        overlap_end = min(end_frame, int(row.end_frame))
        overlap = max(0, overlap_end - overlap_start + 1) / window_len
        if overlap > best_overlap:
            best_overlap = overlap
            best_label = str(row.label)

    return best_label if best_overlap >= min_overlap else "none"


def build_dataset(
    raw_dir: Path,
    labels_path: Path,
    output_path: Path,
    window_size: int = 64,
    stride: int = 8,
    min_overlap: float = 0.25,
    none_stride: int | None = None,
    max_none_ratio: float = 1.0,
    class_names: list[str] | None = None,
) -> None:
    class_names = class_names or CLASS_NAMES
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}
    labels = read_labels(labels_path)

    X = []
    y = []
    meta = []

    for csv_path in sorted(raw_dir.glob("*.pose.csv")):
        video_id, frames, poses = load_pose_csv(csv_path)
        poses = normalize_pose_sequence(poses)
        video_labels = labels[labels["video_id"] == video_id]

        if len(poses) < window_size:
            continue

        for start in range(0, len(poses) - window_size + 1, stride):
            end = start + window_size
            start_frame = int(frames[start])
            end_frame = int(frames[end - 1])
            label = choose_window_label(video_labels, start_frame, end_frame, min_overlap)
            if label not in class_to_idx:
                raise ValueError(f"Unknown label '{label}'. Add it to CLASS_NAMES or fix labels.csv.")

            window = canonicalize_facing(poses[start:end])
            X.append(np.transpose(window, (2, 0, 1)))
            y.append(class_to_idx[label])
            meta.append(
                {
                    "video_id": video_id,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "label": label,
                }
            )

        if none_stride:
            positive_count = sum(1 for item in meta if item["video_id"] == video_id and item["label"] != "none")
            max_none = int(positive_count * max_none_ratio)
            none_added = 0
            for start in range(0, len(poses) - window_size + 1, none_stride):
                if none_added >= max_none:
                    break
                end = start + window_size
                start_frame = int(frames[start])
                end_frame = int(frames[end - 1])
                label = choose_window_label(video_labels, start_frame, end_frame, min_overlap=0.01)
                if label != "none":
                    continue
                window = poses[start:end]
                X.append(np.transpose(window, (2, 0, 1)))
                y.append(class_to_idx["none"])
                meta.append(
                    {
                        "video_id": video_id,
                        "start_frame": start_frame,
                        "end_frame": end_frame,
                        "label": "none",
                    }
                )
                none_added += 1

    if not X:
        raise RuntimeError("No windows created. Check raw CSV files, labels, and window size.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        X=np.asarray(X, dtype=np.float32),
        y=np.asarray(y, dtype=np.int64),
        classes=np.asarray(class_names),
        meta=np.asarray([json.dumps(item, ensure_ascii=True) for item in meta]),
    )


def build_event_dataset(
    raw_dir: Path,
    labels_path: Path,
    output_path: Path,
    window_size: int = 32,
    context_frames: int = 4,
    shift_radius: int = 2,
    class_names: list[str] | None = None,
) -> None:
    labels = read_labels(labels_path)
    if class_names is None:
        has_none = bool((labels["label"] == "none").any())
        class_names = CLASS_NAMES if has_none else [name for name in CLASS_NAMES if name != "none"]
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}

    X = []
    y = []
    meta = []

    for csv_path in sorted(raw_dir.glob("*.pose.csv")):
        video_id, frames, poses = load_pose_csv(csv_path)
        video_labels = labels[labels["video_id"] == video_id]
        if video_labels.empty:
            continue

        frame_to_pos = {int(frame): idx for idx, frame in enumerate(frames)}
        for row in video_labels.itertuples(index=False):
            label = str(row.label)
            if label not in class_to_idx:
                continue

            start_frame = int(row.start_frame) - context_frames
            end_frame = int(row.end_frame) + context_frames
            apex_frame = int(row.apex_frame)
            start_pos = int(np.searchsorted(frames, start_frame, side="left"))
            end_pos = int(np.searchsorted(frames, end_frame, side="right")) - 1
            apex_pos = frame_to_pos.get(apex_frame, int(np.searchsorted(frames, apex_frame, side="left")))

            if end_pos <= start_pos:
                continue
            start_pos = max(0, start_pos)
            end_pos = min(len(poses) - 1, end_pos)
            apex_pos = int(np.clip(apex_pos, start_pos, end_pos))

            shifts = range(-shift_radius, shift_radius + 1) if shift_radius > 0 else range(1)
            for shift in shifts:
                shifted_start = int(np.clip(start_pos + shift, 0, len(poses) - 1))
                shifted_end = int(np.clip(end_pos + shift, 0, len(poses) - 1))
                if shifted_end <= shifted_start:
                    continue

                segment = poses[shifted_start : shifted_end + 1]
                window = normalize_pose_sequence(resample_pose_sequence(segment, window_size))
                window = canonicalize_facing(window)
                X.append(np.transpose(window, (2, 0, 1)))
                y.append(class_to_idx[label])
                meta.append(
                    {
                        "video_id": video_id,
                        "start_frame": int(frames[shifted_start]),
                        "apex_frame": int(frames[apex_pos]),
                        "end_frame": int(frames[shifted_end]),
                        "label": label,
                    }
                )

    if not X:
        raise RuntimeError("No event windows created. Check labels.csv and pose CSV files.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        X=np.asarray(X, dtype=np.float32),
        y=np.asarray(y, dtype=np.int64),
        classes=np.asarray(class_names),
        meta=np.asarray([json.dumps(item, ensure_ascii=True) for item in meta]),
    )
