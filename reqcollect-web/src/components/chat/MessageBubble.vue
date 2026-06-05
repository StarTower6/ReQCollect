<template>
  <div class="msg-row" :class="msg.role">
    <div v-if="msg.role === 'assistant'" class="avatar">PM</div>
    <div class="bubble-wrap">
      <div class="msg-meta">
        <span>{{ msg.role === 'user' ? '你' : 'PM Agent' }}</span>
        <span v-if="msg.created_at">· {{ formatTime(msg.created_at) }}</span>
        <button v-if="msg.content" class="msg-copy-btn" @click="copyText(msg.content)" title="复制">📋</button>
      </div>
      <div v-if="msg.content" class="msg" :class="msg.role" v-html="rendered"></div>
      <div v-if="isTyping" class="msg assistant" style="padding:10px 0;display:flex;gap:4px;align-items:center;min-height:24px">
        <span class="typing-dot" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--muted)"></span>
        <span class="typing-dot" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--muted)"></span>
        <span class="typing-dot" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--muted)"></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, watch } from 'vue'
import type { Message } from '@/types'
import { marked } from 'marked'
import hljs from 'highlight.js'

const props = defineProps<{
  msg: Message
  isTyping?: boolean
  isStreaming?: boolean
}>()

const emit = defineEmits<{ scrollToBottom: [] }>()

function escapeHtml(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

const rendered = computed(() => {
  if (props.msg.role === 'user') return escapeHtml(props.msg.content)
  const html = marked.parse(props.msg.content, { async: false }) as string
  nextTick(() => {
    document.querySelectorAll('.msg.assistant pre code').forEach(block => {
      hljs.highlightElement(block as HTMLElement)
    })
  })
  return html
})

watch(() => props.msg.content, () => emit('scrollToBottom'))

function formatTime(dateStr: string) {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch { return '' }
}

function copyText(text: string) {
  navigator.clipboard.writeText(text).catch(() => {})
}
</script>
