import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { pollJob } from '../api.js';

export default function Recommendation() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    let alive = true;
    (async () => {
      await pollJob(jobId, (j) => { if (alive) setJob(j); }, 1000);
    })().catch((e) => alive && setJob({ status: 'failed', error: e.message }));
    return () => { alive = false; };
  }, [jobId]);

  if (!job) {
    return <Center>분석 작업을 시작하는 중...</Center>;
  }
  if (job.status === 'failed') {
    return (
      <Center>
        <p className="text-red-300 mb-4">분석에 실패했습니다.</p>
        <pre className="bg-red-900/20 border border-red-900/40 p-4 rounded-lg text-xs text-red-200 max-w-xl whitespace-pre-wrap">{job.error}</pre>
        <button onClick={() => nav('/coach/upload')} className="btn-secondary mt-6">다시 시도</button>
      </Center>
    );
  }
  if (job.status !== 'done') {
    return (
      <div className="max-w-3xl mx-auto px-6 py-24 text-center">
        <h2 className="font-display text-4xl tracking-wider mb-8">분석 중</h2>
        <div className="bar mx-auto max-w-md">
          <div className="bar-fill" style={{ width: `${Math.round((job.progress ?? 0) * 100)}%` }} />
        </div>
        <p className="mt-4 text-sm text-zinc-400">
          {job.progress_label || '준비 중'} · {Math.round((job.progress ?? 0) * 100)}%
        </p>
        <p className="mt-2 text-xs text-zinc-500">RTMPose 모델 첫 로드는 30초~1분 정도 걸릴 수 있습니다.</p>
      </div>
    );
  }

  const result = job.result;
  const top = result.coaches[0];

  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      <p className="text-accent text-sm font-medium tracking-wider uppercase mb-2">분석 완료</p>
      <h1 className="font-display text-5xl tracking-wider mb-2">
        당신은 <span className="text-accent">{top.display.name}</span> 스타일입니다
      </h1>
      <p className="text-zinc-400 mb-10">{top.display.style} · {top.display.tagline}</p>

      <div className="grid md:grid-cols-2 gap-4">
        {result.coaches.map((c, i) => (
          <div key={c.coach}
               className={`rounded-2xl p-6 border ${i === 0 ? 'border-accent/60 bg-accent/5' : 'border-white/5 bg-canvas'}`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-zinc-500 font-medium tracking-wider uppercase">{i === 0 ? '추천' : `#${i + 1}`}</p>
                <h3 className="font-display text-2xl mt-1">{c.display.name}</h3>
                <p className="text-sm text-zinc-400">{c.display.style}</p>
              </div>
              <div className="text-right">
                <p className="font-display text-3xl text-accent">{(c.confidence * 100).toFixed(0)}%</p>
                <p className="text-xs text-zinc-500">유사도</p>
              </div>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
              <Metric label="자세 유사도" value={c.pose_similarity} />
              <Metric label="펀치 유사도" value={c.punch_similarity} hidden={!c.used_punch} />
              <Metric label="자세 거리(z)" value={c.pose_distance} fmt="num" />
              <Metric label="펀치 거리(z)" value={c.punch_distance} fmt="num" hidden={!c.used_punch} />
            </div>
            <div className="mt-6 grid grid-cols-2 gap-2">
              <button onClick={() => nav(`/coach/realtime/${c.coach}`)}
                      className="btn-primary text-sm py-2">
                실시간 코칭
              </button>
              <button onClick={() => nav(`/coach/coaching/${c.coach}`)}
                      className="btn-secondary text-sm py-2">
                영상 분석
              </button>
            </div>
          </div>
        ))}
      </div>

      <p className="mt-10 text-xs text-zinc-500 text-center">
        분석 프레임: {result.frames_used} · 감지된 펀치:&nbsp;
        {Object.entries(result.user_punch_counts || {})
          .filter(([, n]) => n > 0)
          .map(([k, n]) => `${k} ${n}`)
          .join(' · ') || '없음'}
      </p>
    </div>
  );
}

function Metric({ label, value, fmt = 'pct', hidden }) {
  if (hidden) return <div />;
  let text = '—';
  if (value != null) {
    text = fmt === 'pct' ? `${(value * 100).toFixed(1)}%` : value.toFixed(2);
  }
  return (
    <div className="bg-white/5 rounded-lg px-3 py-2">
      <p className="text-zinc-500">{label}</p>
      <p className="text-zinc-100 text-sm font-medium mt-0.5">{text}</p>
    </div>
  );
}

function Center({ children }) {
  return <div className="max-w-3xl mx-auto px-6 py-24 text-center">{children}</div>;
}
