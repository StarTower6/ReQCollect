/* ── Workspace Files API ── */

import { apiGet, apiPost, apiDelete } from './client'

export interface WorkspaceFile {
  path: string
  size: number
  type: string
  source: string
  uploaded_at: string
  summary: string
}

export async function fetchWorkspaceFiles(
  wsId: string,
  pattern?: string
): Promise<WorkspaceFile[]> {
  const params = pattern ? `?pattern=${encodeURIComponent(pattern)}` : ''
  const res: any = await apiGet(`/workspaces/${wsId}/files${params}`)
  return res.files
}

export async function readWorkspaceFile(
  wsId: string,
  path: string,
  maxChars?: number
): Promise<any> {
  const params = maxChars ? `?max_chars=${maxChars}` : ''
  const res: any = await apiGet(
    `/workspaces/${wsId}/files/${encodeURIComponent(path)}${params}`
  )
  return res.file
}

export async function deleteWorkspaceFile(
  wsId: string,
  path: string
): Promise<void> {
  await apiDelete(`/workspaces/${wsId}/files/${encodeURIComponent(path)}`)
}
