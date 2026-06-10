<template>
  <section class="chat-shell" aria-label="对话区">
    <div class="chat-scroll" ref="scrollRef">
      <div class="chat-inner">
        <!-- Welcome -->
        <div v-if="messages.length === 0 && !streaming" class="welcome">
          <div class="welcome-card">
            <div class="welcome-logo"></div>
            <div class="welcome-title">我是 ReQCollect，很高兴见到你！</div>
            <div class="welcome-subtitle">开始描述您的业务需求，我会帮您梳理并生成需求文档。</div>
            <div class="prompt-grid">
              <button class="prompt-card" type="button" @click="$emit('sendQuick', '我想做一个企业报销审批系统')">企业报销审批系统</button>
              <button class="prompt-card" type="button" @click="$emit('sendQuick', '我想做一个餐厅外卖智能客服系统')">餐厅外卖智能客服</button>
              <button class="prompt-card" type="button" @click="$emit('sendQuick', '生成 PRD')">基于当前信息生成 PRD</button>
              <button class="prompt-card" type="button" @click="$emit('toggleMode')">切换生成模式</button>
            </div>
          </div>
        </div>

        <!-- Messages -->
        <template v-for="(msg, idx) in displayMessages" :key="msg._id || idx">
          <div v-if="msg.role === 'event'" class="event">{{ msg.content }}</div>
          <MessageBubble
            v-else-if="msg.role === 'user' || msg.role === 'assistant'"
            :msg="msg"
            :is-typing="streaming && idx === displayMessages.length - 1 && msg.role === 'assistant' && !msg.content"
            :is-streaming="streaming"
            @scroll-to-bottom="scrollToBottom"
          />
          <QuickReplyBar
            v-if="msg._quickReplies && msg._quickReplies.length"
            :replies="msg._quickReplies"
            :mode="msg._qrMode || 'single'"
            :disabled="msg._qrDisabled || false"
            @select="(v: string) => handleQrSelect(msg, v)"
            @submit="(v: string) => handleQrSubmit(msg, v)"
          />
        </template>
      </div>
    </div>
    <!-- Upload indicator -->
    <div v-if="uploading" class="upload-indicator">
      <el-progress :percentage="uploadProgress" :stroke-width="4" />
      <span class="upload-label">{{ uploadStatus }}</span>
    </div>
    <ChatInput
      :disabled="streaming"
      :mode="mode"
      :session-id="sessionId"
      :referenced-files="referencedFiles"
      :workspace-id="workspaceId"
      @send="(v) => $emit('send', v)"
      @toggle-mode="$emit('toggleMode')"
      @file-upload="handleFileUpload"
      @reference="(fp) => $emit('reference', fp)"
      @remove-reference="(fp) => $emit('removeReference', fp)"
      ref="chatInputRef"
    />
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import type { Message, QrOption } from '@/types'
import MessageBubble from './MessageBubble.vue'
import QuickReplyBar from './QuickReplyBar.vue'
import ChatInput from './ChatInput.vue'

const props = defineProps<{
  messages: Message[]
  streaming: boolean
  mode: string
  sessionId: string | null
  referencedFiles: string[]
  workspaceId: string | null
}>()

const emit = defineEmits<{
  send: [text: string]
  sendQuick: [text: string]
  toggleMode: []
  fileUpload: [file: File, sessionId: string]
  reference: [filePath: string]
  removeReference: [filePath: string]
}>()

const scrollRef = ref<HTMLElement | null>(null)
const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')

async function handleFileUpload(file: File) {
  if (!props.sessionId) {
    ElMessage.warning('请先创建一个会话再上传文件')
    return
  }
  uploading.value = true
  uploadProgress.value = 10
  uploadStatus.value = '上传中...'
  try {
    const formData = new FormData()
    formData.append('file', file)
    const resp = await fetch(`/api/pm/sessions/${props.sessionId}/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('reqcollect_token') || ''}` },
      body: formData,
    })
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)

    uploadProgress.value = 40
    uploadStatus.value = 'AI 正在分析...'

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
            uploadProgress.value = 70
          } else if (event.type === 'content' && typeof event.data === 'string') {
            uploadProgress.value = 85
          }
        } catch { /* skip */ }
      }
    }
    uploadProgress.value = 100
    uploadStatus.value = '完成'
    ElMessage.success(`「${file.name}」已上传并分析`)
    emit('fileUpload', file, props.sessionId)
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    setTimeout(() => { uploading.value = false; uploadProgress.value = 0 }, 1000)
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.streaming, scrollToBottom)

// Display messages with quick reply extraction
const displayMessages = computed(() => {
  const msgs = props.messages.map(m => ({ ...m, _qrSelected: m._qrSelected ? new Set(m._qrSelected) : undefined }))
  for (let i = msgs.length - 1; i >= 0; i--) {
    const m = msgs[i]
    const orig = props.messages[i]
    if (m.role === 'assistant' && m.content && !props.streaming) {
      if (!orig._qrProcessed && !m._quickReplies) {
        orig._qrProcessed = true
        const groups = extractQuickReplyGroups(m.content)
        if (groups.length > 0) {
          orig._quickReplies = groups[0].options.map(o => ({ label: o, value: o }))
          orig._qrMode = groups[0].mode
          orig._qrSelected = new Set()
          orig._qrDisabled = false
          m._quickReplies = orig._quickReplies
          m._qrMode = orig._qrMode
          m._qrSelected = orig._qrSelected
          m._qrDisabled = orig._qrDisabled
        }
      } else if (orig._quickReplies) {
        m._quickReplies = orig._quickReplies
        m._qrMode = orig._qrMode
        m._qrSelected = orig._qrSelected
        m._qrDisabled = orig._qrDisabled
      }
      break
    }
  }
  return msgs
})

function handleQrSelect(msg: Message, value: string) {
  // Find original message by _id (displayMessages creates shallow copies, so indexOf fails)
  const orig = msg._id ? props.messages.find(m => m._id === msg._id) : undefined
  if (orig) { orig._qrDisabled = true }
  emit('sendQuick', value)
}

function handleQrSubmit(msg: Message, value: string) {
  const orig = msg._id ? props.messages.find(m => m._id === msg._id) : undefined
  if (orig) { orig._qrDisabled = true }
  emit('sendQuick', value)
}

function focus() { chatInputRef.value?.focus() }
defineExpose({ focus })

/* ── Quick Reply extraction utilities ── */
function normalizeQuickReplyOption(raw: string): string {
  const text = String(raw || '').replace(/\*\*/g, '').replace(/`/g, '').replace(/\s+/g, ' ')
    .replace(/^\s*(?:[-*+•]\s*)?/, '')
    .replace(/^\s*(?:(?:选项|方案)\s*)?[\(（]?(?:[A-Ha-h]|[1-9][0-9]?|[一二三四五六七八九十]|[①②③④⑤⑥⑦⑧⑨⑩])[\)）.、:：]\s*/, '')
    .replace(/^[“"'']|[”"'']$/g, '').trim()
  if (!text || text.length > 90) return ''
  if (/^(问题|请问|当前|已覆盖|待挖掘|需求完整度|Sufficiency|Missing)/i.test(text)) return ''
  return text
}

function looksLikePendingQuestion(text: string): boolean {
  const tail = (text || '').slice(-1200)
  return /[?？]|请选择|选一|选择|确认|倾向|更适合|是否|要不要|还是|或者/.test(tail)
}

function isQuestionHeader(text: string): boolean {
  const v = (text || '').trim()
  return /[?？]/.test(v) || /(?:请选择|选择|确认|倾向|更适合|哪些|哪几|哪个|哪种|什么|是否|要不要|规模|人群|量级|比如|例如)/.test(v)
}

function uniqueOptions(options: string[]): string[] {
  const seen = new Set<string>(), result: string[] = []
  for (const o of options) {
    const v = normalizeQuickReplyOption(o)
    if (!v || seen.has(v)) continue
    seen.add(v); result.push(v)
    if (result.length >= 6) break
  }
  return result
}

function extractQuickReplyGroups(text: string): { question: string; options: string[]; mode: 'single' | 'multi' }[] {
  if (!looksLikePendingQuestion(text)) return []
  const plain = (text || '').replace(/```[\s\S]*?```/g, '')
  const groups: { question: string; options: string[]; mode: 'single' | 'multi' }[] = []
  const fallbackOptions: string[] = []
  let current: { question: string; options: string[]; mode: 'single' | 'multi' } | null = null
  function finishCurrent() { if (current && current.options.length) { groups.push(current) } current = null }
  for (const rawLine of plain.split('\n')) {
    const line = rawLine.trim()
    if (!line) continue
    const optionMatch = line.match(/^(?:[-*+•]\s*)?(?:(?:选项|方案)\s*)?[\(（]?([A-Ha-h]|[1-9][0-9]?|[一二三四五六七八九十]|[①②③④⑤⑥⑦⑧⑨⑩])[\)）.、:：]\s*(.+)$/)
    if (optionMatch) {
      const marker = optionMatch[1], body = optionMatch[2].trim()
      const numeric = !/^[A-Ha-h]$/.test(marker)
      if (numeric && isQuestionHeader(body) && body.length > 8) { finishCurrent(); current = { question: body, options: [], mode: inferMode(body, []) }; continue }
      if (current) current.options.push(body); else fallbackOptions.push(body)
      continue
    }
    const bullet = line.match(/^[-*+•]\s+(.+)$/)
    if (bullet) { (current || { question: '', options: fallbackOptions, mode: 'single' }).options.push(bullet[1]); continue }
    if (isQuestionHeader(line)) { finishCurrent(); current = { question: line, options: [], mode: inferMode(line, []) } }
  }
  finishCurrent()
  if (groups.length) return normalizeGroups(groups)
  let options = uniqueOptions(fallbackOptions)
  if (!options.length) options = uniqueOptions(extractInlineOptions(plain))
  if (!options.length && /是否|要不要|确认|生成\s*PRD/.test(plain)) options = ['是', '否', '请你推荐方案']
  if (!options.length) options = ['请你推荐默认方案', '暂不确定，先跳过']
  return normalizeGroups([{ question: '', options, mode: inferMode(plain, options) }])
}

function extractInlineOptions(text: string): string[] {
  const tail = (text || '').replace(/\s+/g, ' ').slice(-500)
  const pair = tail.match(/([^，。！？?；;：:]{2,24})(?:还是|或者|或)([^，。！？?；;：:]{2,24})/)
  if (!pair) return []
  return [pair[1], pair[2]].map(p => p.replace(/^.*(?:是|选择|采用|按)/, '').replace(/^(比如|例如|可以|为)/, '').replace(/(呢|吗|更合适|更适合)$/g, '').trim())
}

function inferMode(text: string, options: string[]): 'single' | 'multi' {
  const tail = (text || '').slice(-1200)
  if (/多选|可多选|选择多个|选多个|勾选|哪些|哪几/.test(tail)) return 'multi'
  if (/单选|二选一|选一个|选择一个|是否|要不要/.test(tail)) return 'single'
  if (options.length > 3 && /角色|模块|功能|端|渠道|范围|能力|场景|需求/.test(tail)) return 'multi'
  return 'single'
}

function normalizeGroups(groups: { question: string; options: string[]; mode: 'single' | 'multi' }[]) {
  return groups.map(g => ({ ...g, options: uniqueOptions(g.options) })).filter(g => g.options.length > 0)
}
</script>
