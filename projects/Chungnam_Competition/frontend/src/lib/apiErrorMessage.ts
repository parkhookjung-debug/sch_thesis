/** FastAPI·프록시가 돌려주는 JSON `detail` 을 사용자 메시지로 쓴다. */
export async function readFetchErrorMessage(res: Response, fallback: string): Promise<string> {
  const ct = res.headers.get('content-type') || ''
  if (!ct.includes('application/json')) return fallback
  try {
    const j = (await res.json()) as { detail?: unknown }
    if (typeof j?.detail === 'string') return j.detail
    if (Array.isArray(j?.detail)) {
      const parts = j.detail.map((x) => (typeof x === 'object' && x && 'msg' in x ? String((x as { msg: unknown }).msg) : String(x)))
      if (parts.length) return parts.join('; ')
    }
    if (j?.detail != null && typeof j.detail !== 'object') return String(j.detail)
  } catch {
    /* ignore */
  }
  return fallback
}
