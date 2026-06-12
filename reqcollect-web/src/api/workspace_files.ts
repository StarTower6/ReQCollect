/* ── Workspace Files API ── */

import { apiGet, apiPost, apiPatch, apiDelete } from './client'

export interface WorkspaceFile {
  path: string
  size: number
  type: string
  source: string
  uploaded_at: string
  summary: string
  analysis?: { summary: string; tags: string[]; domain: string }
}

export interface Folder {
  id: string
  name: string
  parent_id: string
  children?: Folder[]
  file_count?: number
}

export interface RelatedFile {
  path: string
  summary: string
  tags: string[]
  similarity: number
}

// ── Folders ──

export async function fetchFolders(wsId: string, tree?: boolean): Promise<Folder[]> {
  const params = tree ? '?tree=true' : ''
  const res: any = await apiGet(`/workspaces/${wsId}/folders${params}`)
  return res.folders || []
}

export async function createFolder(wsId: string, name: string, parentId?: string): Promise<Folder> {
  const res: any = await apiPost(`/workspaces/${wsId}/folders`, { name, parent_id: parentId || '' })
  return res.folder
}

export async function renameFolder(wsId: string, folderId: string, name: string): Promise<Folder> {
  const res: any = await apiPatch(`/workspaces/${wsId}/folders/${folderId}`, { name })
  return res.folder
}

export async function deleteFolder(wsId: string, folderId: string): Promise<void> {
  await apiDelete(`/workspaces/${wsId}/folders/${folderId}`)
}

export async function setFileFolder(wsId: string, filePath: string, folderId: string): Promise<void> {
  await apiPatch(`/workspaces/${wsId}/files/${encodeURIComponent(filePath)}/folder`, { folder_id: folderId })
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

export async function fetchRelatedFiles(
  wsId: string,
  path: string,
): Promise<RelatedFile[]> {
  const res: any = await apiGet(
    `/workspaces/${wsId}/files/related?path=${encodeURIComponent(path)}`
  )
  return res.related || []
}

export async function uploadWorkspaceFile(
  wsId: string,
  file: File,
  token: string
): Promise<any> {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(`/api/workspaces/${wsId}/files/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text.slice(0, 200))
  }
  return resp.json()
}
