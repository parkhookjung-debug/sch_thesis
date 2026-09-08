from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pose_schema import NUM_JOINTS, SKELETON_EDGES
from preprocessing import normalize_pose_sequence
from st_gcn import STGCN


COLORS = {
    "none": (150, 150, 150),
    "jab": (0, 220, 255),
    "cross": (40, 160, 255),
    "hook": (255, 50, 200),
    "uppercut": (50, 255, 100),
}


def parse_source(source: str):
    try:
        return int(source)
    except ValueError:
        return source


def resolve_device(requested: str) -> torch.device:
    if requested.startswith("cuda") and not torch.cuda.is_available():
        print("CUDA was requested, but this venv has CPU-only PyTorch. Falling back to CPU.")
        return torch.device("cpu")
    return torch.device(requested)


def select_primary_pose(result: dict):
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

    fixed_keypoints = np.zeros((NUM_JOINTS, 2), dtype=np.float32)
    fixed_scores = np.zeros(NUM_JOINTS, dtype=np.float32)
    count = min(NUM_JOINTS, len(keypoints))
    if count:
        fixed_keypoints[:count] = keypoints[:count, :2]
    count = min(NUM_JOINTS, len(scores))
    if count:
        fixed_scores[:count] = scores[:count]
    return fixed_keypoints, fixed_scores


def infer_pose(inferencer, frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result_generator = inferencer(rgb, show=False, return_vis=False)
    result = next(result_generator)
    keypoints, scores = select_primary_pose(result)
    return np.concatenate([keypoints, scores[:, None]], axis=1)


def predict(model, buffer, classes, device):
    poses = np.asarray(buffer, dtype=np.float32)
    poses = normalize_pose_sequence(poses)
    x = np.transpose(poses, (2, 0, 1))[None].astype(np.float32)
    with torch.no_grad():
        logits = model(torch.from_numpy(x).to(device))
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
    idx = int(probs.argmax())
    confidence = float(probs[idx])
    raw_label = classes[idx]
    return raw_label, confidence, probs


def draw_pose(frame, pose, min_score=0.25):
    for a, b in SKELETON_EDGES:
        if pose[a, 2] < min_score or pose[b, 2] < min_score:
            continue
        pa = tuple(np.round(pose[a, :2]).astype(int))
        pb = tuple(np.round(pose[b, :2]).astype(int))
        cv2.line(frame, pa, pb, (80, 220, 120), 2, cv2.LINE_AA)
    for idx in range(NUM_JOINTS):
        if pose[idx, 2] < min_score:
            continue
        p = tuple(np.round(pose[idx, :2]).astype(int))
        cv2.circle(frame, p, 3, (255, 255, 255), -1, cv2.LINE_AA)


def choose_label(classes, probs, threshold, margin):
    order = np.argsort(probs)[::-1]
    top = int(order[0])
    second = int(order[1]) if len(order) > 1 else top
    confidence = float(probs[top])
    gap = float(probs[top] - probs[second])
    raw_label = classes[top]
    label = raw_label if confidence >= threshold and gap >= margin else "none"
    return label, raw_label, confidence, gap, order


def draw_hud(frame, label, raw_label, confidence, gap, fps, buffer_len, window_size, classes, probs):
    h, w = frame.shape[:2]
    color = COLORS.get(label, (255, 255, 255))
    cv2.rectangle(frame, (0, 0), (w, 142), (0, 0, 0), -1)
    title = f"{label.upper()}  {confidence:.2f}" if label != "none" else f"NONE  raw={raw_label} {confidence:.2f}"
    cv2.putText(frame, title, (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.15, color, 3, cv2.LINE_AA)
    cv2.putText(
        frame,
        f"fps {fps:.1f}  buffer {buffer_len}/{window_size}  margin {gap:.2f}  Q quit",
        (24, 78),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (230, 230, 230),
        1,
        cv2.LINE_AA,
    )
    if probs is not None:
        x = 24
        y = 118
        for name, prob in sorted(zip(classes, probs), key=lambda item: item[1], reverse=True):
            text = f"{name}:{prob:.2f}"
            cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLORS.get(name, (220, 220, 220)), 1, cv2.LINE_AA)
            x += 135


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="Camera index or video path.")
    parser.add_argument("--checkpoint", default=ROOT / "models" / "stgcn_best.pt", type=Path)
    parser.add_argument("--window-size", type=int, default=32)
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--margin", type=float, default=0.06, help="Top-1 minus top-2 probability margin required for a punch.")
    parser.add_argument("--ema", type=float, default=0.45, help="Probability smoothing. 0 disables smoothing, higher is smoother.")
    parser.add_argument("--hold-frames", type=int, default=6, help="Keep the last confident punch visible for this many frames.")
    parser.add_argument("--pose2d", default="human")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--draw-pose", action="store_true")
    parser.add_argument("--record", default=None, type=Path)
    args = parser.parse_args()

    from mmpose.apis import MMPoseInferencer

    device = resolve_device(args.device)
    infer_device = str(device)
    checkpoint = torch.load(args.checkpoint, map_location=device)
    classes = [str(item) for item in checkpoint["classes"]]
    model = STGCN(in_channels=int(checkpoint["in_channels"]), num_classes=len(classes))
    model.load_state_dict(checkpoint["model_state"])
    model.to(device)
    model.eval()

    inferencer = MMPoseInferencer(
        pose2d=args.pose2d,
        det_model=None,
        det_cat_ids=[0],
        device=infer_device,
        show_progress=False,
    )

    cap = cv2.VideoCapture(parse_source(args.source))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open source: {args.source}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    writer = None
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(args.record), fourcc, src_fps, (width, height))

    pose_buffer = deque(maxlen=args.window_size)
    label = "none"
    raw_label = "none"
    confidence = 0.0
    gap = 0.0
    probs_ema = None
    display_label = "none"
    display_confidence = 0.0
    hold_ttl = 0
    fps = 0.0
    prev = time.perf_counter()

    cv2.namedWindow("Boxing Punch Recognizer", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Boxing Punch Recognizer", min(width, 1280), int(min(width, 1280) * height / max(width, 1)))

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        pose = infer_pose(inferencer, frame)
        pose_buffer.append(pose)

        if len(pose_buffer) == args.window_size:
            raw_label, confidence, probs = predict(model, pose_buffer, classes, device)
            if probs_ema is None or args.ema <= 0:
                probs_ema = probs
            else:
                probs_ema = args.ema * probs_ema + (1.0 - args.ema) * probs
            label, raw_label, confidence, gap, _ = choose_label(classes, probs_ema, args.threshold, args.margin)
            if label != "none":
                display_label = label
                display_confidence = confidence
                hold_ttl = args.hold_frames
            elif hold_ttl > 0:
                hold_ttl -= 1
            else:
                display_label = "none"
                display_confidence = confidence

        now = time.perf_counter()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev, 1e-6)) if fps else 1.0 / max(now - prev, 1e-6)
        prev = now

        if args.draw_pose:
            draw_pose(frame, pose)
        draw_hud(
            frame,
            display_label,
            raw_label,
            display_confidence,
            gap,
            fps,
            len(pose_buffer),
            args.window_size,
            classes,
            probs_ema,
        )

        cv2.imshow("Boxing Punch Recognizer", frame)
        if writer:
            writer.write(frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
