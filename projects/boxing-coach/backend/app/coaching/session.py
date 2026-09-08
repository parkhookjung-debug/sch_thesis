"""
End-to-end 코칭 세션:
  사용자 영상 (입력)
    → RTMPose 키포인트 시퀀스
    → 펀치 감지 + 자세 평가 (코치 DNA 기준)
    → 오버레이된 결과 영상 (mp4)
    → 요약 JSON
"""
from __future__ import annotations

import csv as _csv
import statistics
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

from .keypoints import detect_facing
from .posture import PostureResult, calc_posture
from .punch_detector import PunchDetectorState, feed as feed_punch
from .render import draw_counter, draw_posture, draw_punch_flash, draw_skeleton
from ..pose.dna import DNA_METRICS, compute_frame_metrics
from ..pose.extractor import extract_video_to_csv, get_model
from ..pose.punch_dna import aggregate_punch_dna


def _aggregate_dna(metric_buckets: dict[str, list[float]]) -> dict:
    dna: dict[str, float] = {}
    for key in DNA_METRICS:
        vals = metric_buckets.get(key, [])
        if vals:
            dna[key] = statistics.mean(vals)
            dna[f"{key}_std"] = statistics.stdev(vals) if len(vals) > 1 else 0.0
        else:
            dna[key] = 0.0
            dna[f"{key}_std"] = 0.0
    return dna


def analyze_user_video(
    video_path: str | Path,
    work_dir: str | Path,
    progress: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """사용자 영상에서 자세 DNA + 펀치 DNA 추출 (매칭 단계 입력).

    Returns: { 'user_dna': dict, 'user_punch': {pt: row}, 'frames_used': int }
    """
    video_path = Path(video_path)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    full_csv = work_dir / "user_full_data.csv"
    extract_video_to_csv(video_path, full_csv, progress=progress)

    # 자세 DNA
    buckets: dict[str, list[float]] = {k: [] for k in DNA_METRICS}
    frames_used = 0
    with full_csv.open(newline="", encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            m = compute_frame_metrics(row)
            if m is None:
                continue
            for k, v in m.items():
                buckets[k].append(v)
            frames_used += 1
    user_dna = _aggregate_dna(buckets)

    # 펀치 DNA (단일 CSV)
    punch_rows = aggregate_punch_dna([full_csv])
    user_punch = {row["punch_type"]: row for row in punch_rows}

    return {
        "user_dna": user_dna,
        "user_punch": user_punch,
        "frames_used": frames_used,
        "full_csv": str(full_csv),
    }


def render_coaching_video(
    video_path: str | Path,
    output_path: str | Path,
    coach_dna: dict,
    coach_label: str,
    progress: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """입력 영상에 스켈레톤 + 카운터 + 점수 패널 + 펀치 플래시를 오버레이한
    결과 영상(mp4)을 만든다.
    """
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (fw, fh))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot open output writer: {output_path}")

    model = get_model()
    state = PunchDetectorState(facing_right=True)
    posture_running: Optional[PostureResult] = None
    posture_samples: list[PostureResult] = []
    punch_events: list[dict] = []
    last_punch_type: Optional[str] = None
    last_punch_time = -10.0
    facing_locked = False
    frame_idx = 0
    score_sum = 0
    score_n = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            t = frame_idx / fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            kps, scs = model(rgb)
            if len(kps) > 0:
                kp = kps[0]
                sc = scs[0]
                # 초반 30프레임 동안 facing 자동 판정
                if not facing_locked and frame_idx <= 30:
                    state.facing_right = detect_facing(kp, sc)
                    if frame_idx == 30:
                        facing_locked = True

                events = feed_punch(state, kp, sc, frame_idx, t)
                for ev in events:
                    punch_events.append({
                        "frame": ev.frame_number,
                        "time": round(ev.timestamp, 3),
                        "type": ev.punch_type,
                        "side": ev.side,
                        "arm_extension": ev.arm_extension,
                        "elbow_angle": ev.elbow_angle,
                        "lean_forward": ev.lean_forward,
                    })
                    last_punch_type = ev.punch_type
                    last_punch_time = t

                p = calc_posture(kp, sc, coach_dna, facing_right=state.facing_right)
                if p is not None:
                    posture_running = p
                    posture_samples.append(p)
                    score_sum += p.total
                    score_n += 1

                draw_skeleton(frame, kp, sc)

            draw_counter(frame, state.counts)
            if posture_running is not None:
                draw_posture(frame, posture_running, coach_label=f"COACH · {coach_label}")
            if last_punch_type is not None:
                draw_punch_flash(frame, last_punch_type, t - last_punch_time)

            writer.write(frame)
            if progress is not None:
                progress(frame_idx, total)
    finally:
        cap.release()
        writer.release()

    avg_score = round(score_sum / score_n, 1) if score_n else 0.0
    summary = {
        "output_video": str(output_path),
        "frames_total": total,
        "frames_processed": frame_idx,
        "facing_right": state.facing_right,
        "coach": coach_label,
        "punch_counts": dict(state.counts),
        "total_punches": sum(state.counts.values()),
        "punch_events": punch_events[:200],   # 200개 이상은 잘라서 응답 크기 제한
        "average_score": avg_score,
        "samples_evaluated": score_n,
    }
    return summary
