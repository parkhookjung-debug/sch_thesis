import type { Side } from '../pose/detection';

export function AttackArrow({
  side, phase, feint, revealed,
}: {
  side: Side;
  phase: 'warn' | 'defend';
  feint?: boolean;
  revealed?: boolean;
}) {
  const isWarn = phase === 'warn';
  // During feint warn (or pre-reveal defend) we display the OPPOSITE side as a fake.
  const showFake = !!feint && !revealed;
  const displayed: Side = showFake ? (side === 'LEFT' ? 'RIGHT' : 'LEFT') : side;
  const flip = displayed === 'LEFT' ? '' : 'flipped';
  const fillWarn = 'rgba(255,58,85,0.85)';
  const fillDef  = 'rgba(58,213,255,0.85)';
  const fillFeint = 'rgba(180,90,255,0.9)';
  const stroke = isWarn ? '#ff3a55' : '#3ad5ff';
  return (
    <div
      className={`attack-arrow ${flip} ${isWarn ? 'warn' : 'defend'} ${feint ? 'feint' : ''} ${revealed ? 'revealed' : ''}`}
    >
      <svg viewBox="0 0 400 200" preserveAspectRatio="xMidYMid meet">
        <polygon
          points="20,100 160,30 160,75 380,75 380,125 160,125 160,170"
          fill={feint && revealed ? fillFeint : (isWarn ? fillWarn : fillDef)}
          stroke={feint && revealed ? '#c060ff' : stroke}
          strokeWidth="3"
        />
      </svg>
      <div className="label">
        {displayed === 'LEFT' ? '← 왼쪽 공격!' : '오른쪽 공격! →'}
      </div>
      {feint && revealed && <div className="feint-label">페이크!</div>}
    </div>
  );
}
