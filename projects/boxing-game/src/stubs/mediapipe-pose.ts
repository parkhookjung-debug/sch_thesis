// Stub for @mediapipe/pose. The pose-detection package statically imports
// `Pose` from this module to satisfy its BlazePose adapter, but we only use
// MoveNet at runtime — none of these symbols are ever called.
export class Pose {
  constructor(_opts?: unknown) {}
  setOptions(_opts: unknown) {}
  onResults(_cb: unknown) {}
  send(_input: unknown): Promise<void> { return Promise.resolve(); }
  reset() {}
  close() {}
}
export const POSE_LANDMARKS = {};
export const POSE_LANDMARKS_LEFT = {};
export const POSE_LANDMARKS_RIGHT = {};
export const POSE_LANDMARKS_NEUTRAL = {};
export const POSE_CONNECTIONS: unknown[] = [];
export default { Pose };
