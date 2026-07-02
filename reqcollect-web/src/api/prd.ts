import { apiGet, apiPatch } from './client'
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


/** Update PRD markdown (edit mode save) */
export async function updatePrd(prdId: string, body: { markdown: string; title?: string }): Promise<PrdRecord> {
  const data = await apiPatch<{ success: boolean; prd: PrdRecord }>(`/pm/prd/by-id/${encodeURIComponent(prdId)}`, body)
  return data.prd
}
