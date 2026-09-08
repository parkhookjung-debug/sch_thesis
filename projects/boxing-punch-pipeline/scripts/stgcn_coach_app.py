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

from punch_event import (
    LEFT_ELBOW,
    LEFT_WRIST,
    RIGHT_ELBOW,
    RIGHT_WRIST,
    PunchEventDetector,
    extract_event_window,
    pose_scale,
)
from pose_schema import NUM_JOINTS, SKELETON_EDGES
from preprocessing import normalize_pose_sequence
from st_gcn import STGCN


WIN_W, WIN_H = 1280, 720
CAM_W = 853
SB_X = CAM_W + 1
SB_W = WIN_W - SB_X
PAD = 14

C_INK = (18, 13, 11)
C_CANVAS = (28, 21, 19)
C_BORDER = (55, 48, 46)
C_TEXT = (245, 244, 244)
C_MUTED = (170, 161, 161)
C_DIM = (122, 113, 113)
C_ACCENT = (87, 61, 255)
C_GREEN = (100, 220, 0)
C_AMBER = (50, 165, 255)

PUNCH_BGR = {
    "jab": (0, 220, 255),
    "cross": (255, 160, 40),
    "hook": (200, 50, 255),
    "uppercut": (100, 255, 50),
    "none": (130, 130, 130),
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


def draw_text(img, text, pos, scale=0.6, color=C_TEXT, thickness=1):
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def draw_card(img, x, y, w, h, color=C_CANVAS, border=C_BORDER):
    cv2.rectangle(img, (x, y), (x + w, y + h), color, -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), border, 1)


def draw_bar(img, x, y, w, h, ratio, color=C_ACCENT, bg=C_BORDER):
    cv2.rectangle(img, (x, y), (x + w, y + h), bg, -1)
    fw = int(w * max(0.0, min(1.0, ratio)))
    if fw:
        cv2.rectangle(img, (x, y), (x + fw, y + h), color, -1)


def select_primary_pose(result: dict):
    instances = result.get("predictions", [[]])
    instances = instances[0] if instances else []
    if not instances:
        return np.zeros((NUM_JOINTS, 2), dtype=np.float32), np.zeros(NUM_JOINTS, dtype=np.float32)

    def instance_score(instance):
        bbox_score = instance.get("bbox_score", instance.get("bbox_scores", [1.0]))
        if isinstance(bbox_score, list):
            bbox_score = bbox_score[0] if bbox_score else 1.0
        bbox = instance.get("bbox", instance.get("bboxes", None))
        area = 1.0
        if bbox is not None:
            arr = np.asarray(bbox, dtype=np.float32).reshape(-1)
            if arr.size >= 4:
                area = max(1.0, float((arr[2] - arr[0]) * (arr[3] - arr[1])))
        return float(bbox_score) * area

    primary = max(instances, key=instance_score)
    keypoints = np.asarray(primary.get("keypoints", []), dtype=np.float32)
    scores = np.asarray(primary.get("keypoint_scores", []), dtype=np.float32)
    fixed_keypoints = np.zeros((NUM_JOINTS, 2), dtype=np.float32)
    fixed_scores = np.zeros(NUM_JOINTS, dtype=np.float32)
    n = min(NUM_JOINTS, len(keypoints))
    if n:
        fixed_keypoints[:n] = keypoints[:n, :2]
    n = min(NUM_JOINTS, len(scores))
    if n:
        fixed_scores[:n] = scores[:n]
    return fixed_keypoints, fixed_scores


def infer_pose(inferencer, frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = next(inferencer(rgb, show=False, return_vis=False))
    keypoints, scores = select_primary_pose(result)
    return np.concatenate([keypoints, scores[:, None]], axis=1)


def draw_skeleton(frame, pose, min_score=0.25):
    for a, b in SKELETON_EDGES:
        if pose[a, 2] < min_score or pose[b, 2] < min_score:
            continue
        pa = tuple(np.round(pose[a, :2]).astype(int))
        pb = tuple(np.round(pose[b, :2]).astype(int))
        cv2.line(frame, pa, pb, (60, 60, 85), 2, cv2.LINE_AA)
    for i in range(NUM_JOINTS):
        if pose[i, 2] < min_score:
            continue
        p = tuple(np.round(pose[i, :2]).astype(int))
        cv2.circle(frame, p, 4, C_ACCENT, -1, cv2.LINE_AA)


def predict(model, poses, device):
    poses = normalize_pose_sequence(np.asarray(poses, dtype=np.float32))
    x = np.transpose(poses, (2, 0, 1))[None].astype(np.float32)
    with torch.no_grad():
        logits = model(torch.from_numpy(x).to(device))
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
    return probs


def choose_label(classes, probs, threshold, margin):
    order = np.argsort(probs)[::-1]
    top = int(order[0])
    second = int(order[1]) if len(order) > 1 else top
    conf = float(probs[top])
    gap = float(probs[top] - probs[second])
    raw = classes[top]
    label = raw if conf >= threshold and gap >= margin else "none"
    return label, raw, conf, gap


def rule_classify_event(event, lead_hand):
    apex_pose = event.poses[event.apex_index]
    start_pose = event.poses[0]
    end_pose = event.poses[-1]
    scale = pose_scale(apex_pose)

    side = event.active_side
    wrist_idx = LEFT_WRIST if side == "left" else RIGHT_WRIST
    elbow_idx = LEFT_ELBOW if side == "left" else RIGHT_ELBOW
    apex_feat = event.features[event.apex_index]
    elbow_angle = apex_feat.left_elbow_angle if side == "left" else apex_feat.right_elbow_angle
    extension = apex_feat.left_extension if side == "left" else apex_feat.right_extension

    wrist_path = event.poses[:, wrist_idx, :2]
    lateral_range = float((np.max(wrist_path[:, 0]) - np.min(wrist_path[:, 0])) / scale)
    start_to_apex = (apex_pose[wrist_idx, :2] - start_pose[wrist_idx, :2]) / scale
    apex_to_end = (end_pose[wrist_idx, :2] - apex_pose[wrist_idx, :2]) / scale
    upward = float(-start_to_apex[1])
    downward_after = float(apex_to_end[1])

    is_lead = side == lead_hand
    straight_label = "jab" if is_lead else "cross"

    straight_score = 0.0
    straight_score += np.clip((elbow_angle - 125.0) / 35.0, 0.0, 1.0) * 0.45
    straight_score += np.clip((extension - 0.85) / 0.55, 0.0, 1.0) * 0.35
    straight_score += np.clip((0.95 - lateral_range) / 0.65, 0.0, 1.0) * 0.20

    hook_score = 0.0
    hook_score += np.clip((145.0 - elbow_angle) / 45.0, 0.0, 1.0) * 0.45
    hook_score += np.clip((lateral_range - 0.35) / 0.65, 0.0, 1.0) * 0.40
    hook_score += np.clip((extension - 0.55) / 0.45, 0.0, 1.0) * 0.15

    uppercut_score = 0.0
    uppercut_score += np.clip((upward - 0.12) / 0.45, 0.0, 1.0) * 0.45
    uppercut_score += np.clip((downward_after - 0.02) / 0.30, 0.0, 1.0) * 0.15
    uppercut_score += np.clip((150.0 - elbow_angle) / 55.0, 0.0, 1.0) * 0.25
    uppercut_score += np.clip((extension - 0.45) / 0.45, 0.0, 1.0) * 0.15

    scores = {
        straight_label: float(straight_score),
        "hook": float(hook_score),
        "uppercut": float(uppercut_score),
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    label, confidence = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    return label, confidence, {
        "elbow": elbow_angle,
        "extension": extension,
        "lateral": lateral_range,
        "upward": upward,
        "scores": scores,
        "margin": float(confidence - runner_up),
    }


def fuse_model_and_rule(model_label, model_conf, model_gap, rule_label, rule_conf, rule_margin, use_rule):
    if not use_rule or model_label == "none":
        return model_label
    if model_label == rule_label:
        return model_label

    # The geometry rule is a useful tie-breaker, but it can over-call straights
    # because hooks and uppercuts also pass through extended-elbow frames.
    if model_label == "cross" and rule_label in {"hook", "uppercut"}:
        if rule_conf >= 0.70 and rule_margin >= 0.16:
            return rule_label
    if model_conf < 0.62 and rule_conf >= 0.70 and rule_margin >= 0.16:
        return rule_label
    if model_conf < 0.80 and model_gap < 0.18 and rule_conf >= 0.88 and rule_margin >= 0.22:
        return rule_label
    return model_label


def render_sidebar(
    canvas,
    classes,
    probs,
    label,
    raw_label,
    confidence,
    gap,
    energy,
    phase,
    side,
    counts,
    recent,
    fps,
    ready,
    mirrored,
):
    x0 = SB_X + PAD
    cw = SB_W - PAD * 2

    draw_text(canvas, "BOXING", (x0, 45), 1.35, C_TEXT, 3)
    draw_text(canvas, ".", (x0 + 182, 45), 1.35, C_ACCENT, 3)
    draw_text(canvas, "COACH", (x0 + 205, 45), 1.35, C_TEXT, 3)

    cy = 70
    draw_card(canvas, x0, cy, cw, 78)
    col = PUNCH_BGR.get(label, C_DIM)
    title = label.upper() if label != "none" else "READY" if ready else "POSE..."
    draw_text(canvas, title, (x0 + 14, cy + 40), 1.0, col, 2)
    draw_text(canvas, f"raw {raw_label}  conf {confidence:.2f}  gap {gap:.2f}", (x0 + 14, cy + 62), 0.48, C_MUTED)
    draw_text(canvas, f"{phase}  {side}  motion {energy:.3f}", (x0 + 14, cy + 82), 0.44, C_DIM)
    cy += 92

    draw_card(canvas, x0, cy, cw, 178)
    draw_text(canvas, "PROBABILITY", (x0 + 12, cy + 26), 0.55, C_DIM)
    py = cy + 46
    if probs is not None:
        for name, prob in sorted(zip(classes, probs), key=lambda item: item[1], reverse=True):
            color = PUNCH_BGR.get(name, C_ACCENT)
            draw_text(canvas, f"{name.upper():8s} {prob:.2f}", (x0 + 14, py), 0.52, C_TEXT)
            draw_bar(canvas, x0 + 140, py - 13, cw - 158, 9, float(prob), color)
            py += 25
    cy += 192

    draw_card(canvas, x0, cy, cw, 158)
    draw_text(canvas, "PUNCH COUNT", (x0 + 12, cy + 26), 0.55, C_DIM)
    labels = ["jab", "cross", "hook", "uppercut"]
    for i, name in enumerate(labels):
        bx = x0 + 14 + (i % 2) * (cw // 2)
        by = cy + 48 + (i // 2) * 48
        color = PUNCH_BGR[name]
        draw_text(canvas, name.upper(), (bx, by), 0.48, C_MUTED)
        draw_text(canvas, f"{counts.get(name, 0):03d}", (bx, by + 28), 0.82, color, 2)
    cy += 174

    draw_card(canvas, x0, cy, cw, 124)
    draw_text(canvas, "RECENT", (x0 + 12, cy + 26), 0.55, C_DIM)
    for i, item in enumerate(list(recent)[-4:][::-1]):
        name, conf = item
        draw_text(canvas, f"{name.upper():8s} {conf:.2f}", (x0 + 14, cy + 52 + i * 22), 0.52, PUNCH_BGR.get(name, C_TEXT))
    cy += 140

    draw_card(canvas, x0, cy, cw, 76)
    draw_text(canvas, f"FPS {fps:.1f}", (x0 + 14, cy + 30), 0.62, C_TEXT)
    draw_text(canvas, f"R reset   M mirror {'ON' if mirrored else 'OFF'}   Q quit", (x0 + 14, cy + 58), 0.52, C_DIM)


def main():
    parser = argparse.ArgumentParser(description="ST-GCN boxing coach UI")
    parser.add_argument("--source", default="0", help="camera index or video path")
    parser.add_argument("--checkpoint", default=ROOT / "models" / "event" / "stgcn_best.pt", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--pose2d", default="human")
    parser.add_argument("--window-size", type=int, default=32)
    parser.add_argument("--threshold", type=float, default=0.45)
    parser.add_argument("--margin", type=float, default=0.04)
    parser.add_argument("--cooldown", type=float, default=0.35)
    parser.add_argument("--start-threshold", type=float, default=0.17)
    parser.add_argument("--end-threshold", type=float, default=0.09)
    parser.add_argument("--min-event-frames", type=int, default=5)
    parser.add_argument("--max-event-frames", type=int, default=28)
    parser.add_argument("--pre-roll", type=int, default=5)
    parser.add_argument("--cooldown-frames", type=int, default=7)
    parser.add_argument("--event-smooth", type=float, default=0.35)
    parser.add_argument("--fall-ratio", type=float, default=0.45)
    parser.add_argument("--hold", type=float, default=0.28)
    parser.add_argument("--lead-hand", choices=["left", "right"], default="left")
    parser.add_argument("--disable-rule", action="store_true")
    parser.add_argument("--debug-events", action="store_true", help="Print model/rule/fused labels for each detected event.")
    parser.add_argument("--mirror", action="store_true", help="Flip camera/video horizontally before pose inference.")
    args = parser.parse_args()

    from mmpose.apis import MMPoseInferencer

    device = resolve_device(args.device)
    infer_device = str(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    classes = [str(item) for item in ckpt["classes"]]
    model = STGCN(in_channels=int(ckpt["in_channels"]), num_classes=len(classes))
    model.load_state_dict(ckpt["model_state"])
    model.to(device).eval()

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
    recent = deque(maxlen=8)
    probs_last = None
    label, raw_label, confidence, gap = "none", "none", 0.0, 0.0
    display_label, display_confidence = "none", 0.0
    display_until = 0.0
    energy = 0.0
    last_count_time = 0.0
    flash = None
    phase = "READY"
    side = "-"
    fps = 0.0
    prev = time.perf_counter()

    cv2.namedWindow("BOXING COACH", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("BOXING COACH", WIN_W, WIN_H)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        now = time.perf_counter()
        if args.mirror:
            frame = cv2.flip(frame, 1)

        frame_h, frame_w = frame.shape[:2]
        cam_frame = cv2.resize(frame, (CAM_W, WIN_H), interpolation=cv2.INTER_AREA)
        pose = infer_pose(inferencer, frame)
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
                model_label,
                confidence,
                gap,
                rule_label,
                rule_confidence,
                float(rule_debug.get("margin", 0.0)),
                not args.disable_rule,
            )
            if args.debug_events:
                rule_scores = rule_debug.get("scores", {})
                print(
                    "event "
                    f"model={model_label} conf={confidence:.2f} gap={gap:.2f} "
                    f"rule={rule_label} rconf={rule_confidence:.2f} rmargin={rule_debug.get('margin', 0.0):.2f} "
                    f"fused={label} side={event.active_side} "
                    f"scores={rule_scores}",
                    flush=True,
                )
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
            display_confidence = confidence

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
            canvas,
            classes,
            probs_last,
            display_label,
            raw_label,
            display_confidence,
            gap,
            energy,
            phase,
            side,
            counts,
            recent,
            fps,
            True,
            args.mirror,
        )

        cv2.imshow("BOXING COACH", canvas)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("r"):
            for name in counts:
                counts[name] = 0
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
