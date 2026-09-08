"""
프레임 위에 스켈레톤 / 펀치 카운터 / 자세 점수 패널을 합성.

원본: LIM coach 4 의 draw_* 함수들 — opencv only 로 단순화.
한글 표시는 OS 폰트(Pillow)가 있을 때만 활성화.
"""
from __future__ import annotations

import cv2
import numpy as np

from .keypoints import COCO_CONN
from .posture import PostureResult
from .punch_detector import PUNCH_COLORS
from ..config import VIS_MIN

try:
    from PIL import Image as PILImage, ImageDraw, ImageFont

    def _font(size):
        for p in ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/gulim.ttc"):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
        return ImageFont.load_default()

    _F_SM = _font(16)
    _F_MD = _font(24)
    _F_LG = _font(38)
    _PIL_OK = True
except Exception:
    _PIL_OK = False


def _draw_kr(frame, text, pos, color_bgr, font=None):
    if not _PIL_OK:
        cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.65, color_bgr, 2)
        return
    pil = PILImage.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)
    r, g, b = color_bgr[2], color_bgr[1], color_bgr[0]
    draw.text(pos, text, font=font or _F_MD, fill=(r, g, b))
    frame[:] = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def draw_skeleton(frame, kp, sc, color=(0, 200, 255)):
    for a, b in COCO_CONN:
        if sc[a] > VIS_MIN and sc[b] > VIS_MIN:
            cv2.line(frame,
                     (int(kp[a][0]), int(kp[a][1])),
                     (int(kp[b][0]), int(kp[b][1])),
                     (80, 80, 80), 2)
    for i in range(17):
        if sc[i] > VIS_MIN:
            cv2.circle(frame, (int(kp[i][0]), int(kp[i][1])), 4, color, -1)


def draw_counter(frame, counts: dict[str, int]):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 60), (8, 8, 20), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    x = 10
    for pt, color in PUNCH_COLORS.items():
        _draw_kr(frame, f"{pt[:2].upper()} {counts.get(pt, 0):03d}", (x, 8), color, font=_F_MD if _PIL_OK else None)
        x += w // 4


def draw_posture(frame, posture: PostureResult, coach_label: str | None = None):
    h, w = frame.shape[:2]
    px, py = 10, h - 200
    overlay = frame.copy()
    cv2.rectangle(overlay, (px - 5, py - 30), (px + 260, h - 5), (15, 15, 25), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    if coach_label:
        _draw_kr(frame, coach_label, (px, py - 26), (200, 200, 220), font=_F_SM if _PIL_OK else None)

    y = py
    for item in posture.items:
        bw = 180
        cv2.rectangle(frame, (px, y), (px + bw, y + 10), (50, 50, 60), -1)
        cv2.rectangle(frame, (px, y),
                      (px + int(bw * item.score / max(item.max_score, 1)), y + 10),
                      item.color_bgr, -1)
        _draw_kr(frame, f"{item.label}: {item.score}/{item.max_score}",
                 (px, y - 18), (200, 200, 200), font=_F_SM if _PIL_OK else None)
        y += 38

    _draw_kr(frame, f"TOTAL {posture.total}/100  [{posture.grade}]",
             (px, y), posture.grade_color, font=_F_MD if _PIL_OK else None)


def draw_punch_flash(frame, punch_type: str, age: float, duration: float = 0.6):
    """펀치 직후 큰 텍스트로 어떤 펀치였는지 잠깐 띄움."""
    if age > duration:
        return
    alpha = max(0.0, 1.0 - age / duration)
    h, w = frame.shape[:2]
    color = PUNCH_COLORS.get(punch_type, (255, 255, 255))
    text = punch_type.upper()
    if _PIL_OK:
        pil = PILImage.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil)
        r, g, b = color[2], color[1], color[0]
        draw.text((w // 2 - 100, 80), text, font=_F_LG, fill=(r, g, b))
        frame[:] = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    else:
        cv2.putText(frame, text, (w // 2 - 100, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, color, 4)
