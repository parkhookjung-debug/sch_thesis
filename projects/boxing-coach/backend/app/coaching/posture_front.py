"""
정면 카메라용 자세 점수.

측면용(`posture.py`)과 다르게:
- lean_forward 제거 → 점수 배분 재구성
- 가드 X(얼굴 가드), shoulder/hip tilt, 어깨-골반 회전 비율 추가
- 무릎/발목이 안 보이면 stance 항목은 보류(점수 N/A) — 카메라가 상반신만이어도 동작
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .keypoints import (
    KP_L_AN, KP_L_EL, KP_L_HI, KP_L_KN, KP_L_SH, KP_L_WR,
    KP_NOSE,
    KP_R_AN, KP_R_EL, KP_R_HI, KP_R_KN, KP_R_SH, KP_R_WR,
    angle3pt,
)
from .posture import PostureResult, ScoreItem
from ..config import VIS_MIN


def _partial(err: float, mx: int, tol: float) -> int:
    if abs(err) <= tol:
        return mx
    return max(0, int(mx * max(0.0, 1.0 - (abs(err) - tol) / tol)))


def calc_posture_front(
    kp: np.ndarray,
    sc: np.ndarray,
    coach_dna: dict,
) -> Optional[PostureResult]:
    """정면 자세 점수. coach_dna 는 `*_DNA_front.csv` 로드 결과."""
    if sc[KP_L_SH] < VIS_MIN or sc[KP_R_SH] < VIS_MIN:
        return None
    if sc[KP_L_WR] < VIS_MIN or sc[KP_R_WR] < VIS_MIN:
        return None

    sw = abs(kp[KP_L_SH][0] - kp[KP_R_SH][0]) + 1e-6  # 정면 어깨폭 = X
    sh_cx = (kp[KP_L_SH][0] + kp[KP_R_SH][0]) / 2
    sh_cy = (kp[KP_L_SH][1] + kp[KP_R_SH][1]) / 2

    issues: list[tuple[int, str, str, int, tuple[int, int, int]]] = []

    # ── 가드 Y (30점) — 양손 손목 높이 ──
    l_y = (kp[KP_L_WR][1] - kp[KP_L_SH][1]) / sw
    r_y = (kp[KP_R_WR][1] - kp[KP_R_SH][1]) / sw
    ref_l = coach_dna.get("guard_l_y", -0.4)
    ref_r = coach_dna.get("guard_r_y", -0.4)
    tol_y = 0.30
    l_err, r_err = l_y - ref_l, r_y - ref_r
    l_s = _partial(l_err, 15, tol_y)
    r_s = _partial(r_err, 15, tol_y)
    guard_y_score = l_s + r_s
    if l_s < 15:
        issues.append((0, "왼손 가드 " + ("올려" if l_err > 0 else "내려"),
                       "왼손 " + ("올려!" if l_err > 0 else "내려!"),
                       15 - l_s, (0, 60, 255)))
    if r_s < 15:
        issues.append((0, "오른손 가드 " + ("올려" if r_err > 0 else "내려"),
                       "오른손 " + ("올려!" if r_err > 0 else "내려!"),
                       15 - r_s, (0, 60, 255)))
    if l_s == 15 and r_s == 15:
        guard_y_msg, guard_y_col = "가드 높이 좋아!", (0, 220, 100)
    else:
        guard_y_msg, guard_y_col = "가드 높이 조정", (0, 60, 255)

    # ── 가드 X (20점) — 얼굴 앞에 모여 있나 ──
    l_xc = (kp[KP_L_WR][0] - sh_cx) / sw
    r_xc = (kp[KP_R_WR][0] - sh_cx) / sw
    ref_lx = coach_dna.get("guard_l_xcenter", 0.2)
    ref_rx = coach_dna.get("guard_r_xcenter", -0.2)
    tol_x = 0.30
    lx_s = _partial(l_xc - ref_lx, 10, tol_x)
    rx_s = _partial(r_xc - ref_rx, 10, tol_x)
    guard_x_score = lx_s + rx_s
    if guard_x_score == 20:
        guard_x_msg, guard_x_col = "양손이 얼굴을 잘 가려요", (0, 220, 100)
    else:
        guard_x_msg = "양손이 너무 벌어졌어요"
        guard_x_col = (0, 60, 255)
        issues.append((1, "가드 좁혀", "가드 좁혀!", 20 - guard_x_score, guard_x_col))

    # ── 어깨/골반 균형 (20점) ──
    sh_tilt = (kp[KP_R_SH][1] - kp[KP_L_SH][1]) / sw
    sh_ref = coach_dna.get("shoulder_tilt", 0.0)
    sh_err = sh_tilt - sh_ref
    sh_score = _partial(sh_err, 10, 0.15)

    hip_ok = sc[KP_L_HI] > VIS_MIN and sc[KP_R_HI] > VIS_MIN
    if hip_ok:
        hip_tilt = (kp[KP_R_HI][1] - kp[KP_L_HI][1]) / sw
        hip_err = hip_tilt - coach_dna.get("hip_tilt", 0.0)
        hip_score = _partial(hip_err, 10, 0.15)
    else:
        hip_score = 5  # 보이지 않으면 중간값
    balance_score = sh_score + hip_score
    if balance_score >= 18:
        bal_msg, bal_col = "균형 좋아!", (0, 220, 100)
    elif sh_score < 7:
        bal_msg, bal_col = "어깨가 한쪽으로 기울었어요", (0, 165, 255)
        issues.append((2, "어깨 수평", "어깨 수평!", 20 - balance_score, bal_col))
    else:
        bal_msg, bal_col = "골반 정렬을 신경쓰세요", (0, 165, 255)

    # ── 머리 (15점) ──
    head_y = (kp[KP_NOSE][1] - sh_cy) / sw
    head_err = head_y - coach_dna.get("head_y_ratio", -1.0)
    head_score = 15 if abs(head_err) < 0.25 else 8 if abs(head_err) < 0.45 else 0
    if abs(head_err) < 0.25:
        head_msg, head_col = "머리 자세 좋아!", (0, 220, 100)
    elif head_err > 0:
        head_msg, head_col = "고개 들어!", (0, 165, 255)
        issues.append((3, "고개 드세요", "고개 들어!", 15 - head_score, head_col))
    else:
        head_msg, head_col = "턱 당겨!", (0, 165, 255)
        issues.append((3, "턱 당기세요", "턱 당겨!", 15 - head_score, head_col))

    # ── 스탠스 (15점, 보일 때만) ──
    lower_visible = all(sc[i] > VIS_MIN for i in (KP_L_KN, KP_R_KN, KP_L_AN, KP_R_AN, KP_L_HI, KP_R_HI))
    if lower_visible:
        stance = abs(kp[KP_L_AN][0] - kp[KP_R_AN][0]) / sw
        stance_err = stance - coach_dna.get("stance_step_x", 1.2)
        st_score = _partial(stance_err, 7, 0.5)
        # 무릎
        kn_l = angle3pt(kp[KP_L_HI][0], kp[KP_L_HI][1], kp[KP_L_KN][0], kp[KP_L_KN][1],
                        kp[KP_L_AN][0], kp[KP_L_AN][1])
        kn_r = angle3pt(kp[KP_R_HI][0], kp[KP_R_HI][1], kp[KP_R_KN][0], kp[KP_R_KN][1],
                        kp[KP_R_AN][0], kp[KP_R_AN][1])
        kn_avg = (kn_l + kn_r) / 2
        kn_err = kn_avg - (coach_dna.get("knee_bend_l", 160) + coach_dna.get("knee_bend_r", 160)) / 2
        kn_score = _partial(kn_err, 8, 25.0)
        stance_score = st_score + kn_score
        if stance_score >= 12:
            st_msg, st_col = "스탠스 좋아!", (0, 220, 100)
        else:
            st_msg, st_col = "스탠스/무릎 조정", (0, 165, 255)
            issues.append((4, "스탠스 조정", "스탠스 조정", 15 - stance_score, st_col))
    else:
        stance_score = 0
        st_msg, st_col = "하체 미감지", (120, 120, 120)

    total = guard_y_score + guard_x_score + balance_score + head_score + stance_score
    if total >= 85:
        grade, gcol = "S", (0, 255, 120)
    elif total >= 70:
        grade, gcol = "A", (0, 200, 255)
    elif total >= 50:
        grade, gcol = "B", (0, 165, 255)
    else:
        grade, gcol = "C", (0, 60, 255)

    items = [
        ScoreItem("가드 높이",  guard_y_score, 30, guard_y_msg, guard_y_col),
        ScoreItem("가드 위치",  guard_x_score, 20, guard_x_msg, guard_x_col),
        ScoreItem("어깨/골반",  balance_score, 20, bal_msg,     bal_col),
        ScoreItem("머리",       head_score,    15, head_msg,    head_col),
        ScoreItem("스탠스",     stance_score,  15, st_msg,      st_col),
    ]
    return PostureResult(total=total, grade=grade, grade_color=gcol,
                         items=items, issues=issues)
