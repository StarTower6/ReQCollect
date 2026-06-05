import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message, QrOption } from '@/types'
import { fetchHistory } from '@/api/session'

let _msgIdCounter = 0

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const streaming = ref(false)

  async function loadHistory(sessionId: string) {
    messages.value = []
    const msgs = await fetchHistory(sessionId)
    for (const m of msgs) {
      messages.value.push({
        role: m.role === 'user' ? 'user' : (m.role === 'event' ? 'event' : 'assistant'),
        content: m.content || '',
        created_at: m.created_at || '',
        _id: m.id || `msg-${_msgIdCounter++}`,
      })
    }
  }

  function addMessage(role: Message['role'], content: string, extra?: Partial<Message>) {
    const msg: Message = {
      role,
      content,
      _id: `msg-${_msgIdCounter++}`,
      created_at: new Date().toISOString(),
      ...extra,
    }
    messages.value = [...messages.value, msg]
    return msg
  }

  function updateLastAssistant(content: string) {
    const msgs = messages.value
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'assistant') {
        msgs[i].content = content
        messages.value = [...messages.value]
        return
      }
    }
  }

  function addQuickReplies(role: Message['role'], content: string, qrList: QrOption[], mode: 'single' | 'multi') {
    const msg = addMessage(role, content)
    msg._quickReplies = qrList
    msg._qrMode = mode
    msg._qrSelected = new Set()
    msg._qrDisabled = false
    return msg
  }

  function clear() {
    messages.value = []
  }

  return { messages, streaming, loadHistory, addMessage, updateLastAssistant, addQuickReplies, clear }
})
