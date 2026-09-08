"""
RTMPose (RTMO-s) 기반 비디오 → 정규화 키포인트 시퀀스 추출.

원본: LIM data extraction.py (COCO 17 키포인트, normalized 0~1 좌표).
재사용 가능한 함수 형태로 정리.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterator, NamedTuple

import cv2
import numpy as np

from ..config import RTMO_URL

COCO17_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

CSV_HEADER = ["frame_number"]
for _name in COCO17_NAMES:
    CSV_HEADER.extend([f"{_name}_x", f"{_name}_y", f"{_name}_z", f"{_name}_v"])


class FrameKeypoints(NamedTuple):
    frame_number: int
    # (17, 2) pixel coords
    pixels: np.ndarray
    # (17,) confidence
    scores: np.ndarray
    # (17, 4) normalized (x,y,z=0,v)
    normalized: np.ndarray
    width: int
    height: int


_model_cache = {"model": None}


def _pick_device() -> str:
    """가용한 가장 빠른 ONNX provider 선택.

    우선순위: DmlExecutionProvider (DirectML, Win iGPU/dGPU 모두 지원)
             → CUDAExecutionProvider
             → CPUExecutionProvider
    """
    try:
        import onnxruntime as ort
        from rtmlib.tools.base import RTMLIB_SETTINGS
        avail = set(ort.get_available_providers())
        # rtmlib 기본 매핑에는 dml 이 없으니 한 번에 추가
        RTMLIB_SETTINGS.setdefault("onnxruntime", {})["dml"] = "DmlExecutionProvider"
        if "DmlExecutionProvider" in avail:
            return "dml"
        if "CUDAExecutionProvider" in avail:
            return "cuda"
    except Exception as e:
        print(f"[pose] provider detection failed: {e}")
    return "cpu"


def get_model():
    """Lazy-load the RTMPose model once per process."""
    if _model_cache["model"] is None:
        from rtmlib import RTMO  # imported lazily so the module is importable without onnx
        device = _pick_device()
        print(f"[pose] Loading RTMPose (RTMO-s) on device={device}...")
        try:
            _model_cache["model"] = RTMO(RTMO_URL, backend="onnxruntime", device=device)
        except Exception as e:
            print(f"[pose] failed to load on {device} ({e}), falling back to cpu")
            _model_cache["model"] = RTMO(RTMO_URL, backend="onnxruntime", device="cpu")
        print("[pose] Model ready.")
    return _model_cache["model"]


def iter_video_keypoints(
    video_path: str | Path,
    progress: Callable[[int, int], None] | None = None,
) -> Iterator[FrameKeypoints | None]:
    """Yield FrameKeypoints per frame (None for unrecognized frames)."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    model = get_model()
    frame_idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            fh, fw = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            kps, scs = model(rgb)

            if len(kps) > 0:
                kp = kps[0]  # (17, 2)
                sc = scs[0]  # (17,)
                norm = np.zeros((17, 4), dtype=np.float32)
                norm[:, 0] = kp[:, 0] / fw
                norm[:, 1] = kp[:, 1] / fh
                norm[:, 2] = 0.0
                norm[:, 3] = sc
                yield FrameKeypoints(
                    frame_number=frame_idx,
                    pixels=kp.astype(np.float32),
                    scores=sc.astype(np.float32),
                    normalized=norm,
                    width=fw,
                    height=fh,
                )
            else:
                yield None

            if progress is not None:
                progress(frame_idx, total)
    finally:
        cap.release()


def extract_video_to_csv(
    video_path: str | Path,
    csv_path: str | Path,
    progress: Callable[[int, int], None] | None = None,
) -> dict:
    """Run extraction and write a CSV identical in schema to LIM_full_data*.csv."""
    import csv as _csv

    video_path = Path(video_path)
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    saved = skipped = 0
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.writer(f)
        writer.writerow(CSV_HEADER)
        for fk in iter_video_keypoints(video_path, progress=progress):
            if fk is None:
                skipped += 1
                continue
            row = [fk.frame_number]
            for i in range(17):
                nx, ny, _, v = fk.normalized[i]
                row.extend([round(float(nx), 6), round(float(ny), 6), 0.0, round(float(v), 4)])
            writer.writerow(row)
            saved += 1

    return {"saved": saved, "skipped": skipped, "csv": str(csv_path)}
