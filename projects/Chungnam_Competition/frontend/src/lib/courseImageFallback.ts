/** 코스 히어로·스텝 썸네일 — 동일 출처 SVG(외부 CDN 차단·대기업망 대비) */
export const COURSE_IMAGE_FALLBACK = '/hero-course-placeholder.svg'

export function appImageSrc(src?: string | null): string {
  const raw = (src || '').trim()
  if (!raw) return COURSE_IMAGE_FALLBACK
  try {
    const u = new URL(raw, window.location.origin)
    const proxyHosts = new Set([
      'tong.visitkorea.or.kr',
      'cdn.visitkorea.or.kr',
      'api.visitkorea.or.kr',
      'visitkorea.or.kr',
      'www.visitkorea.or.kr',
      'korean.visitkorea.or.kr',
    ])
    if (proxyHosts.has(u.hostname)) {
      return `/api/proxy-external-image?url=${encodeURIComponent(u.href)}`
    }
    if (u.hostname === 'places.googleapis.com' && u.pathname.includes('/media')) {
      const match = u.pathname.match(/\/v1\/(places\/.+?)\/media/)
      if (match?.[1]) {
        return `/api/place-photo?name=${encodeURIComponent(match[1])}&maxHeightPx=720`
      }
    }
  } catch {
    return raw
  }
  return raw
}
