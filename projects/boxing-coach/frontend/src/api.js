/** Tiny fetch wrapper for the backend API. */
const BASE = '/api';

async function handle(res) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText} — ${text}`);
  }
  return res.json();
}

export async function getCoaches() {
  return handle(await fetch(`${BASE}/coaches`));
}

export async function analyzeStyle(file) {
  const form = new FormData();
  form.append('video', file);
  return handle(await fetch(`${BASE}/analyze-style`, { method: 'POST', body: form }));
}

export async function startCoachingSession(file, coachId) {
  const form = new FormData();
  form.append('video', file);
  form.append('coach', coachId);
  return handle(await fetch(`${BASE}/coaching-session`, { method: 'POST', body: form }));
}

export async function getJob(jobId) {
  return handle(await fetch(`${BASE}/jobs/${jobId}`));
}

/**
 * Poll a job until it's done or failed.
 * @param {string} jobId
 * @param {(job) => void} onUpdate
 * @param {number} intervalMs
 */
export async function pollJob(jobId, onUpdate, intervalMs = 1000) {
  while (true) {
    const job = await getJob(jobId);
    onUpdate?.(job);
    if (job.status === 'done' || job.status === 'failed') return job;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
