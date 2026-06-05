import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Session } from '@/types'
import { fetchSessions, deleteSessionApi } from '@/api/session'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const currentId = ref<string | null>(null)
  const searchQuery = ref('')

  const filteredSessions = computed(() => {
    const q = searchQuery.value.trim().toLowerCase()
    if (!q) return sessions.value
    return sessions.value.filter(s =>
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

  function newSession(): string {
    const id = 'session-' + Date.now()
    currentId.value = id
    return id
  }

  async function remove(sessionId: string) {
    await deleteSessionApi(sessionId)
    sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
    if (currentId.value === sessionId) {
      currentId.value = null
    }
  }

  return { sessions, currentId, searchQuery, filteredSessions, load, setCurrent, newSession, remove }
})
