import { DIFF, type Difficulty } from '../game/config';

const ORDER: Difficulty[] = ['EASY', 'NORMAL', 'HARD', 'EXTREME'];

export function DifficultySelect({ onPick }: { onPick: (d: Difficulty) => void }) {
  return (
    <div className="overlay-screen dim diff-select">
      <h1>BOXING DEFENSE</h1>
      <p className="muted">난이도를 선택하세요</p>
      <div className="diff-grid">
        {ORDER.map((d, i) => {
          const cfg = DIFF[d];
          return (
            <button
              key={d}
              className="diff-card"
              style={{ borderColor: cfg.color }}
              onClick={() => onPick(d)}
            >
              <span className="num" style={{ color: cfg.color }}>{i + 1}</span>
              <span className="label" style={{ color: cfg.color }}>{cfg.label}</span>
              <span className="desc">{cfg.desc}</span>
            </button>
          );
        })}
      </div>
      <p className="footer">10라운드 클리어 → 스피드 서바이벌 모드</p>
    </div>
  );
}
