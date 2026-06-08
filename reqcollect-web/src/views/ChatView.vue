<template>
  <AppLayout>
    <ChatArea
      :messages="chatStore.messages"
      :streaming="chatStore.streaming"
      :mode="mode"
      :session-id="sessionStore.currentId"
      @send="handleSend"
      @send-quick="handleSend"
      @toggle-mode="toggleMode"
      @file-upload="handleFileUpload"
    />
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useChatStore } from '@/stores/chat'
import { useProfileStore } from '@/stores/profile'
import { readSSEStream } from '@/api/client'
import AppLayout from '@/components/layout/AppLayout.vue'
import ChatArea from '@/components/chat/ChatArea.vue'

const route = useRoute()
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const profileStore = useProfileStore()

const mode = ref<'one_shot' | 'incremental'>('one_shot')

watch(() => route.params.sessionId, (sid: any) => {
  if (sid && typeof sid === 'string') {
    sessionStore.setCurrent(sid)
    chatStore.loadHistory(sid)
    profileStore.load(sid)
  }
}, { immediate: true })

onMounted(() => {
  sessionStore.load()
})

function toggleMode() {
  mode.value = mode.value === 'one_shot' ? 'incremental' : 'one_shot'
}

async function handleFileUpload(file: File, sid: string) {
  chatStore.addMessage('event', `📄 已上传文档: ${file.name}，AI 正在分析...`)
  // Reload history after upload to pick up new messages from the SSE stream
  setTimeout(() => {
    chatStore.loadHistory(sid)
    profileStore.load(sid)
  }, 500)
}

async function handleSend(text: string) {
  if (!sessionStore.currentId) {
    const id = sessionStore.newSession()
    await sessionStore.load()
    chatStore.loadHistory(id)
    profileStore.load(id)
  }

  const sid = sessionStore.currentId!
  chatStore.addMessage('user', text)
  chatStore.streaming = true
  let currentAssistant: any = null

  readSSEStream({
    message: text,
    session_id: sid,
    mode: mode.value,
    use_knowledge: false,
  }, (event: any) => {
    switch (event.type) {
      case 'content':
        if (!currentAssistant) {
          currentAssistant = chatStore.addMessage('assistant', '')
        }
        currentAssistant.content += event.data
        chatStore.updateLastAssistant(currentAssistant.content)
        break
      case 'sufficiency':
        chatStore.addMessage('event', `需求完整度: ${Math.round(event.data.score * 100)}%`)
        profileStore.updateSufficiency(event.data.score)
        break
      case 'ready_to_generate':
      case 'awaiting_approval':
        chatStore.addQuickReplies(
          'event',
          event.data.message || '',
          event.type === 'ready_to_generate'
            ? [{ label: '生成 PRD', value: '生成PRD' }, { label: '继续补充需求', value: '继续补充需求' }]
            : [{ label: '继续生成下一章', value: '继续' }, { label: '先停止在这里', value: '先停止在这里' }],
          'single'
        )
        break
      case 'status':
        chatStore.addMessage('event', event.data.message || '')
        break
      case 'prd_complete':
        chatStore.addMessage('event', 'PRD 生成完成')
        break
      case 'prd_plan':
        if (event.data.sections) {
          chatStore.addMessage('event', 'PRD 大纲: ' + event.data.sections.map((s: any) => s.title).join(' / '))
        }
        break
      case 'section_start':
        chatStore.addMessage('event', `正在撰写: ${event.data.title} (${event.data.index}/${event.data.total})`)
        currentAssistant = null
        break
      case 'section_content':
        if (!currentAssistant) currentAssistant = chatStore.addMessage('assistant', '')
        currentAssistant.content += event.data
        chatStore.updateLastAssistant(currentAssistant.content)
        break
      case 'section_complete':
        currentAssistant = null
        break
      case 'error':
        chatStore.addMessage('event', 'Error: ' + (event.data || ''))
        break
    }
  }, (err) => {
    chatStore.addMessage('event', 'Error: ' + err.message)
    chatStore.streaming = false
  }, () => {
    chatStore.streaming = false
    sessionStore.load()
    if (sessionStore.currentId) profileStore.load(sessionStore.currentId)
  })
}
</script>
