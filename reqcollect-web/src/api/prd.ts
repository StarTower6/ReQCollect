import { apiGet } from './client'
import type { PrdRecord } from '@/types'

export async function fetchPrd(sessionId: string): Promise<PrdRecord | null> {
  try {
    const data = await apiGet<{ success: boolean; prd: PrdRecord }>(`/pm/prd/${encodeURIComponent(sessionId)}`)
    return data.prd
  } catch {
    return null
  }
}

export async function fetchPrdById(prdId: string): Promise<PrdRecord | null> {
  try {
    const data = await apiGet<{ success: boolean; prd: PrdRecord }>(`/pm/prd/by-id/${encodeURIComponent(prdId)}`)
    return data.prd
  } catch {
    return null
  }
}
