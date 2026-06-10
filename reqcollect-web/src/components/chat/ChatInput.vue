<template>
  <div class="composer-wrap">
    <div class="composer">
      <!-- Referenced file tags -->
      <div v-if="referencedFiles.length" class="ref-tags">
        <el-tag v-for="(f, i) in referencedFiles" :key="i" closable size="small"
          @close="$emit('removeReference', f)" type="primary">
          📄 {{ f }}
        </el-tag>
      </div>
      <textarea
        class="composer-textarea"
        rows="1"
        placeholder="按 @ 引用工作区文件..."
        v-model="text"
        @keydown="onKeydown"
        @input="onInput"
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
          <button class="tool-btn upload-btn" type="button" @click="triggerUpload" title="上传文档">📎</button>
          <input ref="fileInputRef" type="file" accept=".md" hidden @change="handleFileSelect" />
          <button class="send-btn" type="button" @click="send" :disabled="disabled" aria-label="发送">↑</button>
        </div>
      </div>
    </div>
    <!-- @ file picker dropdown -->
    <div v-if="showFilePicker" class="fp-dropdown">
      <div class="fp-search">
        <input v-model="fileQuery" placeholder="搜索工作区文件..." autofocus />
      </div>
      <div class="fp-list">
        <div v-for="f in filteredFiles" :key="f.path" class="fp-item" @click="selectFile(f)">
          <span>{{ fileIcon(f.type) }}</span>
          <span class="fp-fname">{{ f.path }}</span>
          <span class="fp-ftype">{{ f.type }}</span>
        </div>
        <div v-if="filteredFiles.length === 0" class="fp-empty">无匹配文件</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchWorkspaceFiles } from '@/api/workspace_files'

const props = defineProps<{
  disabled: boolean
  mode: string
  sessionId: string | null
  referencedFiles: string[]
  workspaceId: string | null
}>()

const emit = defineEmits<{
  send: [text: string]
  toggleMode: []
  fileUpload: [file: File]
  reference: [filePath: string]
  removeReference: [filePath: string]
}>()

const text = ref('')
const inputRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const showFilePicker = ref(false)
const fileQuery = ref('')
const allFiles = ref<any[]>([])

const filteredFiles = computed(() => {
  const q = fileQuery.value.trim().toLowerCase()
  if (!q) return allFiles.value
  return allFiles.value.filter((f: any) =>
    f.path.toLowerCase().includes(q) || (f.summary || '').toLowerCase().includes(q)
  )
})

function fileIcon(type: string) {
  const m: Record<string, string> = { md: '📝', txt: '📄', json: '📋', docx: '📘', xlsx: '📊', pptx: '📙', png: '🖼️', jpg: '🖼️' }
  return m[type] || '📄'
}

watch(showFilePicker, async (v) => {
  if (v && props.workspaceId) {
    try {
      allFiles.value = await fetchWorkspaceFiles(props.workspaceId)
    } catch {
      allFiles.value = []
    }
  }
})

function onInput() {
  const len = text.value.length
  const lastChar = len > 0 ? text.value[len - 1] : ''
  const prevChar = len > 1 ? text.value[len - 2] : ''
  if (lastChar === '@' && (!prevChar || prevChar === ' ' || prevChar === '\n')) {
    fileQuery.value = ''
    showFilePicker.value = true
  }
  // Hide picker if backspaced past @
  if (showFilePicker.value && !text.value.includes('@')) {
    showFilePicker.value = false
  }
  nextTick(autoGrow)
}

function selectFile(f: any) {
  // Remove the trailing @ from text
  text.value = text.value.replace(/@\s*$/, '').replace(/\s+@\s*$/, '')
  showFilePicker.value = false
  emit('reference', f.path)
  nextTick(() => inputRef.value?.focus())
}

function triggerUpload() { fileInputRef.value?.click() }

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
  if (e.key === 'Escape' && showFilePicker.value) {
    showFilePicker.value = false
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
  if (showFilePicker.value) return
  text.value = ''
  autoGrow()
  emit('send', msg)
}

function toggleMode() { emit('toggleMode') }

function focus() { inputRef.value?.focus() }
defineExpose({ focus })
</script>

<style scoped>
.composer-wrap { position: relative; }
.composer { border-top: 1px solid var(--line, #e5e6eb); padding: 12px 16px; background: var(--panel, #fff); }
.ref-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px; }
.composer-textarea { width: 100%; border: none; outline: none; resize: none; font-size: 14px; font-family: inherit; min-height: 22px; max-height: 180px; line-height: 1.5; color: var(--text, #1d2129); background: transparent; }
.composer-textarea::placeholder { color: #c0c4cc; }
.composer-bar { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.tool-group { display: flex; gap: 4px; }
.tool-btn { border: 1px solid var(--line, #e5e6eb); background: #f7f8fa; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; color: #4e5969; transition: all .12s; }
.tool-btn:hover { background: #eef0f4; }
.tool-btn.active { background: #409eff; color: #fff; border-color: #409eff; }
.action-group { display: flex; gap: 6px; align-items: center; }
.upload-btn { font-size: 16px; padding: 2px 6px; }
.send-btn { width: 32px; height: 32px; border-radius: 8px; border: none; background: #409eff; color: #fff; font-size: 16px; cursor: pointer; transition: background .12s; }
.send-btn:hover { background: #337ecc; }
.send-btn:disabled { background: #c0c4cc; cursor: not-allowed; }
/* @ file picker dropdown */
.fp-dropdown { position: absolute; bottom: 100%; left: 16px; right: 16px; background: #fff; border: 1px solid #e5e6eb; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,.1); z-index: 100; max-height: 300px; display: flex; flex-direction: column; }
.fp-search { padding: 8px; border-bottom: 1px solid #f0f0f5; }
.fp-search input { width: 100%; border: 1px solid #e5e6eb; border-radius: 6px; padding: 6px 8px; font-size: 13px; outline: none; }
.fp-list { overflow-y: auto; flex: 1; }
.fp-item { display: flex; align-items: center; gap: 6px; padding: 6px 12px; cursor: pointer; font-size: 13px; }
.fp-item:hover { background: #f0f3f8; }
.fp-fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fp-ftype { font-size: 11px; color: #c0c4cc; }
.fp-empty { padding: 20px; text-align: center; color: #c0c4cc; font-size: 13px; }
</style>
