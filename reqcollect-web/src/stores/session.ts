import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Session } from '@/types'
import { fetchSessions, deleteSessionApi } from '@/api/session'
import { fetchWorkspaces } from '@/api/workspace'

const WS_STORAGE_KEY = 'reqcollect_workspace_id'

function matchesSearch(s: Session, query: string): boolean {
  return (s.project_name || '').toLowerCase().includes(query) ||
         (s.session_id || '').toLowerCase().includes(query)
}

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const currentId = ref<string | null>(null)
  const currentWorkspaceId = ref<string | null>(localStorage.getItem(WS_STORAGE_KEY))
  const searchQuery = ref('')
  const expandedWsId = ref<string | null>(null)
  const savedExpandedWsId = ref<string | null>(null)
  const workspaces = ref<any[]>([])

  const filteredSessions = computed(() => {
    const q = searchQuery.value.trim().toLowerCase()
    if (!q) return sessions.value
    return sessions.value.filter(s => matchesSearch(s, q))
  })

  const treeData = computed(() => {
    const q = searchQuery.value.trim().toLowerCase()
    const isSearching = !!q
    const nodes: Array<{
      type: 'workspace' | 'ungrouped'
      id: string
      name: string
      count: number
      sessions: Session[]
      expanded: boolean
    }> = []

    // 1. Workspace nodes
    for (const ws of workspaces.value) {
      const wsSessions = sessions.value.filter(s => s.workspace_id === ws.id)
      if (!isSearching && wsSessions.length === 0) continue

      const match = isSearching ? wsSessions.filter(s => matchesSearch(s, q)).length > 0 : true
      if (isSearching && !match && !(ws.name || '').toLowerCase().includes(q)) continue

      nodes.push({
        type: 'workspace',
        id: ws.id,
        name: ws.name,
        count: wsSessions.length,
        sessions: isSearching ? wsSessions.filter(s => matchesSearch(s, q)) : wsSessions,
        expanded: isSearching || expandedWsId.value === ws.id,
      })
    }

    // 2. Ungrouped sessions (workspace_id is empty string)
    const ungrouped = sessions.value.filter(s => !s.workspace_id)
    if (ungrouped.length > 0) {
      nodes.push({
        type: 'ungrouped',
        id: '__ungrouped__',
        name: '未分类会话',
        count: ungrouped.length,
        sessions: isSearching ? ungrouped.filter(s => matchesSearch(s, q)) : ungrouped,
        expanded: true,
      })
    }

    return nodes
  })

  async function load() {
    sessions.value = await fetchSessions()
  }

  async function loadWorkspaces() {
    try {
      workspaces.value = await fetchWorkspaces()
    } catch {
      // 静默降级
    }
  }

  function toggleWorkspace(id: string) {
    if (expandedWsId.value === id) {
      expandedWsId.value = null
    } else {
      expandedWsId.value = id
    }
  }

  function saveExpandState() {
    savedExpandedWsId.value = expandedWsId.value
  }

  function restoreExpandState() {
    if (savedExpandedWsId.value) {
      expandedWsId.value = savedExpandedWsId.value
      savedExpandedWsId.value = null
    }
  }

  function setCurrent(id: string) {
    currentId.value = id
    const session = sessions.value.find(s => s.session_id === id)
    if (session && session.workspace_id) {
      currentWorkspaceId.value = session.workspace_id
      localStorage.setItem(WS_STORAGE_KEY, session.workspace_id)
    }
    // Do NOT clear currentWorkspaceId when session not found yet:
    // newSession creates a local ID before the session is persisted,
    // and setCurrent gets called before sessions.value is refreshed.
  }

  function newSession(workspaceId?: string): string {
    const id = 'session-' + Date.now()
    currentId.value = id
    if (workspaceId) {
      currentWorkspaceId.value = workspaceId
      localStorage.setItem(WS_STORAGE_KEY, workspaceId)
    }
    return id
  }

  async function remove(sessionId: string) {
    await deleteSessionApi(sessionId)
    sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
    if (currentId.value === sessionId) {
      currentId.value = null
    }
  }

  function setWorkspace(wsId: string | null) {
    currentWorkspaceId.value = wsId
    if (wsId) {
      localStorage.setItem(WS_STORAGE_KEY, wsId)
    } else {
      localStorage.removeItem(WS_STORAGE_KEY)
    }
  }

  function clearWorkspace() {
    currentWorkspaceId.value = null
    localStorage.removeItem(WS_STORAGE_KEY)
  }

  return {
    sessions, currentId, currentWorkspaceId, searchQuery,
    filteredSessions, treeData,
    workspaces,
    expandedWsId,
    load, loadWorkspaces,
    setCurrent, newSession, remove, setWorkspace, clearWorkspace,
    toggleWorkspace,
    saveExpandState, restoreExpandState,
  }
})
