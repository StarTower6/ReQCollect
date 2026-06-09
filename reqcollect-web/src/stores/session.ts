import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Session } from '@/types'
import { fetchSessions, deleteSessionApi } from '@/api/session'

const WS_STORAGE_KEY = 'reqcollect_workspace_id'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const currentId = ref<string | null>(null)
  const currentWorkspaceId = ref<string | null>(localStorage.getItem(WS_STORAGE_KEY))
  const searchQuery = ref('')

  const filteredSessions = computed(() => {
    const q = searchQuery.value.trim().toLowerCase()
    let result = sessions.value
    if (currentWorkspaceId.value) {
      result = result.filter(s => s.workspace_id === currentWorkspaceId.value)
    }
    if (!q) return result
    return result.filter(s =>
      (s.project_name || '').toLowerCase().includes(q) ||
      (s.session_id || '').toLowerCase().includes(q)
    )
  })

  async function load() {
    sessions.value = await fetchSessions()
  }

  function setCurrent(id: string) {
    currentId.value = id
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

  return { sessions, currentId, currentWorkspaceId, searchQuery, filteredSessions, load, setCurrent, newSession, remove, setWorkspace, clearWorkspace }
})
