"""
자세 점수 계산 — 코치 DNA(자세 평균)를 기준으로 0~100점.

원본: LIM coach 4.py 의 calc_posture(). 코치별 DNA 를 인자로 받게 일반화.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .keypoints import (
    KP_L_HI, KP_L_SH, KP_NOSE, KP_R_HI, KP_R_SH,
    arm_indices, shoulder_width_px,
)
from ..config import VIS_MIN


@dataclass
class ScoreItem:
    label: str
    score: int
    max_score: int
    message: str
    color_bgr: tuple[int, int, int]


@dataclass
class PostureResult:
    total: int
    grade: str
    grade_color: tuple[int, int, int]
    items: list[ScoreItem]
    issues: list[tuple[int, str, str, int, tuple[int, int, int]]]  # (priority, fb_text, voice, deficit, color)


def _partial(err: float, mx: int, tol: float) -> int:
    if abs(err) <= tol:
        return mx
    return max(0, int(mx * max(0.0, 1.0 - (abs(err) - tol) / tol)))


def calc_posture(
    kp: np.ndarray,
    sc: np.ndarray,
    coach_dna: dict,
    facing_right: bool = True,
) -> Optional[PostureResult]:
    """Return scored posture or None if keypoints are too unreliable."""
    if sc[KP_L_SH] < VIS_MIN or sc[KP_R_SH] < VIS_MIN:
        return None

    JAB_WR, JAB_SH, JAB_EL, CROSS_WR, CROSS_SH, CROSS_EL = arm_indices(facing_right)
    sw = shoulder_width_px(kp)
    sh_y = (kp[KP_L_SH][1] + kp[KP_R_SH][1]) / 2

    issues: list[tuple[int, str, str, int, tuple[int, int, int]]] = []

    # ── 가드 높이 (35점) ──
    l_ydiff = (kp[JAB_WR][1] - kp[JAB_SH][1]) / sw
    r_ydiff = (kp[CROSS_WR][1] - kp[CROSS_SH][1]) / sw
    ref_l = coach_dna.get("guard_l_ydiff", -0.15)
    ref_r = coach_dna.get("guard_r_ydiff", -0.10)
    tol_g = 0.25
    l_err, r_err = l_ydiff - ref_l, r_ydiff - ref_r
    l_score = _partial(l_err, 18, tol_g)
    r_score = _partial(r_err, 17, tol_g)
    guard_score = l_score + r_score
    if l_score < 18:
        issues.append((0, "잽 가드 올려" if l_err > 0 else "잽 가드 내려",
                       "잽손 올려!" if l_err > 0 else "잽손 내려!",
                       18 - l_score, (0, 60, 255)))
    if r_score < 17:
        issues.append((0, "크로스 가드 올려" if r_err > 0 else "크로스 가드 내려",
                       "크로스손 올려!" if r_err > 0 else "크로스손 내려!",
                       17 - r_score, (0, 60, 255)))
    if l_score == 18 and r_score == 17:
        guard_msg, guard_col = "Guard 좋아!", (0, 220, 100)
    elif l_score < 18 and r_score < 17:
        guard_msg, guard_col = "양손 가드 조정", (0, 60, 255)
    elif l_score < 18:
        guard_msg = "잽손 가드 내려감" if l_err > 0 else "잽손 너무 높음"
        guard_col = (0, 60, 255)
    else:
        guard_msg = "크로스손 가드 내려감" if r_err > 0 else "크로스손 너무 높음"
        guard_col = (0, 60, 255)

    # ── 린 포워드 (25점) ──
    lean_score = 0
    lean_msg, lean_col = "엉덩이 미감지", (120, 120, 120)
    hi_ok = sc[KP_L_HI] > VIS_MIN and sc[KP_R_HI] > VIS_MIN
    if hi_ok:
        sh_cx = (kp[KP_L_SH][0] + kp[KP_R_SH][0]) / 2
        hi_cx = (kp[KP_L_HI][0] + kp[KP_R_HI][0]) / 2
        lean = (sh_cx - hi_cx) / sw
        ref_lf = coach_dna.get("lean_forward", 0.05)
        tol_lean = 0.12
        lean_err = lean - ref_lf
        lean_score = _partial(lean_err, 25, tol_lean)
        if lean_score == 25:
            lean_msg = f"상체 기울기 좋아! ({lean:+.2f})"
            lean_col = (0, 220, 100)
        elif lean_err < 0:
            lean_msg = f"앞으로 더 기울여 ({lean:+.2f})"
            lean_col = (0, 165, 255)
            issues.append((1, "앞으로 기울여", lean_msg, 25 - lean_score, lean_col))
        else:
            lean_msg = f"상체 너무 앞으로 ({lean:+.2f})"
            lean_col = (0, 165, 255)
            issues.append((1, "상체 세워", lean_msg, 25 - lean_score, lean_col))

    # ── 머리 자세 (20점) ──
    head_y = (kp[KP_NOSE][1] - sh_y) / sw
    head_err = head_y - coach_dna.get("head_y_ratio", -0.85)
    head_score = 20 if abs(head_err) < 0.18 else 10 if abs(head_err) < 0.30 else 0
    if abs(head_err) < 0.18:
        head_msg, head_col = "머리 자세 좋아!", (0, 220, 100)
    elif head_err > 0:
        head_msg, head_col = "고개 들어!", (0, 165, 255)
        issues.append((2, "고개 드세요", "고개 들어!", 20 - head_score, head_col))
    else:
        head_msg, head_col = "턱 당겨!", (0, 165, 255)
        issues.append((2, "턱 당기세요", "턱 당겨!", 20 - head_score, head_col))

    # ── 팔꿈치 (20점) ──
    l_el_y = (kp[JAB_EL][1] - kp[JAB_SH][1]) / sw
    r_el_y = (kp[CROSS_EL][1] - kp[CROSS_SH][1]) / sw
    el_ok_l = (l_el_y > l_ydiff) and (l_el_y < 0.60)
    el_ok_r = (r_el_y > r_ydiff) and (r_el_y < 0.60)
    elbow_score = (10 if el_ok_l else 0) + (10 if el_ok_r else 0)
    if el_ok_l and el_ok_r:
        el_msg, el_col = "팔꿈치 자세 좋아!", (0, 220, 100)
    elif not el_ok_l:
        if l_el_y >= 0.60:
            el_msg = "잽 팔꿈치 올려!"
            issues.append((3, "잽 팔꿈치 올려", "팔꿈치 올려!", 10, (0, 165, 255)))
        else:
            el_msg = "잽 팔꿈치 내려!"
            issues.append((3, "잽 팔꿈치 내려", "팔꿈치 내려!", 10, (0, 165, 255)))
        el_col = (0, 165, 255)
    else:
        if r_el_y >= 0.60:
            el_msg = "크로스 팔꿈치 올려!"
            issues.append((3, "크로스 팔꿈치 올려", "팔꿈치 올려!", 10, (0, 165, 255)))
        else:
            el_msg = "크로스 팔꿈치 내려!"
            issues.append((3, "크로스 팔꿈치 내려", "팔꿈치 내려!", 10, (0, 165, 255)))
        el_col = (0, 165, 255)

    total = guard_score + lean_score + head_score + elbow_score
    if total >= 85:
        grade, gcol = "S", (0, 255, 120)
    elif total >= 70:
        grade, gcol = "A", (0, 200, 255)
    elif total >= 50:
        grade, gcol = "B", (0, 165, 255)
    else:
        grade, gcol = "C", (0, 60, 255)

    items = [
        ScoreItem("가드",     guard_score, 35, guard_msg, guard_col),
        ScoreItem("린포워드", lean_score,  25, lean_msg,  lean_col),
        ScoreItem("머리",     head_score,  20, head_msg,  head_col),
        ScoreItem("팔꿈치",   elbow_score, 20, el_msg,    el_col),
    ]
    return PostureResult(total=total, grade=grade, grade_color=gcol,
                         items=items, issues=issues)
