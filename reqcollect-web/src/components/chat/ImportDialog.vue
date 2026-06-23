<template>
  <el-dialog
    v-model="visible"
    title="导入会议记录"
    width="500px"
    :close-on-click-modal="false"
    @closed="handleClose"
  >
    <div class="import-body">
      <!-- Upload zone -->
      <div
        class="upload-zone"
        :class="{ 'drag-over': dragging }"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="handleDrop"
        @click="inputRef?.click()"
      >
        <input
          ref="inputRef"
          type="file"
          accept=".md"
          hidden
          @change="handleFileSelect"
        />
        <div v-if="!selectedFile" class="upload-placeholder">
          <span class="upload-icon">📄</span>
          <p>点击或拖拽 .md 文件到此处</p>
          <p class="upload-hint">支持 Markdown 格式，单个文件 ≤ 10MB</p>
        </div>
        <div v-else class="upload-preview">
          <span class="file-icon">📄</span>
          <div class="file-info">
            <span class="file-name">{{ selectedFile.name }}</span>
            <span class="file-size">{{ formatSize(selectedFile.size) }}</span>
          </div>
          <el-button size="small" type="danger" text @click="clearFile">移除</el-button>
        </div>
      </div>

      <!-- Progress -->
      <div v-if="importing" class="import-progress">
        <el-progress :percentage="progress" :stroke-width="6" />
        <p class="progress-text">{{ statusText }}</p>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false" :disabled="importing">取消</el-button>
      <el-button
        type="primary"
        :disabled="!selectedFile || importing"
        :loading="importing"
        @click="handleImport"
      >
        {{ importing ? '分析中...' : '开始导入' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useChatStore } from '@/stores/chat'
import { useProfileStore } from '@/stores/profile'
import { readSSEStream } from '@/api/client'
import { ElMessage } from 'element-plus'

const router = useRouter()
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const profileStore = useProfileStore()

const visible = defineModel<boolean>('visible', { default: false })
const emit = defineEmits<{ done: [] }>()

const inputRef = ref<HTMLInputElement>()
const selectedFile = ref<File | null>(null)
const dragging = ref(false)
const importing = ref(false)
const progress = ref(0)
const statusText = ref('')

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function handleDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) validateAndSet(file)
}

function handleFileSelect(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) validateAndSet(file)
}

function validateAndSet(file: File) {
  if (!file.name.toLowerCase().endsWith('.md')) {
    ElMessage.error('仅支持 .md 格式文件')
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 10MB')
    return
  }
  selectedFile.value = file
}

function clearFile() {
  selectedFile.value = null
  if (inputRef.value) inputRef.value.value = ''
}

function handleClose() {
  selectedFile.value = null
  progress.value = 0
  statusText.value = ''
  importing.value = false
}

async function handleImport() {
  if (!selectedFile.value) return

  importing.value = true
  progress.value = 10
  statusText.value = '正在上传文件...'

  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const resp = await fetch('/api/pm/import', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('reqcollect_token') || ''}`,
      },
      body: formData,
    })

    if (!resp.ok || !resp.body) {
      throw new Error(`HTTP ${resp.status}`)
    }

    progress.value = 30
    statusText.value = 'AI 正在分析文档...'
    let newSessionId = ''
    let sessionCreated = false

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      buffer = buffer.replace(/\r\n/g, '\n')
      const frames = buffer.split('\n\n')
      buffer = frames.pop() || ''

      for (const frame of frames) {
        const dataLine = frame.split('\n').find(l => l.startsWith('data: '))
        if (!dataLine) continue
        try {
          const event = JSON.parse(dataLine.slice(6))
          if (event.type === 'import_analysis') {
            newSessionId = event.data.session_id
            sessionCreated = true
          } else if (event.type === 'import_complete') {
            progress.value = 100
            statusText.value = '分析完成！'
          } else if (event.type === 'error') {
            throw new Error(event.data)
          }
        } catch { /* skip */ }
      }
    }

    if (sessionCreated && newSessionId) {
      await sessionStore.load()
      sessionStore.setCurrent(newSessionId)
      chatStore.loadHistory(newSessionId)
      profileStore.load(newSessionId)
      router.push(`/chat/${newSessionId}`)
      ElMessage.success('导入完成')
      emit('done')
      visible.value = false
    }
  } catch (e: any) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    importing.value = false
    progress.value = 0
  }
}
</script>

<style scoped>
.upload-zone {
  border: 2px dashed var(--line-strong);
  border-radius: 8px;
  padding: 32px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg);
}
.upload-zone:hover,
.upload-zone.drag-over {
  border-color: var(--brand);
  background: var(--brand-soft);
}
.upload-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 12px;
}
.upload-placeholder p {
  margin: 4px 0;
  color: var(--muted);
}
.upload-hint {
  font-size: 12px;
  color: var(--muted);
}
.upload-preview {
  display: flex;
  align-items: center;
  gap: 12px;
}
.file-icon {
  font-size: 28px;
}
.file-info {
  flex: 1;
  text-align: left;
  display: flex;
  flex-direction: column;
}
.file-name {
  font-weight: 500;
  color: var(--text);
}
.file-size {
  font-size: 12px;
  color: var(--muted);
}
.import-progress {
  margin-top: 20px;
}
.progress-text {
  text-align: center;
  font-size: 13px;
  color: var(--muted);
  margin-top: 8px;
}
</style>
