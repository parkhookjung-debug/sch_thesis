from __future__ import annotations

import argparse
import csv
import shutil
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


PUNCH_BGR = {
    "none": (130, 130, 130),
    "jab": (0, 220, 255),
    "cross": (40, 160, 255),
    "hook": (255, 50, 200),
    "uppercut": (50, 255, 100),
}

C_BG = (18, 13, 11)
C_PANEL = (28, 21, 19)
C_BORDER = (70, 64, 60)
C_TEXT = (245, 244, 244)
C_DIM = (150, 145, 142)
C_ACCENT = (87, 61, 255)
C_GOOD = (60, 230, 120)
C_WARN = (0, 190, 255)

WIN_W, WIN_H = 1280, 760
VID_MAX_H = 570
TL_X, TL_Y, TL_W, TL_H = 8, 586, 1264, 30
LIST_Y = 628
HINT_Y = 735

KEY_TO_LABEL = {
    ord("n"): "none",
    ord("0"): "none",
    ord("j"): "jab",
    ord("c"): "cross",
    ord("h"): "hook",
    ord("u"): "uppercut",
    ord("1"): "jab",
    ord("2"): "cross",
    ord("3"): "hook",
    ord("4"): "uppercut",
}


@dataclass
class Segment:
    video_id: str
    start_frame: int
    apex_frame: int
    end_frame: int
    label: str


_mouse_x = -1
_mouse_clicked = False


def _on_mouse(event, x, y, flags, param):
    global _mouse_x, _mouse_clicked
    if event == cv2.EVENT_LBUTTONDOWN and TL_Y <= y <= TL_Y + TL_H:
        _mouse_x = x
        _mouse_clicked = True


def load_segments(path: Path) -> list[Segment]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        segments = []
        for row in reader:
            if {"video_id", "start_frame", "apex_frame", "end_frame", "label"}.issubset(row):
                segments.append(
                    Segment(
                        row["video_id"],
                        int(row["start_frame"]),
                        int(row["apex_frame"]),
                        int(row["end_frame"]),
                        row["label"],
                    )
                )
            elif {"frame_number", "punch_type"}.issubset(row):
                frame = int(row["frame_number"])
                label = row["punch_type"]
                video_id = path.stem.replace("_labels", "")
                segments.append(Segment(video_id, frame, frame, frame, label))
        return segments


def backup_existing(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(path, backup_dir / f"{path.stem}_{stamp}{path.suffix}")


def save_segments(path: Path, segments: list[Segment], backup: bool = True) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup:
        backup_existing(path)
    rows = sorted(segments, key=lambda item: (item.video_id, item.apex_frame, item.start_frame))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["video_id", "start_frame", "apex_frame", "end_frame", "label"],
        )
        writer.writeheader()
        for item in rows:
            writer.writerow(item.__dict__)
    return len(rows)


def nearest_segment_index(segments: list[Segment], video_id: str, frame: int, win: int = 8) -> int | None:
    best_idx = None
    best_dist = win + 1
    for idx, item in enumerate(segments):
        if item.video_id != video_id:
            continue
        dist = abs(item.apex_frame - frame)
        if dist < best_dist:
            best_idx = idx
            best_dist = dist
    return best_idx


def draw_text(img, text: str, org: tuple[int, int], scale: float, color, thickness: int = 1) -> None:
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def fit_video(frame: np.ndarray) -> tuple[np.ndarray, int, int, int, int]:
    fh, fw = frame.shape[:2]
    scale = min(WIN_W / fw, VID_MAX_H / fh)
    nw, nh = int(fw * scale), int(fh * scale)
    ox = (WIN_W - nw) // 2
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    return resized, ox, 0, nw, nh


def render(
    canvas: np.ndarray,
    frame: np.ndarray,
    segments: list[Segment],
    video_id: str,
    fidx: int,
    total: int,
    playing: bool,
    speed: float,
    out_path: Path,
    msg: str,
    mode: str,
    temp_start: int | None,
    temp_apex: int | None,
) -> None:
    canvas[:] = C_BG
    video, ox, oy, nw, nh = fit_video(frame)
    canvas[oy : oy + nh, ox : ox + nw] = video

    video_segments = [item for item in segments if item.video_id == video_id]
    current_idx = nearest_segment_index(segments, video_id, fidx, win=3)
    if current_idx is not None:
        item = segments[current_idx]
        col = PUNCH_BGR.get(item.label, C_ACCENT)
        cv2.rectangle(canvas, (ox, oy), (ox + nw, oy + nh), col, 8)
        draw_text(canvas, item.label.upper(), (ox + 18, oy + 40), 0.9, col, 2)

    if temp_start is not None:
        draw_text(canvas, f"START {temp_start}", (ox + 18, oy + 76), 0.7, C_GOOD, 2)
    if temp_apex is not None:
        draw_text(canvas, f"APEX {temp_apex}", (ox + 18, oy + 108), 0.7, C_WARN, 2)

    status = f"{'PLAY' if playing else 'PAUSE'}  {fidx:04d}/{max(total - 1, 0):04d}  x{speed:.2f}  {video_id}  labels:{len(video_segments)}  mode:{mode}"
    draw_text(canvas, status, (10, VID_MAX_H - 22), 0.58, C_TEXT, 1)
    if msg:
        draw_text(canvas, msg, (780, VID_MAX_H - 22), 0.58, C_ACCENT, 1)

    cv2.rectangle(canvas, (TL_X, TL_Y), (TL_X + TL_W, TL_Y + TL_H), (38, 33, 31), -1)
    cv2.rectangle(canvas, (TL_X, TL_Y), (TL_X + TL_W, TL_Y + TL_H), C_BORDER, 1)
    prog_w = int(TL_W * fidx / max(total - 1, 1))
    cv2.rectangle(canvas, (TL_X, TL_Y), (TL_X + prog_w, TL_Y + TL_H), (48, 44, 42), -1)

    for item in video_segments:
        mx = TL_X + int(TL_W * item.apex_frame / max(total - 1, 1))
        col = PUNCH_BGR.get(item.label, C_ACCENT)
        cv2.circle(canvas, (mx, TL_Y + TL_H // 2), 5, col, -1)
        start_x = TL_X + int(TL_W * item.start_frame / max(total - 1, 1))
        end_x = TL_X + int(TL_W * item.end_frame / max(total - 1, 1))
        cv2.line(canvas, (start_x, TL_Y + TL_H - 4), (end_x, TL_Y + TL_H - 4), col, 2)

    cx = TL_X + int(TL_W * fidx / max(total - 1, 1))
    cv2.line(canvas, (cx, TL_Y - 3), (cx, TL_Y + TL_H + 3), (255, 255, 255), 2)

    draw_text(canvas, "RECENT", (10, LIST_Y), 0.45, C_DIM)
    for i, item in enumerate(reversed(video_segments[-10:])):
        col = PUNCH_BGR.get(item.label, C_ACCENT)
        text = f"{item.start_frame:04d}-{item.apex_frame:04d}-{item.end_frame:04d}  {item.label}"
        draw_text(canvas, text, (10, LIST_Y + 22 + i * 18), 0.48, col)

    count_x = 980
    draw_text(canvas, "COUNT", (count_x, LIST_Y), 0.45, C_DIM)
    for i, label in enumerate(["none", "jab", "cross", "hook", "uppercut"]):
        cnt = sum(1 for item in video_segments if item.label == label)
        draw_text(canvas, f"{label:8s} {cnt:3d}", (count_x, LIST_Y + 22 + i * 20), 0.52, PUNCH_BGR[label])
    draw_text(canvas, out_path.name, (count_x, LIST_Y + 116), 0.45, C_DIM)

    hints = [
        "Space play",
        "A/D 1f",
        "F/G 10f",
        "S start",
        "P apex",
        "E end+label",
        "N none",
        "J/C/H/U quick",
        "BS del",
        "[/] speed",
        "W save",
        "Q quit",
    ]
    x = 10
    for hint in hints:
        draw_text(canvas, hint, (x, HINT_Y), 0.42, C_DIM)
        x += int(len(hint) * 8.2) + 18


def main() -> None:
    global _mouse_clicked, _mouse_x

    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--output", default=Path("data/labels/labels.csv"), type=Path)
    parser.add_argument("--speed", default=1.0, type=float)
    parser.add_argument("--fresh", action="store_true", help="Clear labels for this video only.")
    parser.add_argument("--quick-radius", default=8, type=int, help="Segment radius for J/C/H/U quick apex labels.")
    args = parser.parse_args()

    video_id = args.video.stem
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video: {args.video}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    speed = args.speed

    all_segments = load_segments(args.output)
    if args.fresh:
        all_segments = [item for item in all_segments if item.video_id != video_id]

    cache: OrderedDict[int, np.ndarray] = OrderedDict()

    def get_frame(idx: int):
        if idx in cache:
            return cache[idx]
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            return None
        if len(cache) >= 500:
            cache.popitem(last=False)
        cache[idx] = frame.copy()
        return frame

    canvas = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)
    fidx = 0
    playing = False
    msg = ""
    msg_ttl = 0
    temp_start: int | None = None
    temp_apex: int | None = None

    cv2.namedWindow("Punch Labeler", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Punch Labeler", WIN_W, WIN_H)
    cv2.setMouseCallback("Punch Labeler", _on_mouse)

    while True:
        frame = get_frame(fidx)
        if frame is None:
            break

        mode = "segment" if temp_start is not None else "quick"
        render(
            canvas,
            frame,
            all_segments,
            video_id,
            fidx,
            total,
            playing,
            speed,
            args.output,
            msg if msg_ttl > 0 else "",
            mode,
            temp_start,
            temp_apex,
        )
        msg_ttl = max(0, msg_ttl - 1)
        cv2.imshow("Punch Labeler", canvas)

        delay = max(1, int(1000 / fps / speed)) if playing else 30
        key = cv2.waitKey(delay)

        if _mouse_clicked:
            fidx = max(0, min(total - 1, int(((_mouse_x - TL_X) / TL_W) * (total - 1))))
            playing = False
            _mouse_clicked = False
            continue

        if playing:
            fidx = min(total - 1, fidx + 1)
            if fidx >= total - 1:
                playing = False
            if key == -1:
                continue

        if key == -1:
            continue

        k = key & 0xFF
        if k in (ord("q"), 27):
            n = save_segments(args.output, all_segments)
            print(f"saved {n} labels -> {args.output}")
            break
        if k == ord(" "):
            playing = not playing
        elif k in (ord("a"), 81):
            fidx = max(0, fidx - 1)
            playing = False
        elif k in (ord("d"), 83):
            fidx = min(total - 1, fidx + 1)
            playing = False
        elif k == ord("f"):
            fidx = max(0, fidx - 10)
            playing = False
        elif k == ord("g"):
            fidx = min(total - 1, fidx + 10)
            playing = False
        elif k == ord("["):
            speed = max(0.25, speed - 0.25)
        elif k == ord("]"):
            speed = min(4.0, speed + 0.25)
        elif k == ord("s"):
            temp_start = fidx
            temp_apex = None
            msg = f"start {fidx}"
            msg_ttl = 50
            playing = False
        elif k == ord("p") and temp_start is not None:
            temp_apex = fidx
            msg = f"apex {fidx}"
            msg_ttl = 50
            playing = False
        elif k == ord("e") and temp_start is not None:
            end = fidx
            start = min(temp_start, end)
            end = max(temp_start, end)
            apex = temp_apex if temp_apex is not None else fidx
            apex = max(start, min(end, apex))
            msg = "press N/J/C/H/U or 0/1/2/3/4"
            msg_ttl = 100
            render(canvas, frame, all_segments, video_id, fidx, total, False, speed, args.output, msg, "label", temp_start, apex)
            cv2.imshow("Punch Labeler", canvas)
            while True:
                label_key = cv2.waitKey(0) & 0xFF
                if label_key in KEY_TO_LABEL:
                    label = KEY_TO_LABEL[label_key]
                    all_segments.append(Segment(video_id, start, apex, end, label))
                    msg = f"+ {label} {start}-{apex}-{end}"
                    print(msg)
                    msg_ttl = 80
                    temp_start = None
                    temp_apex = None
                    break
                if label_key == 27:
                    msg = "cancelled"
                    msg_ttl = 50
                    break
            playing = False
        elif k in KEY_TO_LABEL:
            label = KEY_TO_LABEL[k]
            radius = args.quick_radius
            all_segments.append(
                Segment(
                    video_id,
                    max(0, fidx - radius),
                    fidx,
                    min(total - 1, fidx + radius),
                    label,
                )
            )
            msg = f"+ {label} @ {fidx}"
            msg_ttl = 60
            print(msg)
        elif k == 8:
            idx = nearest_segment_index(all_segments, video_id, fidx)
            if idx is not None:
                item = all_segments.pop(idx)
                msg = f"removed {item.label} @ {item.apex_frame}"
                msg_ttl = 60
                print(msg)
        elif k == ord("w"):
            n = save_segments(args.output, all_segments)
            msg = f"saved {n}"
            msg_ttl = 80
            print(f"saved {n} labels -> {args.output}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
