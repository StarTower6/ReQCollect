/* ── Workspace API ── */

import { apiGet, apiPost, apiPatch, apiDelete } from './client'

export async function fetchWorkspaces(): Promise<any[]> {
  const res: any = await apiGet('/workspaces')
  return res.workspaces
}

export async function fetchWorkspace(id: string): Promise<any> {
  const res: any = await apiGet(`/workspaces/${id}`)
  return res.workspace
}

export async function createWorkspace(data: { name: string; code?: string; description?: string }): Promise<any> {
  const res: any = await apiPost('/workspaces', data)
  return res.workspace
}

export async function updateWorkspace(id: string, data: any): Promise<any> {
  const res: any = await apiPatch(`/workspaces/${id}`, data)
  return res.workspace
}

export async function deleteWorkspace(id: string): Promise<void> {
  await apiDelete(`/workspaces/${id}`)
}

export async function fetchWorkspaceSessions(id: string): Promise<any[]> {
  const res: any = await apiGet(`/workspaces/${id}/sessions`)
  return res.sessions
}

/* ── Workspace Members ── */

export async function listWorkspaceMembers(wsId: string): Promise<any[]> {
  const res: any = await apiGet(`/workspaces/${wsId}/members`)
  return res.members
}

export async function addWorkspaceMember(
  wsId: string,
  userId: string,
  role: string = 'business',
): Promise<any> {
  const res: any = await apiPost(`/workspaces/${wsId}/members`, { user_id: userId, role })
  return res.member
}

export async function removeWorkspaceMember(wsId: string, userId: string): Promise<void> {
  await apiDelete(`/workspaces/${wsId}/members/${userId}`)
}
