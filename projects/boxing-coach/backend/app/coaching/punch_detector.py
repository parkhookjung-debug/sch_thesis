"""
실시간 비디오 스트림에서 펀치 감지 — falling-edge 기반.

원본: LIM coach 4.py 의 update_punch_detect / classify_from_buf / analyse_punch.
프레임 단위로 호출하면 펀치 이벤트를 누적하고, 이벤트 객체를 yield 한다.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .keypoints import (
    KP_L_HI, KP_L_SH, KP_R_HI, KP_R_SH,
    angle3pt, arm_indices, shoulder_width_px,
)
from ..config import VIS_MIN

PUNCH_TYPES = ("jab", "cross", "hook", "uppercut")

PUNCH_COLORS = {
    "jab":      (0, 220, 255),
    "cross":    (255, 160, 40),
    "hook":     (200, 50, 255),
    "uppercut": (100, 255, 50),
}

# 펀치 감지 파라미터 (LIM coach 4 와 동일)
_BUF_SZ = 12
PUNCH_CD = 0.55       # 같은 손 연속 펀치 사이 최소 시간
VEL_START = 0.15      # 감지 시작 속도 (shoulder-width 단위)
DOM_RATIO = 1.35      # 한 손이 다른 손보다 N배 빨라야 그 손의 펀치로 판정

HOOK_ELBOW_THRESH = 0.05
HOOK_ELBOW_ANGLE = 110.0
HOOK_MIN_FRAMES = 3
UPPER_RISE_THRESH = 0.20
UPPER_ELBOW_ANGLE = 120.0
UPPER_ELBOW_LOW = 0.15


@dataclass
class PunchEvent:
    frame_number: int
    timestamp: float
    side: str              # 'lead' or 'rear'
    punch_type: str        # 'jab' / 'cross' / 'hook' / 'uppercut'
    arm_extension: float
    elbow_angle: float
    lean_forward: float


@dataclass
class PunchDetectorState:
    facing_right: bool = True
    v_lead: deque = field(default_factory=lambda: deque(maxlen=_BUF_SZ))
    v_rear: deque = field(default_factory=lambda: deque(maxlen=_BUF_SZ))
    el_lead: deque = field(default_factory=lambda: deque(maxlen=_BUF_SZ))
    el_rear: deque = field(default_factory=lambda: deque(maxlen=_BUF_SZ))
    ea_lead: deque = field(default_factory=lambda: deque(maxlen=_BUF_SZ))
    ea_rear: deque = field(default_factory=lambda: deque(maxlen=_BUF_SZ))
    wy_lead: deque = field(default_factory=lambda: deque(maxlen=_BUF_SZ))
    wy_rear: deque = field(default_factory=lambda: deque(maxlen=_BUF_SZ))
    lm_buf: deque = field(default_factory=lambda: deque(maxlen=30))
    prev_v_lead: float = 0.0
    prev_v_rear: float = 0.0
    prev_lead_wr: Optional[tuple[float, float]] = None
    prev_rear_wr: Optional[tuple[float, float]] = None
    last_lead_time: float = -10.0
    last_rear_time: float = -10.0
    counts: dict[str, int] = field(default_factory=lambda: {t: 0 for t in PUNCH_TYPES})


def _classify_from_buf(side: str, sw: float, el_buf, ea_buf, wy_buf) -> str:
    min_el = min(el_buf) if el_buf else 1.0
    min_ea = min(ea_buf) if ea_buf else 180.0
    wy_list = list(wy_buf)
    if wy_list:
        rise = (wy_list[0] - min(wy_list)) / (sw + 1e-6)
        if rise > UPPER_RISE_THRESH and min_ea < UPPER_ELBOW_ANGLE and min_el > UPPER_ELBOW_LOW:
            return "uppercut"
    hook_frames = sum(1 for el, ea in zip(el_buf, ea_buf)
                      if el < HOOK_ELBOW_THRESH and ea < HOOK_ELBOW_ANGLE)
    if hook_frames >= HOOK_MIN_FRAMES:
        return "hook"
    return "jab" if side == "lead" else "cross"


def _build_punch_event(
    state: PunchDetectorState,
    frame_number: int,
    timestamp: float,
    side: str,
    punch_type: str,
) -> Optional[PunchEvent]:
    """가장 팔이 가장 많이 뻗어 있는 프레임에서 메트릭을 추출."""
    if len(state.lm_buf) < 3:
        return None
    JAB_WR, JAB_SH, JAB_EL, CROSS_WR, CROSS_SH, CROSS_EL = arm_indices(state.facing_right)
    wr_i = JAB_WR if side == "lead" else CROSS_WR
    sh_i = JAB_SH if side == "lead" else CROSS_SH
    el_i = JAB_EL if side == "lead" else CROSS_EL

    best_kp = None
    best_sc = None
    best_d = -1.0
    for kp, sc in state.lm_buf:
        if sc[wr_i] < VIS_MIN or sc[sh_i] < VIS_MIN:
            continue
        d = math.sqrt((kp[wr_i][0] - kp[sh_i][0]) ** 2 + (kp[wr_i][1] - kp[sh_i][1]) ** 2)
        if d > best_d:
            best_d, best_kp, best_sc = d, kp, sc
    if best_kp is None:
        return None

    sw = shoulder_width_px(best_kp)
    sh_cx = (best_kp[KP_L_SH][0] + best_kp[KP_R_SH][0]) / 2
    hi_ok = best_sc[KP_L_HI] > VIS_MIN and best_sc[KP_R_HI] > VIS_MIN
    lean = ((sh_cx - (best_kp[KP_L_HI][0] + best_kp[KP_R_HI][0]) / 2) / sw) if hi_ok else 0.0
    arm_ext = best_d / sw
    el_ang = angle3pt(
        best_kp[sh_i][0], best_kp[sh_i][1],
        best_kp[el_i][0], best_kp[el_i][1],
        best_kp[wr_i][0], best_kp[wr_i][1],
    )

    return PunchEvent(
        frame_number=frame_number,
        timestamp=timestamp,
        side=side,
        punch_type=punch_type,
        arm_extension=round(arm_ext, 4),
        elbow_angle=round(el_ang, 2),
        lean_forward=round(lean, 4),
    )


def feed(
    state: PunchDetectorState,
    kp: np.ndarray,
    sc: np.ndarray,
    frame_number: int,
    timestamp: float,
) -> list[PunchEvent]:
    """한 프레임을 입력하고 발생한 펀치 이벤트 리스트를 반환."""
    state.lm_buf.append((kp.copy(), sc.copy()))

    JAB_WR, JAB_SH, JAB_EL, CROSS_WR, CROSS_SH, CROSS_EL = arm_indices(state.facing_right)
    if sc[JAB_WR] < VIS_MIN or sc[CROSS_WR] < VIS_MIN:
        return []

    sw = shoulder_width_px(kp)
    jx, jy = kp[JAB_WR][0], kp[JAB_WR][1]
    cx_, cy_ = kp[CROSS_WR][0], kp[CROSS_WR][1]

    v_lead = (math.sqrt((jx - state.prev_lead_wr[0]) ** 2 + (jy - state.prev_lead_wr[1]) ** 2) / sw
              if state.prev_lead_wr else 0.0)
    v_rear = (math.sqrt((cx_ - state.prev_rear_wr[0]) ** 2 + (cy_ - state.prev_rear_wr[1]) ** 2) / sw
              if state.prev_rear_wr else 0.0)

    jel = (kp[JAB_EL][1] - kp[JAB_SH][1]) / sw if sc[JAB_EL] > VIS_MIN else 1.0
    rel = (kp[CROSS_EL][1] - kp[CROSS_SH][1]) / sw if sc[CROSS_EL] > VIS_MIN else 1.0
    jea = (angle3pt(kp[JAB_SH][0], kp[JAB_SH][1], kp[JAB_EL][0], kp[JAB_EL][1],
                    kp[JAB_WR][0], kp[JAB_WR][1])
           if sc[JAB_EL] > VIS_MIN else 180.0)
    rea = (angle3pt(kp[CROSS_SH][0], kp[CROSS_SH][1], kp[CROSS_EL][0], kp[CROSS_EL][1],
                    kp[CROSS_WR][0], kp[CROSS_WR][1])
           if sc[CROSS_EL] > VIS_MIN else 180.0)

    state.v_lead.append(v_lead);    state.v_rear.append(v_rear)
    state.el_lead.append(jel);      state.el_rear.append(rel)
    state.ea_lead.append(jea);      state.ea_rear.append(rea)
    state.wy_lead.append(jy);       state.wy_rear.append(cy_)

    peak_lead = max(state.v_lead) if state.v_lead else 0.0
    peak_rear = max(state.v_rear) if state.v_rear else 0.0

    events: list[PunchEvent] = []
    if (state.prev_v_lead > VEL_START and v_lead <= VEL_START
            and peak_lead > peak_rear * DOM_RATIO
            and timestamp - state.last_lead_time > PUNCH_CD):
        pt = _classify_from_buf("lead", sw, state.el_lead, state.ea_lead, state.wy_lead)
        state.last_lead_time = timestamp
        ev = _build_punch_event(state, frame_number, timestamp, "lead", pt)
        if ev:
            state.counts[pt] += 1
            events.append(ev)

    if (state.prev_v_rear > VEL_START and v_rear <= VEL_START
            and peak_rear > peak_lead * DOM_RATIO
            and timestamp - state.last_rear_time > PUNCH_CD):
        pt = _classify_from_buf("rear", sw, state.el_rear, state.ea_rear, state.wy_rear)
        state.last_rear_time = timestamp
        ev = _build_punch_event(state, frame_number, timestamp, "rear", pt)
        if ev:
            state.counts[pt] += 1
            events.append(ev)

    state.prev_v_lead = v_lead
    state.prev_v_rear = v_rear
    state.prev_lead_wr = (jx, jy)
    state.prev_rear_wr = (cx_, cy_)
    return events
