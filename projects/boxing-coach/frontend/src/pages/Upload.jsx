import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyzeStyle } from '../api.js';

export default function Upload() {
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const nav = useNavigate();

  async function onSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    setSubmitting(true);
    try {
      const { job_id } = await analyzeStyle(file);
      nav(`/coach/recommendation/${job_id}`);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <h1 className="font-display text-5xl tracking-wider mb-3">스타일 분석</h1>
      <p className="text-zinc-400 mb-10">
        측면 촬영, 5~30초 분량의 복싱 영상을 권장합니다. 영상이 없으면 건너뛰고 코치를 직접 선택할 수 있습니다.
      </p>

      <form onSubmit={onSubmit} className="rounded-2xl bg-canvas border border-white/5 p-8">
        <label className="block">
          <span className="text-sm text-zinc-300">복싱 영상 (mp4 / mov)</span>
          <input
            type="file"
            accept="video/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block mt-3 w-full text-sm text-zinc-300 file:mr-4 file:rounded-lg file:border-0 file:bg-accent file:text-white file:px-4 file:py-2 file:font-medium hover:file:bg-accent/90"
          />
        </label>

        {file && (
          <p className="mt-3 text-xs text-zinc-500">
            선택됨: <span className="text-zinc-300">{file.name}</span> · {(file.size / 1024 / 1024).toFixed(1)} MB
          </p>
        )}
        {error && (
          <pre className="mt-4 p-3 bg-red-900/20 border border-red-900/40 rounded-lg text-xs text-red-200 whitespace-pre-wrap">
            {error}
          </pre>
        )}

        <div className="mt-8 flex gap-3 flex-wrap">
          <button type="submit" className="btn-primary" disabled={!file || submitting}>
            {submitting ? '분석 시작 중...' : '분석 시작'}
          </button>
          <button type="button" className="btn-secondary" onClick={() => nav('/coach/coaches')}>
            영상 없이 코치 직접 선택
          </button>
        </div>
      </form>
    </div>
  );
}
