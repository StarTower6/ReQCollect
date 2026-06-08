<template>
  <div class="composer-wrap">
    <div class="composer">
      <textarea
        class="composer-textarea"
        rows="1"
        placeholder="描述您的业务需求..."
        v-model="text"
        @keydown="onKeydown"
        :disabled="disabled"
        ref="inputRef"
      ></textarea>
      <div class="composer-bar">
        <div class="tool-group">
          <button class="tool-btn active" type="button">深度挖掘</button>
          <button class="tool-btn" type="button" @click="toggleMode">
            {{ mode === 'one_shot' ? '一键生成' : '逐章确认' }}
          </button>
        </div>
        <div class="action-group">
          <button class="tool-btn upload-btn" type="button" @click="triggerUpload" title="上传文档">
            📎
          </button>
          <input
            ref="fileInputRef"
            type="file"
            accept=".md"
            hidden
            @change="handleFileSelect"
          />
          <button class="send-btn" type="button" @click="send" :disabled="disabled" aria-label="发送">↑</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'

const props = defineProps<{
  disabled: boolean
  mode: string
  sessionId: string | null
}>()

const emit = defineEmits<{
  send: [text: string]
  toggleMode: []
  fileUpload: [file: File]
}>()

const text = ref('')
const inputRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

function triggerUpload() {
  fileInputRef.value?.click()
}

function handleFileSelect(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  emit('fileUpload', file)
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
  nextTick(autoGrow)
}

function autoGrow() {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
    inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 180) + 'px'
  }
}

function send() {
  const msg = text.value.trim()
  if (!msg || props.disabled) return
  text.value = ''
  autoGrow()
  emit('send', msg)
}

function toggleMode() {
  emit('toggleMode')
}

function focus() {
  inputRef.value?.focus()
}

defineExpose({ focus })
</script>
