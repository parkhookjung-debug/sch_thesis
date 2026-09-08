from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pose_schema import NUM_JOINTS, landmark_columns


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}


def iter_videos(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(path for path in input_path.rglob("*") if path.suffix.lower() in VIDEO_EXTENSIONS)


def extract_video(
    video_path: Path,
    output_dir: Path,
    pose2d: str = "human",
    device: str | None = None,
    overwrite: bool = False,
) -> Path:
    try:
        import cv2
        from mmpose.apis import MMPoseInferencer
    except ImportError as exc:
        raise RuntimeError(
            "MMPose is required. Run the install commands in README.md, including mmcv, mmdet, and mmpose."
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{video_path.stem}.pose.csv"
    if out_path.exists() and not overwrite:
        print(f"Skipping existing {out_path}")
        return out_path

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    cap.release()

    inferencer = MMPoseInferencer(
        pose2d=pose2d,
        det_model=None,
        det_cat_ids=[0],
        device=device,
        show_progress=False,
    )

    rows = []
    result_generator = inferencer(str(video_path), show=False, return_vis=False)
    for frame_index, result in enumerate(tqdm(result_generator, total=frame_count or None, desc=video_path.name)):
        row = {
            "video_id": video_path.stem,
            "frame_index": frame_index,
            "time_sec": frame_index / fps if fps > 0 else 0.0,
            "width": width,
            "height": height,
            "fps": fps,
            "pose_model": f"mmpose:{pose2d}",
        }

        keypoints, scores = select_primary_pose(result)
        for idx in range(NUM_JOINTS):
            row[f"kpt_{idx}_x"] = float(keypoints[idx][0])
            row[f"kpt_{idx}_y"] = float(keypoints[idx][1])
            row[f"kpt_{idx}_score"] = float(scores[idx])

        rows.append(row)

    columns = ["video_id", "frame_index", "time_sec", "width", "height", "fps", "pose_model"] + landmark_columns()
    pd.DataFrame(rows, columns=columns).to_csv(out_path, index=False)
    return out_path


def select_primary_pose(result: dict):
    import numpy as np

    instances = result.get("predictions", [[]])
    instances = instances[0] if instances else []
    if not instances:
        return np.zeros((NUM_JOINTS, 2), dtype=np.float32), np.zeros(NUM_JOINTS, dtype=np.float32)

    def instance_score(instance: dict) -> float:
        bbox_score = instance.get("bbox_score", instance.get("bbox_scores", [1.0]))
        if isinstance(bbox_score, list):
            bbox_score = bbox_score[0] if bbox_score else 1.0
        bbox = instance.get("bbox", instance.get("bboxes", None))
        area = 1.0
        if bbox is not None:
            bbox_arr = np.asarray(bbox, dtype=np.float32).reshape(-1)
            if bbox_arr.size >= 4:
                area = max(1.0, float((bbox_arr[2] - bbox_arr[0]) * (bbox_arr[3] - bbox_arr[1])))
        return float(bbox_score) * area

    primary = max(instances, key=instance_score)
    keypoints = np.asarray(primary.get("keypoints", []), dtype=np.float32)
    scores = np.asarray(primary.get("keypoint_scores", []), dtype=np.float32)

    if keypoints.shape != (NUM_JOINTS, 2):
        fixed = np.zeros((NUM_JOINTS, 2), dtype=np.float32)
        count = min(NUM_JOINTS, len(keypoints))
        fixed[:count] = keypoints[:count, :2]
        keypoints = fixed

    if scores.shape != (NUM_JOINTS,):
        fixed_scores = np.zeros(NUM_JOINTS, dtype=np.float32)
        count = min(NUM_JOINTS, len(scores))
        fixed_scores[:count] = scores[:count]
        scores = fixed_scores

    return keypoints, scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path, help="Video file or directory.")
    parser.add_argument("--output", required=True, type=Path, help="Raw pose CSV output directory.")
    parser.add_argument("--pose2d", default="human", help="MMPose pose2d alias/config. Default 'human' is RTMPose-m.")
    parser.add_argument("--device", default=None, help="cuda, cuda:0, cpu, or None for MMPose auto selection.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing pose CSV files.")
    args = parser.parse_args()

    videos = iter_videos(args.input)
    if not videos:
        raise SystemExit(f"No videos found in {args.input}")

    for video_path in videos:
        out_path = extract_video(video_path, args.output, args.pose2d, args.device, args.overwrite)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
