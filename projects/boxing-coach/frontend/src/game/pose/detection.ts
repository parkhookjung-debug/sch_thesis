import { KP, VIS_MIN, type Keypoint, shoulderWidth, spatialArms } from './keypoints';

const BLOCK_NOSE_THRESH = 0.10;
const SLIP_THRESH = 0.20;
const GUARD_DROP_THRESH = 0.55;

// Punch tuning — picks up either a horizontal jab (sideways stance) or a
// straight punch facing the camera (arm extension increases).
const PUNCH_VEL = 0.10;          // horizontal wrist speed / sw per frame
const PUNCH_EXTEND = 0.20;       // wrist travel from baseline / sw
const PUNCH_DOM = 1.10;          // dominant arm must be this much faster
const ARM_EXT_FULL = 1.00;       // wrist-shoulder distance / sw considered "extended"
const ARM_EXT_DELTA = 0.30;      // sudden growth in arm extension that signals a punch
const VEL_BUF_LEN = 8;           // extension/velocity tracking window

export type Side = 'LEFT' | 'RIGHT';
export type Defense = 'BLOCK_L' | 'BLOCK_R' | 'SLIP_L' | 'SLIP_R';

// Map an incoming attack to the defenses that successfully neutralize it,
// and the arm that should counter-punch.
export const VALID_DEF: Record<Side, Partial<Record<Defense, Side>>> = {
  LEFT:  { BLOCK_L: 'LEFT',  SLIP_R: 'RIGHT' },
  RIGHT: { BLOCK_R: 'RIGHT', SLIP_L: 'LEFT' },
};

export function checkGuard(kps: Keypoint[]): boolean {
  const sw = shoulderWidth(kps);
  const shY = (kps[KP.L_SH].y + kps[KP.R_SH].y) / 2;
  const thr = shY + GUARD_DROP_THRESH * sw;
  const arms = spatialArms(kps);
  return kps[arms.r[2]].y < thr && kps[arms.l[2]].y < thr;
}

function detectBlock(kps: Keypoint[]): Side | null {
  const sw = shoulderWidth(kps);
  const noseY = kps[KP.NOSE].y;
  const thr = noseY - BLOCK_NOSE_THRESH * sw;
  const arms = spatialArms(kps);
  const rUp = kps[arms.r[2]].y < thr;
  const lUp = kps[arms.l[2]].y < thr;
  if (rUp && !lUp) return 'RIGHT';
  if (lUp && !rUp) return 'LEFT';
  return null;
}

function detectSlip(kps: Keypoint[]): Side | null {
  const sw = shoulderWidth(kps);
  const shCx = (kps[KP.L_SH].x + kps[KP.R_SH].x) / 2;
  const dev = (kps[KP.NOSE].x - shCx) / sw;
  if (dev > SLIP_THRESH) return 'RIGHT';
  if (dev < -SLIP_THRESH) return 'LEFT';
  return null;
}

export function getDefense(kps: Keypoint[]): Defense | null {
  const b = detectBlock(kps);
  if (b === 'RIGHT') return 'BLOCK_R';
  if (b === 'LEFT') return 'BLOCK_L';
  const s = detectSlip(kps);
  if (s === 'RIGHT') return 'SLIP_R';
  if (s === 'LEFT') return 'SLIP_L';
  return null;
}

// Punch detector — combines the original horizontal-velocity test with an
// arm-extension test so a straight punch facing the camera (where x barely
// changes) is still picked up.
export type PunchTracker = {
  prev: Keypoint[] | null;
  velR: number[];
  velL: number[];
  extR: number[];     // recent wrist↔shoulder distances, normalized by sw
  extL: number[];
  baseR: { x: number; y: number } | null;
  baseL: { x: number; y: number } | null;
  baseExtR: number | null;
  baseExtL: number | null;
};

// Latest measurement snapshot (for on-screen debug display).
export type PunchDebug = {
  vr: number; vl: number;
  er: number; el: number;
  extR: number; extL: number;
  dExtR: number; dExtL: number;
};

export function newPunchTracker(): PunchTracker {
  return {
    prev: null,
    velR: [], velL: [],
    extR: [], extL: [],
    baseR: null, baseL: null,
    baseExtR: null, baseExtL: null,
  };
}

function armExtension(kps: Keypoint[], shIdx: number, wrIdx: number, sw: number): number {
  return Math.hypot(kps[wrIdx].x - kps[shIdx].x, kps[wrIdx].y - kps[shIdx].y) / sw;
}

export function setPunchBaseline(t: PunchTracker, kps: Keypoint[]) {
  const arms = spatialArms(kps);
  const sw = shoulderWidth(kps);
  t.baseR = { x: kps[arms.r[2]].x, y: kps[arms.r[2]].y };
  t.baseL = { x: kps[arms.l[2]].x, y: kps[arms.l[2]].y };
  t.baseExtR = armExtension(kps, arms.r[0], arms.r[2], sw);
  t.baseExtL = armExtension(kps, arms.l[0], arms.l[2], sw);
}

export function detectPunch(
  t: PunchTracker,
  kps: Keypoint[],
): { side: Side | null; debug: PunchDebug } {
  const empty: PunchDebug = { vr: 0, vl: 0, er: 0, el: 0, extR: 0, extL: 0, dExtR: 0, dExtL: 0 };
  if (!t.prev || !t.baseR || !t.baseL || t.baseExtR === null || t.baseExtL === null) {
    t.prev = kps.map((k) => ({ ...k }));
    return { side: null, debug: empty };
  }

  const sw = shoulderWidth(kps);
  const arms = spatialArms(kps);
  const rShIdx = arms.r[0], lShIdx = arms.l[0];
  const rIdx = arms.r[2],   lIdx = arms.l[2];

  // Horizontal wrist velocity (helps with sideways stance).
  const drx = kps[rIdx].x - t.prev[rIdx].x;
  const dlx = kps[lIdx].x - t.prev[lIdx].x;
  // In a mirrored frame, RIGHT arm punching forward moves screen-left (-dx),
  // LEFT arm punching forward moves screen-right (+dx).
  const vr = Math.max(0, -drx) / sw;
  const vl = Math.max(0,  dlx) / sw;

  // Wrist↔baseline travel and current arm extension.
  const er  = Math.hypot(kps[rIdx].x - t.baseR.x, kps[rIdx].y - t.baseR.y) / sw;
  const el  = Math.hypot(kps[lIdx].x - t.baseL.x, kps[lIdx].y - t.baseL.y) / sw;
  const extR = armExtension(kps, rShIdx, rIdx, sw);
  const extL = armExtension(kps, lShIdx, lIdx, sw);
  const dExtR = extR - t.baseExtR;
  const dExtL = extL - t.baseExtL;

  t.prev = kps.map((k) => ({ ...k }));
  pushBuf(t.velR, vr); pushBuf(t.velL, vl);
  pushBuf(t.extR, extR); pushBuf(t.extL, extL);

  const pr = Math.max(...t.velR);
  const pl = Math.max(...t.velL);
  const peakExtR = Math.max(...t.extR);
  const peakExtL = Math.max(...t.extL);
  const peakDExtR = peakExtR - t.baseExtR;
  const peakDExtL = peakExtL - t.baseExtL;

  // A punch fires if EITHER signal is dominant on one side:
  //   (a) horizontal sweep — fast wrist motion + travel from baseline
  //   (b) straight extension — arm became noticeably more extended than baseline
  const horizR = pr > PUNCH_VEL && er > PUNCH_EXTEND && pr > pl * PUNCH_DOM;
  const horizL = pl > PUNCH_VEL && el > PUNCH_EXTEND && pl > pr * PUNCH_DOM;
  const extPunchR = peakExtR > ARM_EXT_FULL && peakDExtR > ARM_EXT_DELTA && peakDExtR > peakDExtL * PUNCH_DOM;
  const extPunchL = peakExtL > ARM_EXT_FULL && peakDExtL > ARM_EXT_DELTA && peakDExtL > peakDExtR * PUNCH_DOM;

  const debug: PunchDebug = { vr, vl, er, el, extR, extL, dExtR, dExtL };
  if (horizR || extPunchR) return { side: 'RIGHT', debug };
  if (horizL || extPunchL) return { side: 'LEFT',  debug };
  return { side: null, debug };
}

function pushBuf(buf: number[], v: number, max = VEL_BUF_LEN) {
  buf.push(v);
  if (buf.length > max) buf.shift();
}

// Used by the renderer to know whether a keypoint can be drawn.
export function visible(k: Keypoint | undefined): boolean {
  return !!k && k.score >= VIS_MIN;
}

export function poseUsable(kps: Keypoint[]): boolean {
  const need = [KP.L_SH, KP.R_SH, KP.L_WR, KP.R_WR, KP.L_EL, KP.R_EL, KP.NOSE];
  return need.every((i) => visible(kps[i]));
}
