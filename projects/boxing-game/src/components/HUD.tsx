import { DIFF, TOTAL_ROUNDS } from '../game/config';
import type { GameState } from '../game/types';

export function HUD({ state }: { state: GameState }) {
  const cfg = DIFF[state.diff];
  const aiHpStars = '★'.repeat(state.aiHp) + '☆'.repeat(cfg.aiHp - state.aiHp);
  const hpRatio = Math.max(0, state.pHp / state.pHpMax);
  const hpColor = hpRatio > 0.5 ? '#3aff7a' : hpRatio > 0.25 ? '#ffb83a' : '#ff3a55';

  return (
    <div className="hud">
      <div className="hud-top">
        <div className="round-info">
          {state.bossActive ? (
            <span className="boss">⚔ BOSS</span>
          ) : state.speedMode ? (
            <span className="speed">SPEED ×{state.speedMult.toFixed(1)} · #{state.speedRound + 1}</span>
          ) : (
            <span>Round {state.round + 1}/{TOTAL_ROUNDS}</span>
          )}
          <span className="combo">  Combo {state.comboIdx + 1}/{state.combo.length}</span>
        </div>
        <div className="ai-hp">
          {state.bossActive
            ? <span style={{ color: '#ff3a55' }}>BOSS: {'❤'.repeat(state.bossHp)}{'♡'.repeat(state.bossHpMax - state.bossHp)}</span>
            : <>AI: <span style={{ color: '#3ad5ff' }}>{aiHpStars}</span></>}
        </div>
        <div className="player-hp">
          <span className="hp-label">{state.pDmg === 0 ? 'HP ∞' : `HP ${state.pHp}`}</span>
          <div className="hp-bar"><div style={{ width: `${hpRatio * 100}%`, background: hpColor }} /></div>
        </div>
      </div>
      <div className="hud-bottom">
        <span>Score: {state.score}</span>
        {state.reactionTimes.length > 0 && (
          <span className="muted">
            Avg react: {Math.round((state.reactionTimes.reduce((a, b) => a + b, 0) / state.reactionTimes.length) * 1000)}ms
          </span>
        )}
      </div>
    </div>
  );
}
