import type { RequirementProfile } from '@/types'
import { apiGet } from './client'

export async function fetchProfile(sessionId: string): Promise<RequirementProfile> {
  const data = await apiGet<{ success: boolean; profile: RequirementProfile }>(
    `/pm/profile/${encodeURIComponent(sessionId)}`
  )
  return data.profile
}
