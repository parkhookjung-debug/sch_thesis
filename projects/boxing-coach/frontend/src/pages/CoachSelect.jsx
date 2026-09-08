import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCoaches } from '../api.js';

export default function CoachSelect() {
  const [coaches, setCoaches] = useState(null);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    getCoaches().then(({ coaches }) => setCoaches(coaches)).catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16">
        <p className="text-red-300 text-sm">코치 목록을 불러오지 못했습니다: {error}</p>
        <p className="text-zinc-500 text-xs mt-2">백엔드가 실행 중인지 확인하세요 (uvicorn).</p>
      </div>
    );
  }
  if (!coaches) {
    return <div className="max-w-3xl mx-auto px-6 py-24 text-center text-zinc-400">불러오는 중...</div>;
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-16">
      <h1 className="font-display text-5xl tracking-wider mb-3">코치를 선택하세요</h1>
      <p className="text-zinc-400 mb-10">
        네 가지 스타일 중 하나를 선택하면 그 코치 버전으로 영상이 분석되고 자막 피드백이 합성됩니다.
      </p>

      <div className="grid md:grid-cols-2 gap-4">
        {coaches.map((c) => (
          <div key={c.id} className={`coach-card ${!c.ready ? 'opacity-50' : ''}`}>
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-display text-3xl tracking-wider">{c.name}</h3>
                <p className="text-accent text-sm mt-1">{c.style}</p>
                <p className="text-zinc-400 text-sm mt-3">{c.tagline}</p>
              </div>
              <span className={`text-[10px] px-2 py-1 rounded-full ${c.ready ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-200'}`}>
                {c.ready ? 'READY' : 'DATA 미생성'}
              </span>
            </div>
            <div className="mt-5 flex gap-2 text-[10px] text-zinc-500">
              <span className={`px-2 py-1 rounded ${c.ready ? 'bg-white/5' : 'bg-amber-500/10 text-amber-300'}`}>자세 DNA {c.ready ? '✓' : '✗'}</span>
              <span className={`px-2 py-1 rounded ${c.punch_dna_ready ? 'bg-white/5' : 'bg-amber-500/10 text-amber-300'}`}>펀치 DNA {c.punch_dna_ready ? '✓' : '✗'}</span>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-2">
              <button
                disabled={!c.ready}
                onClick={() => nav(`/coach/realtime/${c.id}`)}
                className="btn-primary text-sm py-2"
              >
                실시간 코칭
              </button>
              <button
                disabled={!c.ready}
                onClick={() => nav(`/coach/coaching/${c.id}`)}
                className="btn-secondary text-sm py-2"
              >
                영상 분석
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-10 text-xs text-zinc-500 leading-relaxed">
        * `DATA 미생성` 코치는 <code className="bg-white/5 px-1 rounded">backend/scripts/extract_videos.py</code> →&nbsp;
        <code className="bg-white/5 px-1 rounded">build_dna.py</code> 순서로 데이터를 생성하면 활성화됩니다.
      </div>
    </div>
  );
}
