import { apiGet, apiDelete, apiPatch } from './client'
import type { Session } from '@/types'

export async function fetchSessions(): Promise<Session[]> {
  const data = await apiGet<{ success: boolean; sessions: Session[] }>('/pm/sessions')
  return data.sessions || []
}

export async function fetchHistory(sessionId: string): Promise<any[]> {
  const data = await apiGet<{ success: boolean; messages: any[] }>(`/pm/history/${encodeURIComponent(sessionId)}`)
  return data.messages || []
}

export async function deleteSessionApi(sessionId: string): Promise<boolean> {
  const data = await apiDelete<{ success: boolean }>(`/pm/sessions/${encodeURIComponent(sessionId)}`)
  return data.success
}

export async function pinSession(sessionId: string, isPinned: boolean): Promise<boolean> {
  const data = await apiPatch<{ success: boolean }>(`/pm/sessions/${encodeURIComponent(sessionId)}/pin`, { is_pinned: isPinned })
  return data.success
}
