"""COCO 17 keypoint 인덱스 + 간단한 기하 헬퍼."""
import math
import numpy as np

KP_NOSE = 0
KP_L_EYE = 1
KP_R_EYE = 2
KP_L_EAR = 3
KP_R_EAR = 4
KP_L_SH = 5
KP_R_SH = 6
KP_L_EL = 7
KP_R_EL = 8
KP_L_WR = 9
KP_R_WR = 10
KP_L_HI = 11
KP_R_HI = 12
KP_L_KN = 13
KP_R_KN = 14
KP_L_AN = 15
KP_R_AN = 16

COCO_CONN = [
    (KP_L_SH, KP_R_SH), (KP_L_SH, KP_L_EL), (KP_L_EL, KP_L_WR),
    (KP_R_SH, KP_R_EL), (KP_R_EL, KP_R_WR),
    (KP_L_SH, KP_L_HI), (KP_R_SH, KP_R_HI), (KP_L_HI, KP_R_HI),
    (KP_L_HI, KP_L_KN), (KP_L_KN, KP_L_AN),
    (KP_R_HI, KP_R_KN), (KP_R_KN, KP_R_AN),
    (KP_NOSE, KP_L_SH), (KP_NOSE, KP_R_SH),
]


def shoulder_width_px(kp: np.ndarray) -> float:
    dx = kp[KP_R_SH][0] - kp[KP_L_SH][0]
    dy = kp[KP_R_SH][1] - kp[KP_L_SH][1]
    return math.sqrt(dx * dx + dy * dy) + 1e-6


def angle3pt(ax, ay, bx, by, cx, cy) -> float:
    bax, bay = ax - bx, ay - by
    bcx, bcy = cx - bx, cy - by
    dot = bax * bcx + bay * bcy
    mag = math.sqrt(bax**2 + bay**2) * math.sqrt(bcx**2 + bcy**2) + 1e-9
    return math.degrees(math.acos(max(-1, min(1, dot / mag))))


def arm_indices(facing_right: bool):
    """현재 향한 방향에 따라 (JAB_WR, JAB_SH, JAB_EL, CROSS_WR, CROSS_SH, CROSS_EL) 반환."""
    if facing_right:
        return KP_R_WR, KP_R_SH, KP_R_EL, KP_L_WR, KP_L_SH, KP_L_EL
    return KP_L_WR, KP_L_SH, KP_L_EL, KP_R_WR, KP_R_SH, KP_R_EL


def detect_facing(kp: np.ndarray, sc: np.ndarray, vis_min: float = 0.30) -> bool:
    """앞손(lead) 판별 — 측면 뷰에서는 x 가 더 작은 쪽이 앞손."""
    if sc[KP_L_WR] < vis_min and sc[KP_R_WR] < vis_min:
        return True
    if sc[KP_L_WR] < vis_min:
        return False  # 오른쪽 손목이 보이는데 왼쪽은 안 보임 → 좌향일 가능성↑
    if sc[KP_R_WR] < vis_min:
        return True
    return bool(kp[KP_R_WR][0] < kp[KP_L_WR][0])
