import type { Side } from '../pose/detection';
import type { Difficulty } from './config';

export type Screen = 'select' | 'countdown' | 'play' | 'speedAlert' | 'bossIntro' | 'win' | 'lose';
export type Phase = 'warn' | 'defend' | 'counter' | 'result';

export type GameState = {
  screen: Screen;
  diff: Difficulty;

  // HP & score
  aiHp: number;
  aiHpMax: number;
  pHp: number;
  pHpMax: number;
  pDmg: number;

  // Round / combo
  round: number;
  combo: Side[];
  comboIdx: number;

  // Phase timing
  phase: Phase;
  phaseStart: number;
  warnDur: number;
  defendDur: number;
  defended: boolean;
  counterArm: Side | null;
  countered: boolean;
  resultOk: boolean;

  // Speed survival mode
  speedMode: boolean;
  speedMult: number;
  speedRound: number;

  // Boss
  bossActive: boolean;
  bossHp: number;
  bossHpMax: number;

  // Feint (오른쪽 척하고 왼쪽 때리기)
  feintNow: boolean;

  // Pause
  paused: boolean;
  pauseStartedAt: number;

  // Stats
  score: number;
  reactionTimes: number[];
  defendPhaseStart: number;

  // Countdown
  cntdn: number;
};

export function initialState(diff: Difficulty = 'NORMAL'): GameState {
  return {
    screen: 'select',
    diff,
    aiHp: 5, aiHpMax: 5,
    pHp: 100, pHpMax: 100, pDmg: 20,
    round: 0,
    combo: [],
    comboIdx: 0,
    phase: 'warn',
    phaseStart: 0,
    warnDur: 1.8,
    defendDur: 1.4,
    defended: false,
    counterArm: null,
    countered: false,
    resultOk: false,
    speedMode: false,
    speedMult: 1.0,
    speedRound: 0,
    bossActive: false,
    bossHp: 0,
    bossHpMax: 0,
    feintNow: false,
    paused: false,
    pauseStartedAt: 0,
    score: 0,
    reactionTimes: [],
    defendPhaseStart: 0,
    cntdn: 3,
  };
}
