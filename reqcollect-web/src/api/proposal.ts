/* ── Proposal API ── */

import { apiGet, apiPost, apiPatch, apiDelete } from './client'
import type { Proposal, ProposalCreate, ProposalUpdate } from '@/types'

export async function listProposals(
  workspaceId: string,
  params?: { status?: string; urgency?: string; priority?: string; limit?: number; offset?: number }
): Promise<{ proposals: Proposal[]; total: number }> {
  const query = params ? '?' + new URLSearchParams(
    Object.fromEntries(
      Object.entries(params).filter(([_, v]) => v != null).map(([k, v]) => [k, String(v)])
    )
  ).toString() : ''
  return apiGet(`/workspaces/${workspaceId}/proposals${query}`)
}

export async function getProposal(workspaceId: string, proposalId: string): Promise<Proposal> {
  const data = await apiGet<{ proposal: Proposal }>(`/workspaces/${workspaceId}/proposals/${proposalId}`)
  return data.proposal
}

export async function createProposal(workspaceId: string, body: ProposalCreate): Promise<Proposal> {
  const data = await apiPost<{ proposal: Proposal }>(`/workspaces/${workspaceId}/proposals`, body)
  return data.proposal
}

export async function updateProposal(workspaceId: string, proposalId: string, body: ProposalUpdate): Promise<Proposal> {
  const data = await apiPatch<{ proposal: Proposal }>(`/workspaces/${workspaceId}/proposals/${proposalId}`, body)
  return data.proposal
}

export async function deleteProposal(workspaceId: string, proposalId: string): Promise<void> {
  await apiDelete(`/workspaces/${workspaceId}/proposals/${proposalId}`)
}

/* ── SSE 提炼提案 ── */
export async function extractProposalSSE(
  sessionId: string,
  workspaceId: string,
  onField: (field: string, content: any) => void,
  onDone: (data: any) => void,
  onError: (err: string) => void,
): Promise<void> {
  const token = localStorage.getItem('reqcollect_token')
  const resp = await fetch('/api/pm/extract-proposal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ session_id: sessionId, workspace_id: workspaceId }),
  })
  if (!resp.ok || !resp.body) { onError(`HTTP ${resp.status}`); return }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let gotDone = false
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''
    for (const frame of frames) {
      const dataLine = frame.split('\n').find(l => l.startsWith('data: '))
      if (!dataLine) continue
      try {
        const event = JSON.parse(dataLine.slice(6))
        if (event.type === 'proposal_field') onField(event.field, event.content)
        else if (event.type === 'proposal_done') { gotDone = true; onDone(event.data) }
        else if (event.type === 'error') { gotDone = true; onError(event.data) }
      } catch { /* skip malformed frame */ }
    }
  }
  // Stream ended without proposal_done/error — this is abnormal
  if (!gotDone) {
    onError('服务器未返回完整结果，请重试')
  }
}
