"""실시간 프레임에서 view-mode 판정을 위한 슬라이딩 윈도우."""
from __future__ import annotations

from collections import deque

import numpy as np

from .keypoints import KP_L_HI, KP_L_SH, KP_R_HI, KP_R_SH
from ..config import VIS_MIN
from ..pose.view_classifier import classify_ratio


class ViewDetector:
    def __init__(self, window: int = 30):
        self._ratios: deque = deque(maxlen=window)
        self._locked: bool = False
        self._mode: str = "ambiguous"

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def locked(self) -> bool:
        return self._locked

    def force(self, mode: str) -> None:
        if mode in ("front", "side"):
            self._mode = mode
            self._locked = True

    def update(self, kp: np.ndarray, sc: np.ndarray) -> str:
        """프레임 한 장으로 ratio를 누적하고 (윈도우 채워지면) mode 갱신."""
        if self._locked:
            return self._mode
        if min(sc[KP_L_SH], sc[KP_R_SH], sc[KP_L_HI], sc[KP_R_HI]) < VIS_MIN:
            return self._mode
        sw = abs(kp[KP_L_SH][0] - kp[KP_R_SH][0])
        torso = abs((kp[KP_L_SH][1] + kp[KP_R_SH][1]) / 2 - (kp[KP_L_HI][1] + kp[KP_R_HI][1]) / 2)
        if torso < 1.0:  # px 단위
            return self._mode
        self._ratios.append(float(sw / torso))
        if len(self._ratios) >= 10:
            sorted_r = sorted(self._ratios)
            med = sorted_r[len(sorted_r) // 2]
            self._mode = classify_ratio(med)
        return self._mode
