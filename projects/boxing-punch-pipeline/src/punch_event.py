from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from pose_schema import (
    LEFT_SHOULDER,
    NUM_JOINTS,
    RIGHT_SHOULDER,
)

LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10


@dataclass
class EventFeatures:
    frame_index: int
    energy: float
    left_speed: float
    right_speed: float
    left_elbow_angle: float
    right_elbow_angle: float
    left_extension: float
    right_extension: float
    active_side: str


@dataclass
class PunchEvent:
    poses: np.ndarray
    start_frame: int
    apex_frame: int
    end_frame: int
    apex_index: int
    peak_energy: float
    active_side: str
    features: list[EventFeatures]


def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom < 1e-6:
        return 0.0
    cos_value = float(np.dot(ba, bc) / denom)
    return float(np.degrees(np.arccos(np.clip(cos_value, -1.0, 1.0))))


def pose_scale(pose: np.ndarray) -> float:
    shoulders = np.linalg.norm(pose[LEFT_SHOULDER, :2] - pose[RIGHT_SHOULDER, :2])
    return float(max(shoulders, 1.0))


def frame_features(prev_pose: np.ndarray | None, pose: np.ndarray, frame_index: int) -> EventFeatures:
    scale = pose_scale(pose)
    if prev_pose is None:
        left_speed = 0.0
        right_speed = 0.0
    else:
        left_speed = float(np.linalg.norm(pose[LEFT_WRIST, :2] - prev_pose[LEFT_WRIST, :2]) / scale)
        right_speed = float(np.linalg.norm(pose[RIGHT_WRIST, :2] - prev_pose[RIGHT_WRIST, :2]) / scale)

    left_extension = float(np.linalg.norm(pose[LEFT_WRIST, :2] - pose[LEFT_SHOULDER, :2]) / scale)
    right_extension = float(np.linalg.norm(pose[RIGHT_WRIST, :2] - pose[RIGHT_SHOULDER, :2]) / scale)
    left_angle = joint_angle(pose[LEFT_SHOULDER, :2], pose[LEFT_ELBOW, :2], pose[LEFT_WRIST, :2])
    right_angle = joint_angle(pose[RIGHT_SHOULDER, :2], pose[RIGHT_ELBOW, :2], pose[RIGHT_WRIST, :2])

    left_score = left_speed + 0.08 * left_extension + 0.0015 * left_angle
    right_score = right_speed + 0.08 * right_extension + 0.0015 * right_angle
    active_side = "left" if left_score >= right_score else "right"
    energy = max(left_score, right_score)

    return EventFeatures(
        frame_index=frame_index,
        energy=float(energy),
        left_speed=left_speed,
        right_speed=right_speed,
        left_elbow_angle=left_angle,
        right_elbow_angle=right_angle,
        left_extension=left_extension,
        right_extension=right_extension,
        active_side=active_side,
    )


def resample_pose_sequence(poses: np.ndarray, target_size: int) -> np.ndarray:
    poses = np.asarray(poses, dtype=np.float32)
    if len(poses) == target_size:
        return poses.copy()
    if len(poses) == 0:
        return np.zeros((target_size, NUM_JOINTS, 3), dtype=np.float32)
    if len(poses) == 1:
        return np.repeat(poses, target_size, axis=0)

    source_x = np.linspace(0.0, 1.0, len(poses), dtype=np.float32)
    target_x = np.linspace(0.0, 1.0, target_size, dtype=np.float32)
    flat = poses.reshape(len(poses), -1)
    out = np.empty((target_size, flat.shape[1]), dtype=np.float32)
    for col in range(flat.shape[1]):
        out[:, col] = np.interp(target_x, source_x, flat[:, col])
    return out.reshape(target_size, NUM_JOINTS, poses.shape[-1])


def extract_event_window(event: PunchEvent, window_size: int) -> np.ndarray:
    return resample_pose_sequence(event.poses, window_size)


class PunchEventDetector:
    def __init__(
        self,
        start_threshold: float = 0.17,
        end_threshold: float = 0.09,
        min_event_frames: int = 5,
        max_event_frames: int = 28,
        pre_roll: int = 5,
        post_roll: int = 8,
        cooldown_frames: int = 7,
        smooth: float = 0.35,
        fall_ratio: float = 0.45,
    ) -> None:
        self.start_threshold = start_threshold
        self.end_threshold = end_threshold
        self.min_event_frames = min_event_frames
        self.max_event_frames = max_event_frames
        self.pre_roll = pre_roll
        # post_roll keeps collecting frames after the natural energy-fall end of
        # the punch, so the window we emit includes the hand returning to guard.
        # Training windows include ~4 frames of context after the labeled end,
        # so a similar tail at inference time keeps the distributions matched.
        self.post_roll = post_roll
        self.cooldown_frames = cooldown_frames
        self.smooth = smooth
        self.fall_ratio = fall_ratio
        self.reset()

    def reset(self) -> None:
        self.state = "idle"
        self.frame_index = -1
        self.prev_pose = None
        self.energy_ema = 0.0
        self.cooldown_left = 0
        self.pre_buffer: deque[tuple[int, np.ndarray, EventFeatures]] = deque(maxlen=self.pre_roll)
        self.event_buffer: list[tuple[int, np.ndarray, EventFeatures]] = []
        self.peak_pos = 0
        self.peak_energy = 0.0
        self.post_roll_left = 0

    def update(self, pose: np.ndarray) -> tuple[PunchEvent | None, EventFeatures]:
        self.frame_index += 1
        feat = frame_features(self.prev_pose, pose, self.frame_index)
        self.prev_pose = pose.copy()
        self.energy_ema = self.smooth * feat.energy + (1.0 - self.smooth) * self.energy_ema
        feat.energy = float(self.energy_ema)

        emitted = None
        if self.cooldown_left > 0:
            self.cooldown_left -= 1
            self.pre_buffer.append((self.frame_index, pose.copy(), feat))
            return emitted, feat

        if self.state == "idle":
            self.pre_buffer.append((self.frame_index, pose.copy(), feat))
            if feat.energy >= self.start_threshold:
                self.state = "active"
                self.event_buffer = list(self.pre_buffer)
                self.peak_pos = len(self.event_buffer) - 1
                self.peak_energy = feat.energy
            return emitted, feat

        self.event_buffer.append((self.frame_index, pose.copy(), feat))

        if self.state == "post_roll":
            self.post_roll_left -= 1
            if self.post_roll_left <= 0:
                emitted = self._finish_event()
                self.state = "idle"
                self.cooldown_left = self.cooldown_frames
                self.pre_buffer.clear()
                self.event_buffer = []
                self.peak_pos = 0
                self.peak_energy = 0.0
                self.post_roll_left = 0
            return emitted, feat

        if feat.energy >= self.peak_energy:
            self.peak_energy = feat.energy
            self.peak_pos = len(self.event_buffer) - 1

        long_enough = len(self.event_buffer) >= self.min_event_frames
        dynamic_end_threshold = max(self.end_threshold, self.peak_energy * self.fall_ratio)
        should_end = (long_enough and feat.energy <= dynamic_end_threshold) or len(self.event_buffer) >= self.max_event_frames
        if should_end:
            # Don't emit yet -- collect post_roll frames first so the window
            # includes the hand returning to guard. This matches the trailing
            # context the training windows have.
            if self.post_roll > 0:
                self.state = "post_roll"
                self.post_roll_left = self.post_roll
                return emitted, feat
            emitted = self._finish_event()
            self.state = "idle"
            self.cooldown_left = self.cooldown_frames
            self.pre_buffer.clear()
            self.event_buffer = []
            self.peak_pos = 0
            self.peak_energy = 0.0

        return emitted, feat

    def _finish_event(self) -> PunchEvent:
        frames = [item[0] for item in self.event_buffer]
        poses = np.asarray([item[1] for item in self.event_buffer], dtype=np.float32)
        features = [item[2] for item in self.event_buffer]
        apex_index = int(np.clip(self.peak_pos, 0, len(frames) - 1))
        active_side = features[apex_index].active_side if features else "unknown"
        return PunchEvent(
            poses=poses,
            start_frame=int(frames[0]),
            apex_frame=int(frames[apex_index]),
            end_frame=int(frames[-1]),
            apex_index=apex_index,
            peak_energy=float(self.peak_energy),
            active_side=active_side,
            features=features,
        )
