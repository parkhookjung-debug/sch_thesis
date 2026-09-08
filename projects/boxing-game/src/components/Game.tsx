import { useCallback, useEffect, useRef, useState } from 'react';
import { usePoseDetector, type PoseFrame } from '../hooks/usePoseDetector';
import { KP, type Keypoint } from '../pose/keypoints';
import {
  checkGuard, detectPunch, getDefense, newPunchTracker, poseUsable,
  setPunchBaseline, VALID_DEF, visible,
  type Side, type Defense, type PunchTracker,
} from '../pose/detection';
import {
  BOSS_HP, BOSS_INTRO_DUR, BOSS_NAME, COUNTER_DELAY, COUNTER_DUR,
  DEF_COMBO, DEF_SINGLE, DIFF, FEINT_REVEAL_AT, FEINT_TOTAL_DEFEND,
  RESULT_DUR, SPEED_ALERT_DUR, SPEED_BOSS_TRIGGER, TOTAL_ROUNDS,
  WARN_COMBO, WARN_SINGLE, feintChance, genCombo, randRange,
  type Difficulty,
} from '../game/config';
import { initialState, type GameState } from '../game/types';
import { DifficultySelect } from './DifficultySelect';
import { HUD } from './HUD';
import { AttackArrow } from './AttackArrow';

type Particle = { x: number; y: number; vx: number; vy: number; life: number; maxLife: number };
type DamagePopup = { id: number; value: number; x: number; y: number; born: number };

const COCO_CONN: [number, number][] = [
  [KP.L_SH, KP.R_SH], [KP.L_SH, KP.L_EL], [KP.L_EL, KP.L_WR],
  [KP.R_SH, KP.R_EL], [KP.R_EL, KP.R_WR],
  [KP.L_SH, KP.L_HI], [KP.R_SH, KP.R_HI], [KP.L_HI, KP.R_HI],
  [KP.L_HI, KP.L_KN], [KP.L_KN, KP.L_AN], [KP.R_HI, KP.R_KN], [KP.R_KN, KP.R_AN],
  [KP.NOSE, KP.L_SH], [KP.NOSE, KP.R_SH],
];

export function Game() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // The mutable game state lives in a ref so the per-frame loop never
  // triggers React renders. We mirror display-relevant slices into the
  // `view` state below at ~30hz for the UI.
  const stateRef = useRef<GameState>(initialState());
  const punchRef = useRef<PunchTracker>(newPunchTracker());
  const slipBufRef = useRef<(Defense | null)[]>([]);
  const lastFrameRef = useRef<PoseFrame | null>(null);
  const [view, setView] = useState<GameState>(stateRef.current);

  // ── Effects (visceral hit feedback) ────────────────────────────
  const effectsRef = useRef<{
    shakeUntil: number;
    flashUntil: number;
    particles: Particle[];
    popups: DamagePopup[];
  }>({ shakeUntil: 0, flashUntil: 0, particles: [], popups: [] });
  const [popupTick, setPopupTick] = useState(0); // re-render trigger for popups

  const { status, error } = usePoseDetector(videoRef, {
    onFrame: (f) => { lastFrameRef.current = f; },
  });

  // Push the current state to `view` (throttled in the loop).
  const flushView = useCallback(() => {
    setView({ ...stateRef.current });
  }, []);

  // ── Game lifecycle ────────────────────────────────────────────────
  const startGame = useCallback((diff: Difficulty) => {
    const cfg = DIFF[diff];
    stateRef.current = {
      ...initialState(diff),
      diff,
      aiHp: cfg.aiHp, aiHpMax: cfg.aiHp,
      pHp: cfg.pHp, pHpMax: cfg.pHp, pDmg: cfg.pDmg,
      screen: 'countdown',
      cntdn: 3,
      phaseStart: nowSec(),
    };
    flushView();
  }, [flushView]);

  const restart = useCallback(() => {
    stateRef.current = initialState();
    flushView();
  }, [flushView]);

  const togglePause = useCallback(() => {
    const s = stateRef.current;
    if (s.screen !== 'play') return;
    if (s.paused) {
      // Resume: shift timestamps forward by the pause duration so phases
      // continue from where they left off.
      const dur = nowSec() - s.pauseStartedAt;
      s.phaseStart += dur;
      s.defendPhaseStart += dur;
      s.paused = false;
    } else {
      s.paused = true;
      s.pauseStartedAt = nowSec();
    }
    flushView();
  }, [flushView]);

  const quitToMenu = useCallback(() => {
    stateRef.current = initialState();
    flushView();
  }, [flushView]);

  // ── Phase helpers (mutate stateRef) ──────────────────────────────
  function startAttack(s: GameState) {
    s.phase = 'warn';
    s.phaseStart = nowSec();
    s.defended = false;
    s.counterArm = null;
    s.countered = false;
    s.resultOk = false;
    punchRef.current = newPunchTracker();
    slipBufRef.current = [];
  }

  function startRoundCombo(s: GameState) {
    s.combo = genCombo(s.diff);
    s.comboIdx = 0;
    rollAttackTiming(s);
    startAttack(s);
  }

  // ── Effect helpers ───────────────────────────────────────────────
  let popupId = 0;
  function triggerCounterHit(kps: Keypoint[] | null, side: Side | null, dmg: number) {
    const fx = effectsRef.current;
    const now = nowSec();
    fx.shakeUntil = now + 0.4;
    fx.flashUntil = now + 0.18;
    // Particle burst from wrist position (canvas coords).
    let px = 0.5, py = 0.45; // fallback (normalized)
    const c = canvasRef.current;
    if (kps && c && side) {
      const arms = sideArmIdx(kps, side);
      const wrist = kps[arms[2]];
      if (visible(wrist)) {
        px = wrist.x / c.width;
        py = wrist.y / c.height;
        for (let i = 0; i < 14; i++) {
          const a = Math.random() * Math.PI * 2;
          const sp = 220 + Math.random() * 320;
          fx.particles.push({
            x: wrist.x, y: wrist.y,
            vx: Math.cos(a) * sp, vy: Math.sin(a) * sp,
            life: 0.55, maxLife: 0.55,
          });
        }
      }
    }
    // Damage popup at impact location.
    fx.popups.push({
      id: ++popupId,
      value: dmg,
      x: px * 100,
      y: py * 100,
      born: now,
    });
    setPopupTick((t) => t + 1);
    if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
      try { navigator.vibrate?.(70); } catch { /* iOS Safari throws */ }
    }
  }

  function triggerFailHit() {
    const fx = effectsRef.current;
    const now = nowSec();
    fx.shakeUntil = now + 0.35;
    fx.flashUntil = now + 0.22;
    if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
      try { navigator.vibrate?.([40, 30, 50]); } catch { /* */ }
    }
  }

  // Per-attack timing (so feint chance is rolled each attack within a combo).
  function rollAttackTiming(s: GameState) {
    const mult = s.speedMult;
    const ctx: 'normal' | 'speed' | 'boss' =
      s.bossActive ? 'boss' : s.speedMode ? 'speed' : 'normal';
    s.feintNow = Math.random() < feintChance(s.diff, ctx);
    if (s.combo.length === 1) {
      s.warnDur = randRange(...WARN_SINGLE) / mult;
      s.defendDur = randRange(...DEF_SINGLE) / mult;
    } else {
      s.warnDur = randRange(...WARN_COMBO) / mult;
      s.defendDur = randRange(...DEF_COMBO) / mult;
    }
    // Feints need a guaranteed reaction window after the reveal.
    if (s.feintNow) s.defendDur = Math.max(s.defendDur, FEINT_TOTAL_DEFEND);
  }

  function advance(s: GameState) {
    s.round += 1;
    if (s.round >= TOTAL_ROUNDS && !s.speedMode) {
      s.speedMode = true;
      s.speedMult = 1.5;
      s.speedRound = 0;
      s.screen = 'speedAlert';
      s.phaseStart = nowSec();
      return;
    }
    if (s.speedMode && !s.bossActive) {
      s.speedRound += 1;
      s.speedMult = 1.5 + s.speedRound * 0.1;
      // After SPEED_BOSS_TRIGGER speed rounds, summon the boss (HARD/EXTREME only).
      if (s.speedRound >= SPEED_BOSS_TRIGGER && BOSS_HP[s.diff] > 0) {
        s.bossActive = true;
        s.bossHpMax = BOSS_HP[s.diff];
        s.bossHp = s.bossHpMax;
        s.speedMult = 1.6; // boss tempo: stable, not escalating
        s.screen = 'bossIntro';
        s.phaseStart = nowSec();
        return;
      }
    }
    startRoundCombo(s);
  }

  // ── Main game loop ───────────────────────────────────────────────
  useEffect(() => {
    let raf = 0;
    let lastViewFlush = 0;

    const tick = () => {
      const s = stateRef.current;
      const frame = lastFrameRef.current;
      const now = nowSec();
      let kps: Keypoint[] | null = null;
      if (frame && poseUsable(frame.keypoints)) kps = frame.keypoints;

      // Render skeleton overlay every frame regardless of phase.
      drawOverlay(canvasRef.current, frame, kps, s);
      // Advance + draw particles, prune expired popups.
      tickParticles(canvasRef.current, effectsRef.current, now);
      if (prunePopups(effectsRef.current, now)) setPopupTick((t) => t + 1);

      // While paused, keep rendering skeleton but freeze game logic.
      if (s.paused) {
        raf = requestAnimationFrame(tick);
        return;
      }

      switch (s.screen) {
        case 'countdown': {
          const elapsed = now - s.phaseStart;
          const newN = 3 - Math.floor(elapsed);
          if (newN !== s.cntdn && newN >= 0) s.cntdn = newN;
          if (elapsed >= 4.0) {
            s.screen = 'play';
            startRoundCombo(s);
          }
          break;
        }

        case 'speedAlert': {
          if (now - s.phaseStart >= SPEED_ALERT_DUR) {
            s.screen = 'play';
            startRoundCombo(s);
          }
          break;
        }

        case 'bossIntro': {
          if (now - s.phaseStart >= BOSS_INTRO_DUR) {
            s.screen = 'play';
            startRoundCombo(s);
          }
          break;
        }

        case 'play': {
          const attack = s.combo[s.comboIdx];
          const elapsed = now - s.phaseStart;

          if (s.phase === 'warn') {
            if (elapsed >= s.warnDur) {
              s.phase = 'defend';
              s.phaseStart = now;
              s.defendPhaseStart = now;
            }
          } else if (s.phase === 'defend') {
            if (kps && !s.defended) {
              const raw = getDefense(kps);
              slipBufRef.current.push(raw);
              if (slipBufRef.current.length > 3) slipBufRef.current.shift();
              // Block is accepted instantly; slip needs 2 consecutive matching frames.
              let defense: Defense | null = null;
              if (raw && !raw.startsWith('SLIP')) {
                defense = raw;
              } else if (
                slipBufRef.current.length >= 2 &&
                slipBufRef.current[slipBufRef.current.length - 1] ===
                  slipBufRef.current[slipBufRef.current.length - 2] &&
                slipBufRef.current[slipBufRef.current.length - 1]
              ) {
                defense = slipBufRef.current[slipBufRef.current.length - 1];
              }
              if (defense && VALID_DEF[attack][defense]) {
                s.reactionTimes.push(now - s.defendPhaseStart);
                s.defended = true;
                s.counterArm = VALID_DEF[attack][defense]!;
                if (s.comboIdx < s.combo.length - 1) {
                  s.comboIdx += 1;
                  rollAttackTiming(s);
                  startAttack(s);
                } else {
                  s.phase = 'counter';
                  s.phaseStart = now;
                  punchRef.current = newPunchTracker();
                }
              }
            }
            if (elapsed >= s.defendDur && s.phase === 'defend') {
              s.pHp = Math.max(0, s.pHp - s.pDmg);
              s.resultOk = false;
              s.phase = 'result';
              s.phaseStart = now;
              triggerFailHit();
              if (s.pHp <= 0) s.screen = 'lose';
            }
          } else if (s.phase === 'counter') {
            if (kps) {
              if (elapsed < COUNTER_DELAY) {
                punchRef.current.prev = kps.map((k) => ({ ...k }));
                if (!punchRef.current.baseR) setPunchBaseline(punchRef.current, kps);
              } else if (!s.countered) {
                const punch = detectPunch(punchRef.current, kps);
                if (punch.side === s.counterArm) {
                  s.countered = true;
                  s.resultOk = true;
                  s.score += 1;
                  if (s.bossActive) {
                    s.bossHp = Math.max(0, s.bossHp - 1);
                  } else {
                    s.aiHp = Math.max(0, s.aiHp - 1);
                  }
                  triggerCounterHit(kps, s.counterArm, 1);
                  s.phase = 'result';
                  s.phaseStart = now;
                  if (s.bossActive) {
                    if (s.bossHp <= 0) s.screen = 'win';
                  } else if (s.aiHp <= 0) {
                    // For HARD/EXTREME, beating regular AI doesn't end the game —
                    // boss appears after the speed phase. For EASY/NORMAL it's a win.
                    if (BOSS_HP[s.diff] === 0) s.screen = 'win';
                  }
                }
              } else {
                detectPunch(punchRef.current, kps);
              }
            }
            if (elapsed >= COUNTER_DUR && s.phase === 'counter') {
              s.resultOk = true;
              s.phase = 'result';
              s.phaseStart = now;
            }
          } else if (s.phase === 'result') {
            if (now - s.phaseStart >= RESULT_DUR && s.screen === 'play') {
              advance(s);
            }
          }
          break;
        }
      }

      // Flush view ~30 times per second to keep React renders cheap.
      if (now - lastViewFlush > 0.033) {
        lastViewFlush = now;
        setView({ ...s });
      }

      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  // ESC toggles pause during play.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') togglePause();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [togglePause]);

  // Resize canvas to match the video element's intrinsic size.
  useEffect(() => {
    const c = canvasRef.current;
    const v = videoRef.current;
    if (!c || !v) return;
    const ro = new ResizeObserver(() => {
      if (v.videoWidth) {
        c.width = v.videoWidth;
        c.height = v.videoHeight;
      }
    });
    ro.observe(v);
    return () => ro.disconnect();
  }, []);

  // ── Render ───────────────────────────────────────────────────────
  const now = nowSec();
  const fx = effectsRef.current;
  const shaking = now < fx.shakeUntil;
  const flashing = now < fx.flashUntil;
  void popupTick;
  return (
    <div className={`game-root ${shaking ? 'shake' : ''} ${view.bossActive ? 'boss-mode' : ''}`}>
      <video ref={videoRef} className="cam" playsInline muted />
      <canvas ref={canvasRef} className="overlay" />
      {flashing && <div className="hit-flash" />}
      {fx.popups.length > 0 && (
        <div className="popups-layer">
          {fx.popups.map((p) => (
            <div
              key={p.id}
              className="dmg-popup"
              style={{ left: `${p.x}%`, top: `${p.y}%` }}
            >
              -{p.value}
            </div>
          ))}
        </div>
      )}

      {(status === 'loading-camera' || status === 'loading-model') && (
        <div className="loading">
          <div className="spinner" />
          <p>{status === 'loading-camera' ? '카메라 권한 요청 중...' : 'AI 모델 로드 중...'}</p>
        </div>
      )}

      {status === 'error' && (
        <div className="error-screen">
          <h2>⚠️ 카메라 또는 모델 로드 실패</h2>
          <p>{error}</p>
          <p className="hint">카메라 권한을 허용했는지 확인하세요.</p>
        </div>
      )}

      {view.screen === 'select' && (
        <DifficultySelect onPick={startGame} />
      )}

      {view.screen === 'countdown' && (
        <Countdown state={view} />
      )}

      {view.screen === 'speedAlert' && (
        <SpeedAlert />
      )}

      {view.screen === 'bossIntro' && (
        <BossIntro diff={view.diff} />
      )}

      {view.screen === 'play' && (
        <PlayOverlay state={view} kps={lastFrameRef.current?.keypoints ?? null} />
      )}

      {view.screen === 'play' && !view.paused && (
        <button className="pause-btn" onClick={togglePause} aria-label="일시정지">
          ⏸
        </button>
      )}

      {view.paused && view.screen === 'play' && (
        <PauseOverlay onResume={togglePause} onQuit={quitToMenu} />
      )}

      {view.screen === 'win' && <WinScreen state={view} onRestart={restart} />}
      {view.screen === 'lose' && <LoseScreen state={view} onRestart={restart} />}
    </div>
  );
}

function PauseOverlay({ onResume, onQuit }: { onResume: () => void; onQuit: () => void }) {
  return (
    <div className="overlay-screen dim pause-overlay">
      <h1>일시정지</h1>
      <div className="pause-actions">
        <button className="pause-resume" onClick={onResume}>계속하기</button>
        <button className="pause-quit" onClick={onQuit}>나가기</button>
      </div>
      <p className="muted hint">ESC 키로도 토글</p>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────
function Countdown({ state }: { state: GameState }) {
  const cfg = DIFF[state.diff];
  return (
    <div className="overlay-screen dim">
      <div className="diff-label" style={{ color: cfg.color }}>{cfg.label}</div>
      <div className="prep">준비!</div>
      <div className="cntdn">{state.cntdn > 0 ? state.cntdn : 'GO!'}</div>
    </div>
  );
}

function SpeedAlert() {
  return (
    <div className="overlay-screen dim speed-alert">
      <h1>SPEED MODE!</h1>
      <p>1.5배속으로 버텨라!</p>
      <p className="sub">방어 실패 = 게임 오버</p>
    </div>
  );
}

function BossIntro({ diff }: { diff: Difficulty }) {
  return (
    <div className="overlay-screen dim boss-intro">
      <p className="vs">VS</p>
      <h1 className="boss-name">{BOSS_NAME[diff] || 'BOSS'}</h1>
      <p className="boss-tag">페이크 공격을 조심해라</p>
    </div>
  );
}

function PlayOverlay({ state, kps }: { state: GameState; kps: Keypoint[] | null }) {
  const attack = state.combo[state.comboIdx];
  const guardOk = kps ? checkGuard(kps) : true;
  // Feint reveal happens FEINT_REVEAL_AT seconds into defend phase.
  const defendElapsed = state.phase === 'defend' ? nowSec() - state.phaseStart : 0;
  const revealed = state.feintNow && state.phase === 'defend' && defendElapsed >= FEINT_REVEAL_AT;
  const shownAttack: Side = state.feintNow && !revealed
    ? (attack === 'LEFT' ? 'RIGHT' : 'LEFT')
    : attack;

  return (
    <>
      <HUD state={state} />

      {(state.phase === 'warn' || state.phase === 'defend') && (
        <AttackArrow
          side={attack}
          phase={state.phase}
          feint={state.feintNow}
          revealed={revealed}
        />
      )}

      {state.phase === 'defend' && (
        <div className="defend-hints">
          <div className="title">방어하세요!</div>
          <div className="sub">
            {shownAttack === 'LEFT'
              ? '← 왼팔 올려서 막기  ·  → 오른쪽으로 고개 피하기'
              : '오른팔 올려서 막기 →  ·  ← 왼쪽으로 고개 피하기'}
          </div>
        </div>
      )}

      {state.phase === 'counter' && state.counterArm && (
        <div className="counter-banner">
          <h1>카운터!</h1>
          <p>{state.counterArm === 'RIGHT' ? '오른손' : '왼손'}으로 펀치!</p>
        </div>
      )}

      {state.phase === 'result' && (
        <div className={`result-flash ${state.resultOk ? (state.countered ? 'perfect' : 'ok') : 'fail'}`}>
          {state.resultOk ? (state.countered ? 'PERFECT!' : '성공! ✓') : '실패! ✗'}
        </div>
      )}

      {!guardOk && (state.phase === 'warn' || state.phase === 'defend') && (
        <div className="guard-warning">★ 가드 올려! ★</div>
      )}

      <PhaseBar state={state} />
    </>
  );
}

function PhaseBar({ state }: { state: GameState }) {
  const elapsed = nowSec() - state.phaseStart;
  let total = 1;
  let color = '#888';
  if (state.phase === 'warn') { total = state.warnDur; color = '#ff3a55'; }
  else if (state.phase === 'defend') { total = state.defendDur; color = '#3ad5ff'; }
  else if (state.phase === 'counter') { total = COUNTER_DUR; color = '#3aff7a'; }
  else return null;
  const ratio = Math.max(0, 1 - elapsed / total);
  return (
    <div className="phase-bar">
      <div style={{ width: `${ratio * 100}%`, background: color }} />
    </div>
  );
}

function WinScreen({ state, onRestart }: { state: GameState; onRestart: () => void }) {
  const avgMs = state.reactionTimes.length
    ? Math.round((state.reactionTimes.reduce((a, b) => a + b, 0) / state.reactionTimes.length) * 1000)
    : 0;
  const bestMs = state.reactionTimes.length
    ? Math.round(Math.min(...state.reactionTimes) * 1000)
    : 0;
  return (
    <div className="overlay-screen dim end-screen win">
      <h1>승리!</h1>
      <p className="big">카운터 {state.score}번</p>
      {state.speedMode && state.speedRound > 0 && (
        <p>스피드 {state.speedRound}라운드 생존</p>
      )}
      {state.reactionTimes.length > 0 && (
        <p className="muted">평균 반응속도 {avgMs}ms · 최고 {bestMs}ms</p>
      )}
      <button onClick={onRestart}>다시하기</button>
    </div>
  );
}

function LoseScreen({ state, onRestart }: { state: GameState; onRestart: () => void }) {
  return (
    <div className="overlay-screen dim end-screen lose">
      <h1>{state.speedMode ? `스피드 ${state.speedRound}라운드 생존` : '패배'}</h1>
      <p className="big">카운터 {state.score}번</p>
      <button onClick={onRestart}>다시하기</button>
    </div>
  );
}

// ── Canvas renderer ──────────────────────────────────────────────
function drawOverlay(
  canvas: HTMLCanvasElement | null,
  frame: PoseFrame | null,
  kps: Keypoint[] | null,
  s: GameState,
) {
  if (!canvas || !frame) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  if (canvas.width !== frame.width) canvas.width = frame.width;
  if (canvas.height !== frame.height) canvas.height = frame.height;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!kps) return;

  // Skeleton lines
  ctx.strokeStyle = 'rgba(120, 120, 140, 0.7)';
  ctx.lineWidth = 2;
  for (const [a, b] of COCO_CONN) {
    if (visible(kps[a]) && visible(kps[b])) {
      ctx.beginPath();
      ctx.moveTo(kps[a].x, kps[a].y);
      ctx.lineTo(kps[b].x, kps[b].y);
      ctx.stroke();
    }
  }

  // Keypoints
  ctx.fillStyle = 'rgba(60, 220, 255, 0.95)';
  for (const k of kps) {
    if (visible(k)) {
      ctx.beginPath();
      ctx.arc(k.x, k.y, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // When defended successfully, briefly highlight the counter arm.
  if (s.phase === 'counter' && s.counterArm) {
    highlightCounterArm(ctx, kps, s.counterArm);
  }
}

function highlightCounterArm(ctx: CanvasRenderingContext2D, kps: Keypoint[], side: Side) {
  const arms = sideArmIdx(kps, side);
  ctx.strokeStyle = 'rgba(60, 255, 200, 0.9)';
  ctx.lineWidth = 8;
  for (let i = 0; i < arms.length - 1; i++) {
    const a = kps[arms[i]], b = kps[arms[i + 1]];
    if (visible(a) && visible(b)) {
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }
  }
  const wrist = kps[arms[2]];
  if (visible(wrist)) {
    ctx.fillStyle = 'rgba(60, 255, 200, 0.95)';
    ctx.beginPath();
    ctx.arc(wrist.x, wrist.y, 14, 0, Math.PI * 2);
    ctx.fill();
  }
}

function sideArmIdx(kps: Keypoint[], side: Side) {
  // Spatial right arm == screen right; in mirrored frames the user's L shoulder
  // ends up on screen-right when their L_SH.x > R_SH.x.
  const lOnRight = kps[KP.L_SH].x > kps[KP.R_SH].x;
  if (side === 'RIGHT') {
    return lOnRight ? [KP.L_SH, KP.L_EL, KP.L_WR] : [KP.R_SH, KP.R_EL, KP.R_WR];
  }
  return lOnRight ? [KP.R_SH, KP.R_EL, KP.R_WR] : [KP.L_SH, KP.L_EL, KP.L_WR];
}

function nowSec() { return performance.now() / 1000; }

// ── Effect helpers (module-level, no state captured) ─────────────
function tickParticles(
  canvas: HTMLCanvasElement | null,
  fx: { particles: Particle[] },
  now: number,
) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const dt = 1 / 60;
  const drag = 0.92;
  const grav = 600;
  const next: Particle[] = [];
  for (const p of fx.particles) {
    p.life -= dt;
    if (p.life <= 0) continue;
    p.vx *= drag;
    p.vy = p.vy * drag + grav * dt;
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    next.push(p);
    const t = p.life / p.maxLife;
    ctx.globalAlpha = Math.max(0, t);
    ctx.fillStyle = t > 0.5 ? '#fff' : '#ffd23a';
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3 + 4 * t, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
  fx.particles = next;
  void now;
}

function prunePopups(fx: { popups: DamagePopup[] }, now: number): boolean {
  const before = fx.popups.length;
  fx.popups = fx.popups.filter((p) => now - p.born < 0.9);
  return fx.popups.length !== before;
}
