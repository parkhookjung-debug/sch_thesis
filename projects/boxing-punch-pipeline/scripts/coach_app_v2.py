"""Realtime boxing coach UI v2 — GPU pose via rtmlib + SmallSTGCN.

No mmpose dependency. Runs entirely in .venv-gpu.

Pipeline:
  webcam frame
    -> rtmlib RTMPose (ONNX, GPU) -> 17 COCO keypoints
    -> PunchEventDetector (motion energy gating)
    -> normalize + resample to 32-frame window
    -> SmallSTGCN (PyTorch CUDA) -> class probabilities
    -> rule-based geometry fuse -> displayed punch
"""
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

import cuda_setup  # noqa: F401  must come before onnxruntime/rtmlib import
from pose_schema import NUM_JOINTS, SKELETON_EDGES  # noqa: E402
from preprocessing import canonicalize_facing, normalize_pose_sequence  # noqa: E402
from punch_event import (  # noqa: E402
    PunchEventDetector,
    extract_event_window,
)
from small_stgcn import SmallSTGCN  # noqa: E402
from stgcn_coach_app import (  # noqa: E402  reuse the polished UI helpers
    C_ACCENT,
    C_BORDER,
    C_INK,
    PUNCH_BGR,
    CAM_W,
    WIN_H,
    WIN_W,
    draw_skeleton,
    draw_text,
    render_sidebar,
    rule_classify_event,
    fuse_model_and_rule,
    choose_label,
)


def parse_source(s: str):
    try:
        return int(s)
    except ValueError:
        return s


def load_small_model(checkpoint: Path, device: torch.device):
    ckpt = torch.load(checkpoint, map_location=device, weights_only=False)
    classes = [str(c) for c in ckpt["classes"]]
    arch = ckpt.get("arch", "SmallSTGCN")
    if arch != "SmallSTGCN":
        raise SystemExit(f"Checkpoint arch={arch} but this app expects SmallSTGCN.")
    model = SmallSTGCN(
        in_channels=int(ckpt["in_channels"]),
        num_classes=len(classes),
        dropout=float(ckpt.get("dropout", 0.4)),
        base_channels=int(ckpt.get("base_channels", 32)),
    )
    model.load_state_dict(ckpt["model_state"])
    model.to(device).eval()
    return model, classes, ckpt


def init_pose(device_str: str, mode: str = "balanced"):
    """Build an rtmlib RTMPose body pose estimator.

    mode='balanced' uses RTMPose-M, which is the same backbone we trained the
    classifier against (via MMPose extract_pose.py).  Using a different size
    here (e.g. 'lightweight' / RTMPose-S) gives noticeably different keypoint
    positions on fast-moving limbs and breaks classification.
    """
    from rtmlib import Body
    backend = "onnxruntime"
    device = "cuda" if device_str.startswith("cuda") else "cpu"
    body = Body(mode=mode, to_openpose=False, backend=backend, device=device)
    return body


def coco_from_rtmlib(keypoints: np.ndarray, scores: np.ndarray) -> np.ndarray:
    """rtmlib Body returns 17 COCO keypoints in the same order as our pose_schema."""
    pose = np.zeros((NUM_JOINTS, 3), dtype=np.float32)
    n = min(NUM_JOINTS, len(keypoints))
    pose[:n, :2] = keypoints[:n, :2]
    if scores is not None and len(scores):
        pose[:n, 2] = scores[:n]
    return pose


def predict(model, poses_window: np.ndarray, device: torch.device) -> np.ndarray:
    poses = normalize_pose_sequence(np.asarray(poses_window, dtype=np.float32))
    poses = canonicalize_facing(poses)
    x = np.transpose(poses, (2, 0, 1))[None].astype(np.float32)
    with torch.no_grad():
        probs = torch.softmax(model(torch.from_numpy(x).to(device)), dim=1).cpu().numpy()[0]
    return probs


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="0")
    p.add_argument("--checkpoint", type=Path,
                   default=ROOT / "models" / "small" / "best_canonical.pt")
    p.add_argument("--device", default="cuda")
    p.add_argument("--window-size", type=int, default=32)
    p.add_argument("--threshold", type=float, default=0.45)
    p.add_argument("--margin", type=float, default=0.04)
    p.add_argument("--cooldown", type=float, default=0.35)
    p.add_argument("--start-threshold", type=float, default=0.17)
    p.add_argument("--end-threshold", type=float, default=0.09)
    p.add_argument("--min-event-frames", type=int, default=5)
    p.add_argument("--max-event-frames", type=int, default=28)
    p.add_argument("--pre-roll", type=int, default=5)
    p.add_argument("--cooldown-frames", type=int, default=7)
    p.add_argument("--event-smooth", type=float, default=0.35)
    p.add_argument("--fall-ratio", type=float, default=0.45)
    p.add_argument("--hold", type=float, default=0.28)
    p.add_argument("--lead-hand", choices=["left", "right"], default="left")
    p.add_argument("--disable-rule", action="store_true")
    p.add_argument("--mirror", action="store_true")
    p.add_argument("--debug-events", action="store_true")
    p.add_argument("--pose-mode", default="balanced",
                   choices=["lightweight", "balanced", "performance"],
                   help="rtmlib pose model size. 'balanced'=RTMPose-M matches training.")
    args = p.parse_args()

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    print(f"Classifier device: {device}")

    model, classes, ckpt = load_small_model(args.checkpoint, device)
    print(f"Loaded {ckpt.get('arch')} from {args.checkpoint}")
    print(f"  classes={classes}  honest_val_acc={ckpt.get('val_acc'):.3f}")
    if "lovo_per_fold" in ckpt:
        print(f"  per-video LOVO: {ckpt['lovo_per_fold']}")

    pose_estimator = init_pose(args.device, mode=args.pose_mode)
    print(f"Pose estimator: rtmlib Body ({args.pose_mode}, device={args.device})")

    cap = cv2.VideoCapture(parse_source(args.source))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open source: {args.source}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detector = PunchEventDetector(
        start_threshold=args.start_threshold,
        end_threshold=args.end_threshold,
        min_event_frames=args.min_event_frames,
        max_event_frames=args.max_event_frames,
        pre_roll=args.pre_roll,
        cooldown_frames=args.cooldown_frames,
        smooth=args.event_smooth,
        fall_ratio=args.fall_ratio,
    )

    counts = {name: 0 for name in ["jab", "cross", "hook", "uppercut"]}
    recent: deque = deque(maxlen=8)
    probs_last = None
    label, raw_label, confidence, gap = "none", "none", 0.0, 0.0
    display_label, display_confidence, display_until = "none", 0.0, 0.0
    energy = 0.0
    last_count_time = 0.0
    flash = None
    phase = "READY"
    side = "-"
    fps = 0.0
    prev = time.perf_counter()

    cv2.namedWindow("BOXING COACH v2", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("BOXING COACH v2", WIN_W, WIN_H)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        now = time.perf_counter()
        if args.mirror:
            frame = cv2.flip(frame, 1)

        frame_h, frame_w = frame.shape[:2]
        cam_frame = cv2.resize(frame, (CAM_W, WIN_H), interpolation=cv2.INTER_AREA)

        # rtmlib Body returns (keypoints, scores) where keypoints is (N, 17, 2)
        keypoints, scores = pose_estimator(frame)
        if len(keypoints) == 0:
            pose = np.zeros((NUM_JOINTS, 3), dtype=np.float32)
        else:
            # pick largest person by area of the joint bounding box
            best = 0
            if len(keypoints) > 1:
                areas = []
                for kp in keypoints:
                    x0, y0 = kp.min(axis=0)
                    x1, y1 = kp.max(axis=0)
                    areas.append(float((x1 - x0) * (y1 - y0)))
                best = int(np.argmax(areas))
            pose = coco_from_rtmlib(keypoints[best], scores[best])

        event, features = detector.update(pose)
        energy = features.energy
        phase = detector.state.upper()
        side = features.active_side.upper()

        pose_disp = pose.copy()
        pose_disp[:, 0] *= CAM_W / max(1, frame_w)
        pose_disp[:, 1] *= WIN_H / max(1, frame_h)

        if event is not None:
            window = extract_event_window(event, args.window_size)
            probs_last = predict(model, window, device)
            model_label, model_raw, confidence, gap = choose_label(classes, probs_last, args.threshold, args.margin)
            rule_label, rule_confidence, rule_debug = rule_classify_event(event, args.lead_hand)
            label = fuse_model_and_rule(
                model_label, confidence, gap, rule_label,
                rule_confidence, float(rule_debug.get("margin", 0.0)),
                not args.disable_rule,
            )
            if args.debug_events:
                print(f"event model={model_label} conf={confidence:.2f} gap={gap:.2f} "
                      f"rule={rule_label} rconf={rule_confidence:.2f} fused={label}",
                      flush=True)
            raw_label = f"{model_raw}/{rule_label}"
            side = event.active_side.upper()
            phase = "CLASSIFY"
            if label != "none" and now - last_count_time > args.cooldown:
                counts[label] = counts.get(label, 0) + 1
                recent.append((label, confidence))
                flash = (label, now + 0.18)
                display_label = label
                display_confidence = confidence
                display_until = now + args.hold
                last_count_time = now
        elif now > display_until:
            label = "none"
            display_label = "none"

        fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev, 1e-6)) if fps else 1.0 / max(now - prev, 1e-6)
        prev = now

        canvas = np.full((WIN_H, WIN_W, 3), C_INK, dtype=np.uint8)
        canvas[:, :CAM_W] = cam_frame
        draw_skeleton(canvas[:, :CAM_W], pose_disp)

        if flash and now < flash[1]:
            flabel = flash[0]
            color = PUNCH_BGR.get(flabel, C_ACCENT)
            overlay = canvas[:, :CAM_W].copy()
            cv2.rectangle(overlay, (0, 0), (CAM_W - 1, WIN_H - 1), color, 10)
            cv2.addWeighted(overlay, 0.35, canvas[:, :CAM_W], 0.65, 0, canvas[:, :CAM_W])
            draw_text(canvas[:, :CAM_W], flabel.upper(), (34, 70), 1.6, color, 4)

        cv2.line(canvas, (CAM_W, 0), (CAM_W, WIN_H), C_BORDER, 1)
        render_sidebar(
            canvas, classes, probs_last, display_label, raw_label,
            display_confidence, gap, energy, phase, side, counts, recent, fps,
            True, args.mirror,
        )

        cv2.imshow("BOXING COACH v2", canvas)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("r"):
            for n in counts:
                counts[n] = 0
            recent.clear()
        if key == ord("m"):
            args.mirror = not args.mirror
            detector.reset()
            probs_last = None
            display_label = "none"
            display_until = 0.0

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
