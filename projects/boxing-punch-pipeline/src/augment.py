"""Pose-window augmentations for skeleton action recognition.

Operates on tensors of shape (C, T, V) where C=[x,y,score].

Available transforms (applied in this order if enabled):
  - random mirror (left/right joint swap)
  - random temporal time-warp (resample with rate in [0.8, 1.25])
  - random temporal crop+pad (small start offset)
  - random joint dropout (zero confidence of K random joints)
  - Gaussian noise on (x, y)
  - small global scale / rotation around hip center
"""
from __future__ import annotations

import numpy as np
import torch

from pose_schema import NUM_JOINTS

# COCO-17 left/right pairs (used by RTMPose default)
COCO_MIRROR_PAIRS = [
    (1, 2),   # eyes
    (3, 4),   # ears
    (5, 6),   # shoulders
    (7, 8),   # elbows
    (9, 10),  # wrists
    (11, 12), # hips
    (13, 14), # knees
    (15, 16), # ankles
]


def _mirror_pose(x: torch.Tensor) -> torch.Tensor:
    """Flip horizontally and swap left/right joints. Expects (C, T, V) with C>=2."""
    out = x.clone()
    # x-coord flip around origin (poses are already hip-centered + scaled)
    out[0] = -out[0]
    # swap joints
    for a, b in COCO_MIRROR_PAIRS:
        tmp = out[:, :, a].clone()
        out[:, :, a] = out[:, :, b]
        out[:, :, b] = tmp
    return out


def _time_warp(x: torch.Tensor, factor: float) -> torch.Tensor:
    """Resample along T using linear interp, then crop/pad back to original T."""
    c, t, v = x.shape
    new_t = max(2, int(round(t * factor)))
    # interpolate using 1D linear in time
    src_idx = torch.linspace(0, t - 1, new_t, device=x.device)
    lo = src_idx.floor().long().clamp(0, t - 1)
    hi = (lo + 1).clamp(0, t - 1)
    w = (src_idx - lo.float()).view(1, new_t, 1)
    warped = (1 - w) * x[:, lo, :] + w * x[:, hi, :]
    # back to T frames: crop from random start if longer, pad with edge if shorter
    if new_t == t:
        return warped
    if new_t > t:
        start = int(torch.randint(0, new_t - t + 1, (1,)).item())
        return warped[:, start : start + t, :]
    # new_t < t -> pad by repeating last frame at the end
    pad = t - new_t
    pad_block = warped[:, -1:, :].expand(c, pad, v)
    return torch.cat([warped, pad_block], dim=1)


def _joint_dropout(x: torch.Tensor, p: float, max_drop: int = 4) -> torch.Tensor:
    """Zero out the score channel (and xy if no score channel) for a few random joints."""
    if torch.rand(1).item() >= p:
        return x
    c, t, v = x.shape
    k = int(torch.randint(1, max_drop + 1, (1,)).item())
    idx = torch.randperm(v)[:k]
    out = x.clone()
    if c >= 3:
        out[2, :, idx] = 0.0  # zero confidence
    out[:2, :, idx] = 0.0  # zero coords too
    return out


def _gauss_noise(x: torch.Tensor, sigma: float) -> torch.Tensor:
    out = x.clone()
    out[:2] = out[:2] + torch.randn_like(out[:2]) * sigma
    return out


def _scale(x: torch.Tensor, low: float, high: float) -> torch.Tensor:
    s = torch.empty(1).uniform_(low, high).item()
    out = x.clone()
    out[:2] = out[:2] * s
    return out


def _rotate(x: torch.Tensor, max_deg: float) -> torch.Tensor:
    theta = (torch.rand(1).item() * 2 - 1) * np.deg2rad(max_deg)
    cos_t, sin_t = float(np.cos(theta)), float(np.sin(theta))
    out = x.clone()
    x0 = out[0].clone()
    y0 = out[1].clone()
    out[0] = cos_t * x0 - sin_t * y0
    out[1] = sin_t * x0 + cos_t * y0
    return out


class PoseAugment:
    """Compose-able augmentation pipeline for (C, T, V) pose tensors."""

    def __init__(
        self,
        mirror_p: float = 0.5,
        time_warp_p: float = 0.5,
        warp_range: tuple[float, float] = (0.8, 1.25),
        joint_dropout_p: float = 0.4,
        joint_dropout_max: int = 4,
        noise_sigma: float = 0.02,
        scale_range: tuple[float, float] = (0.9, 1.1),
        rotate_max_deg: float = 8.0,
    ) -> None:
        self.mirror_p = mirror_p
        self.time_warp_p = time_warp_p
        self.warp_range = warp_range
        self.joint_dropout_p = joint_dropout_p
        self.joint_dropout_max = joint_dropout_max
        self.noise_sigma = noise_sigma
        self.scale_range = scale_range
        self.rotate_max_deg = rotate_max_deg

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        # x: (C, T, V), already normalized (hip-centered, scaled)
        if torch.rand(1).item() < self.mirror_p:
            x = _mirror_pose(x)
        if torch.rand(1).item() < self.time_warp_p:
            f = float(torch.empty(1).uniform_(*self.warp_range).item())
            x = _time_warp(x, f)
        x = _joint_dropout(x, self.joint_dropout_p, self.joint_dropout_max)
        if self.noise_sigma > 0:
            x = _gauss_noise(x, self.noise_sigma)
        x = _scale(x, *self.scale_range)
        if self.rotate_max_deg > 0:
            x = _rotate(x, self.rotate_max_deg)
        return x
