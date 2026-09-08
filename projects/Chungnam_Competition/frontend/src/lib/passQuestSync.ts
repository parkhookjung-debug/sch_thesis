import type { PassQuestCard, PassQuestRerankMeta, RecommendResponse } from '@/types'
import type { TripFormState } from '@/lib/tripParams'
import { readFetchErrorMessage } from '@/lib/apiErrorMessage'

export async function mergeSyncedPassQuest(
  data: RecommendResponse,
  form: TripFormState,
): Promise<RecommendResponse> {
  const tc = data.top_course
  const pq = data.pass_quest
  if (!tc || !pq?.enabled) return data
  const res = await window.fetch('/api/pass-quest/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      course: tc,
      weather: data.weather,
      intent: {
        companion: form.companion,
        trip_goal: form.tripGoal,
        duration: form.tripDuration,
        transport: form.transport,
        adult_count: form.adultCount,
        child_count: form.childCount,
        meal_preference: form.mealPreference,
      },
      pass_context: {
        tourpass_mode: form.tourpassMode,
        tourpass_ticket_type: form.tourpassTicketType,
        benefit_priority: form.benefitPriority,
        pass_goal: form.passGoal,
        purchased_status: form.purchasedStatus,
      },
      recommendations: data.recommendations ?? [],
      city: data.city,
    }),
  })
  if (!res.ok) {
    throw new Error(await readFetchErrorMessage(res, `패스퀘스트 동기화 오류 (${res.status})`))
  }
  const json = (await res.json()) as {
    top_pass_quest?: PassQuestCard | null
    pass_quest_rerank?: PassQuestRerankMeta
  }
  if (!json.top_pass_quest) return data
  return {
    ...data,
    pass_quest: {
      ...pq,
      top_pass_quest: json.top_pass_quest,
      pass_quest_rerank: json.pass_quest_rerank ?? pq.pass_quest_rerank,
    },
  }
}
