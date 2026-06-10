/* ── Wiki Page API ── */

import { apiGet, apiPost, apiPatch, apiDelete } from './client'

export interface WikiPage {
  id: string
  workspace_id: string
  title: string
  content: string
  created_by: string
  updated_by: string
  created_at: string
  updated_at: string
}

export interface BacklinkRef {
  id: string
  title: string
}

export interface WikiPageDetail {
  page: WikiPage
  backlinks: BacklinkRef[]
}

export async function fetchWikiPages(workspaceId: string): Promise<WikiPage[]> {
  const res: any = await apiGet(`/wiki?workspace_id=${encodeURIComponent(workspaceId)}`)
  return res.pages || []
}

export async function fetchWikiPage(pageId: string): Promise<WikiPage> {
  const res: any = await apiGet(`/wiki/${encodeURIComponent(pageId)}`)
  return res.page
}

export async function fetchWikiPageDetail(pageId: string): Promise<WikiPageDetail> {
  const res: any = await apiGet(`/wiki/${encodeURIComponent(pageId)}`)
  return { page: res.page, backlinks: res.backlinks || [] }
}

export async function createWikiPage(data: { workspace_id: string; title: string; content?: string }): Promise<WikiPage> {
  const res: any = await apiPost('/wiki', data)
  return res.page
}

export async function updateWikiPage(pageId: string, data: { title?: string; content?: string }): Promise<WikiPage> {
  const res: any = await apiPatch(`/wiki/${encodeURIComponent(pageId)}`, data)
  return res.page
}

export async function deleteWikiPage(pageId: string): Promise<void> {
  await apiDelete(`/wiki/${encodeURIComponent(pageId)}`)
}

export interface GraphNode {
  id: string
  label: string
  title: string
  value: number
}

export interface GraphEdge {
  from: string
  to: string
  title: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export async function fetchWikiGraph(workspaceId: string): Promise<GraphData> {
  const res: any = await apiGet(`/wiki/graph/${encodeURIComponent(workspaceId)}`)
  return res.graph || { nodes: [], edges: [] }
}

// ── AI-enhanced wiki endpoints ──

export async function aiCreateWikiPage(data: { workspace_id: string; title: string; context: string }): Promise<WikiPage> {
  const res: any = await apiPost('/wiki/ai/create', data)
  return res.page
}

export async function aiSuggestContent(data: { page_id: string; title: string; existing_content: string }): Promise<string> {
  const res: any = await apiPost('/wiki/ai/suggest', data)
  return res.suggestion
}

export async function aiCreateWikiFromPrd(data: { workspace_id: string; title: string; prd_markdown: string }): Promise<WikiPage> {
  const res: any = await apiPost('/wiki/ai/from-prd', data)
  return res.page
}
