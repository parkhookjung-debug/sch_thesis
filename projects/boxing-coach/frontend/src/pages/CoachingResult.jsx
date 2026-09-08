import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getCoaches, pollJob, startCoachingSession } from '../api.js';

export default function CoachingResult() {
  const { coachId } = useParams();
  const [coach, setCoach] = useState(null);
  const [file, setFile] = useState(null);
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    getCoaches().then(({ coaches }) => {
      const c = coaches.find((x) => x.id === coachId);
      if (!c) setError('알 수 없는 코치입니다.');
      else setCoach(c);
    });
  }, [coachId]);

  async function onSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    setSubmitting(true);
    setJob({ status: 'pending', progress: 0, progress_label: '업로드 중' });
    try {
      const { job_id } = await startCoachingSession(file, coachId);
      await pollJob(job_id, (j) => setJob(j), 1000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (error && !coach) {
    return <div className="max-w-3xl mx-auto px-6 py-16 text-red-300">{error}</div>;
  }
  if (!coach) {
    return <div className="max-w-3xl mx-auto px-6 py-24 text-center text-zinc-400">코치 정보 불러오는 중...</div>;
  }

  const result = job?.status === 'done' ? job.result : null;

  return (
    <div className="max-w-5xl mx-auto px-6 py-14">
      <button onClick={() => nav('/coach/coaches')} className="text-xs text-zinc-500 hover:text-zinc-300">← 코치 변경</button>
      <h1 className="font-display text-5xl tracking-wider mt-3">{coach.name} 코칭 세션</h1>
      <p className="text-accent text-sm mt-1">{coach.style}</p>

      {!result && (
        <form onSubmit={onSubmit} className="mt-10 rounded-2xl bg-canvas border border-white/5 p-8">
          <label className="block">
            <span className="text-sm text-zinc-300">코칭 받을 영상 업로드</span>
            <input
              type="file"
              accept="video/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block mt-3 w-full text-sm text-zinc-300 file:mr-4 file:rounded-lg file:border-0 file:bg-accent file:text-white file:px-4 file:py-2 file:font-medium hover:file:bg-accent/90"
            />
          </label>
          {error && (
            <pre className="mt-4 p-3 bg-red-900/20 border border-red-900/40 rounded-lg text-xs text-red-200 whitespace-pre-wrap">{error}</pre>
          )}
          <button type="submit" className="btn-primary mt-6" disabled={!file || submitting}>
            {submitting ? '분석 중...' : '코칭 영상 생성'}
          </button>
        </form>
      )}

      {job && job.status !== 'done' && job.status !== 'failed' && (
        <div className="mt-10 rounded-2xl bg-canvas border border-white/5 p-8">
          <p className="font-display text-2xl tracking-wider mb-4">{job.progress_label || '진행 중'}</p>
          <div className="bar"><div className="bar-fill" style={{ width: `${Math.round((job.progress ?? 0) * 100)}%` }} /></div>
          <p className="mt-3 text-xs text-zinc-500">{Math.round((job.progress ?? 0) * 100)}%</p>
        </div>
      )}

      {job?.status === 'failed' && (
        <pre className="mt-6 bg-red-900/20 border border-red-900/40 p-4 rounded-lg text-xs text-red-200 whitespace-pre-wrap">{job.error}</pre>
      )}

      {result && (
        <div className="mt-10 grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2">
            <video controls className="w-full rounded-2xl border border-white/5 bg-black" src={result.video_url} />
          </div>
          <div className="rounded-2xl bg-canvas border border-white/5 p-6 space-y-5">
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider">평균 자세 점수</p>
              <p className="font-display text-5xl text-accent">{result.average_score}<span className="text-2xl text-zinc-500">/100</span></p>
            </div>
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">펀치 카운트</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {Object.entries(result.punch_counts).map(([k, v]) => (
                  <div key={k} className="flex justify-between bg-white/5 rounded-lg px-3 py-2">
                    <span className="text-zinc-400 uppercase">{k}</span>
                    <span className="font-medium">{v}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-zinc-500 mt-2">총 {result.total_punches} 회</p>
            </div>
            <div className="text-xs text-zinc-500 leading-relaxed">
              방향: {result.facing_right ? '우향(오르토독스)' : '좌향(사우스포)'} 자동 감지<br/>
              프레임: {result.frames_processed}/{result.frames_total}
            </div>
            <a href={result.video_url} download className="btn-secondary text-sm block text-center">결과 영상 다운로드</a>
          </div>
        </div>
      )}
    </div>
  );
}
