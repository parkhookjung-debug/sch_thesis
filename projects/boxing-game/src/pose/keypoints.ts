// COCO 17 keypoint indices (matches MoveNet output order)
export const KP = {
  NOSE: 0,
  L_EYE: 1, R_EYE: 2,
  L_EAR: 3, R_EAR: 4,
  L_SH: 5, R_SH: 6,
  L_EL: 7, R_EL: 8,
  L_WR: 9, R_WR: 10,
  L_HI: 11, R_HI: 12,
  L_KN: 13, R_KN: 14,
  L_AN: 15, R_AN: 16,
} as const;

export type Keypoint = { x: number; y: number; score: number; name?: string };
export type Pose = { keypoints: Keypoint[]; score?: number };

export const VIS_MIN = 0.3;
export const NEEDED = [KP.L_SH, KP.R_SH, KP.L_WR, KP.R_WR, KP.L_EL, KP.R_EL, KP.NOSE];

// Mirror keypoints horizontally so user sees themself like a mirror.
export function mirrorKeypoints(kps: Keypoint[], w: number): Keypoint[] {
  return kps.map((k) => ({ ...k, x: w - k.x }));
}

// Shoulder width in pixels (used as a body-size scale).
export function shoulderWidth(kps: Keypoint[]): number {
  const dx = kps[KP.R_SH].x - kps[KP.L_SH].x;
  const dy = kps[KP.R_SH].y - kps[KP.L_SH].y;
  return Math.sqrt(dx * dx + dy * dy) + 1e-6;
}

// In a mirrored frame the user's RIGHT shoulder appears on screen-right.
// Returns indices [shoulder, elbow, wrist] for the spatial right & left arm.
export function spatialArms(kps: Keypoint[]) {
  if (kps[KP.L_SH].x > kps[KP.R_SH].x) {
    return {
      r: [KP.L_SH, KP.L_EL, KP.L_WR],
      l: [KP.R_SH, KP.R_EL, KP.R_WR],
    };
  }
  return {
    r: [KP.R_SH, KP.R_EL, KP.R_WR],
    l: [KP.L_SH, KP.L_EL, KP.L_WR],
  };
}
