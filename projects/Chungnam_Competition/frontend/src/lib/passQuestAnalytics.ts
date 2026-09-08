/**
 * 향후 User Feedback Learning / 대시보드용 클라이언트 이벤트(베스트 에포트).
 * 서버가 /api/log/pass-quest-event 를 제공할 때만 전송합니다.
 */
export type PassQuestAnalyticsEvent =
  | 'pass_quest_view'
  | 'pass_quest_select'
  | 'pass_quest_alternative_view'
  | 'pass_quest_mission_replace'
  | 'pass_quest_complete'
  | 'pass_quest_share'

export function logPassQuestEvent(
  event: PassQuestAnalyticsEvent,
  payload?: Record<string, unknown>,
): void {
  if (typeof window === 'undefined') return
  try {
    void window.fetch('/api/log/pass-quest-event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event,
        payload: payload ?? {},
        path: window.location.pathname,
      }),
      keepalive: true,
    })
  } catch {
    /* ignore */
  }
}
