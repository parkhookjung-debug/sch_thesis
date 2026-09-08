import type { Side } from '../pose/detection';

export type Difficulty = 'EASY' | 'NORMAL' | 'HARD' | 'EXTREME';

export const DIFF: Record<Difficulty, {
  aiHp: number;
  pHp: number;
  pDmg: number;
  color: string;
  label: string;
  desc: string;
}> = {
  EASY:    { aiHp: 3,  pHp: 100, pDmg: 0,   color: '#3aff7a', label: 'EASY',    desc: 'AI 체력 3  ·  HP 무한' },
  NORMAL:  { aiHp: 5,  pHp: 100, pDmg: 20,  color: '#3ad5ff', label: 'NORMAL',  desc: 'AI 체력 5  ·  HP 100 (5회)' },
  HARD:    { aiHp: 7,  pHp: 100, pDmg: 34,  color: '#ff8c3a', label: 'HARD',    desc: 'AI 체력 7  ·  HP 100 (3회)' },
  EXTREME: { aiHp: 10, pHp: 100, pDmg: 100, color: '#ff3a55', label: 'EXTREME', desc: 'AI 체력 10 ·  HP 100 (1회)' },
};

export const AI_PATTERNS: Record<Difficulty, Side[][] | null> = {
  EASY: null,
  NORMAL: [
    ['LEFT', 'RIGHT'], ['RIGHT', 'LEFT'],
    ['LEFT'], ['RIGHT'],
    ['LEFT', 'RIGHT', 'LEFT'],
  ],
  HARD: [
    ['LEFT', 'LEFT'], ['RIGHT', 'RIGHT'],
    ['LEFT', 'RIGHT', 'LEFT'], ['RIGHT', 'LEFT', 'RIGHT'],
    ['LEFT', 'RIGHT', 'RIGHT'], ['RIGHT', 'LEFT', 'LEFT'],
  ],
  EXTREME: [
    ['LEFT', 'LEFT', 'LEFT'], ['RIGHT', 'RIGHT', 'RIGHT'],
    ['LEFT', 'RIGHT', 'LEFT'], ['RIGHT', 'LEFT', 'RIGHT'],
    ['LEFT', 'LEFT', 'RIGHT'], ['RIGHT', 'RIGHT', 'LEFT'],
    ['RIGHT', 'LEFT', 'LEFT'], ['LEFT', 'RIGHT', 'RIGHT'],
  ],
};

export const TOTAL_ROUNDS = 10;
export const WARN_SINGLE: [number, number] = [1.4, 2.0];
export const DEF_SINGLE: [number, number] = [1.1, 1.5];
export const WARN_COMBO: [number, number] = [0.6, 1.0];
export const DEF_COMBO: [number, number] = [0.7, 1.0];
export const COUNTER_DUR = 1.5;
export const RESULT_DUR = 0.8;
export const SPEED_ALERT_DUR = 2.5;
export const COUNTER_DELAY = 0.45;

// Boss
export const SPEED_BOSS_TRIGGER = 5; // # speed-mode rounds before boss appears
export const BOSS_INTRO_DUR = 3.2;
export const BOSS_HP: Record<Difficulty, number> = {
  EASY: 0, NORMAL: 0, HARD: 5, EXTREME: 7,
};
export const BOSS_NAME: Record<Difficulty, string> = {
  EASY: '', NORMAL: '', HARD: 'IRON FIST', EXTREME: 'EL DIABLO',
};

// Feint (페이크 공격: warn에는 반대 방향, defend 진입 후 짧게 페이크 유지하다 진짜 방향 노출)
export const FEINT_REVEAL_AT = 0.2;        // defend 시작 후 진짜 방향 노출까지 시간
export const FEINT_REACT_WINDOW = 0.7;     // 노출 후 반응 시간 (보장)
export const FEINT_TOTAL_DEFEND = FEINT_REVEAL_AT + FEINT_REACT_WINDOW;

// 페인트 등장 확률 — 라운드 종류별
export function feintChance(diff: Difficulty, ctx: 'normal' | 'speed' | 'boss'): number {
  if (ctx === 'boss') return diff === 'EXTREME' ? 0.85 : 0.7;
  if (ctx === 'speed') {
    if (diff === 'EXTREME') return 0.5;
    if (diff === 'HARD') return 0.35;
    return 0;
  }
  // normal rounds
  return diff === 'EXTREME' ? 0.25 : 0;
}

export function randRange(lo: number, hi: number) {
  return lo + Math.random() * (hi - lo);
}

export function genCombo(diff: Difficulty): Side[] {
  const patterns = AI_PATTERNS[diff];
  if (!patterns || Math.random() < 0.3) {
    const len = 1 + Math.floor(Math.random() * 3);
    return Array.from({ length: len }, () =>
      Math.random() < 0.5 ? 'LEFT' : 'RIGHT'
    );
  }
  return [...patterns[Math.floor(Math.random() * patterns.length)]];
}
