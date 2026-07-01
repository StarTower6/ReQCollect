<template>
  <AppLayout>
    <!-- 提炼提案按钮 -->
    <div class="cv-actions" v-if="sessionStore.currentId">
      <el-button size="small" @click="showExtract = true">
        <template #icon><span style="font-size:15px">📋</span></template>
        提炼提案
      </el-button>
    </div>

    <ChatArea
      :messages="chatStore.messages"
      :streaming="chatStore.streaming"
      :mode="mode"
      :session-id="sessionStore.currentId"
      :referenced-files="referencedFiles"
      :workspace-id="sessionStore.currentWorkspaceId || null"
      @send="handleSend"
      @send-quick="handleSend"
      @toggle-mode="toggleMode"
      @file-upload="handleFileUpload"
      @reference="(fp: string) => addFileReference(fp)"
      @remove-reference="(fp: string) => removeFileReference(fp)"
    />

    <!-- 提炼提案对话框 -->
    <el-dialog v-model="showExtract" title="提炼提案" width="480px" :close-on-click-modal="false">
      <div v-if="!extracting && !extractDone" class="extract-start">
        <p style="color:var(--muted);font-size:14px;margin:0 0 16px">
          基于当前对话内容，AI 将自动提炼一份需求提案，包含业务背景、核心痛点、期望效果等信息。
        </p>
        <el-button type="primary" :loading="extracting" @click="startExtract" style="width:100%">
          开始提炼
        </el-button>
      </div>

      <div v-if="extracting || extractDone" class="extract-progress">
        <el-steps direction="vertical" :active="extractStep" space="48px" finish-status="success">
          <el-step title="分析对话内容" description="AI 正在理解对话上下文" />
          <el-step title="提炼标题与背景" description="提取项目名称和业务背景" />
          <el-step title="整理核心痛点" description="归纳用户反馈的关键问题" />
          <el-step title="提取期望效果" description="明确预期成果与范围" />
          <el-step title="评估优先级" description="分析紧急度、重要度和标签" />
        </el-steps>
        <p v-if="extracting && extractStatus" class="extract-status-text">{{ extractStatus }}</p>
        <p v-if="extractDone" class="extract-done-text">✅ 提案生成完成！</p>
      </div>

      <template #footer v-if="extractDone">
        <el-button @click="showExtract = false">关闭</el-button>
        <el-button type="primary" @click="goToProposal">查看提案</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, inject, type Ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useSessionStore } from '@/stores/session'
import { useChatStore } from '@/stores/chat'
import { useProfileStore } from '@/stores/profile'
import { readSSEStream } from '@/api/client'
import { extractProposalSSE } from '@/api/proposal'
import AppLayout from '@/components/layout/AppLayout.vue'
import ChatArea from '@/components/chat/ChatArea.vue'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const profileStore = useProfileStore()

const mode = ref<'one_shot' | 'incremental'>('one_shot')
const referencedFiles = inject<Ref<string[]>>('referencedFiles', ref([]))

/* ── 提炼提案 ── */
const showExtract = ref(false)
const extracting = ref(false)
const extractDone = ref(false)
const extractStep = ref(0)
const extractStatus = ref('')
let createdProposalId = ''

const extractFieldMap: Record<string, number> = {
  title: 1,
  background: 2,
  pain_points: 3,
  desired_outcome: 4,
  scope_note: 5,
  tags: 5,
  urgency: 5,
  priority: 5,
}

async function startExtract() {
  extracting.value = true
  extractDone.value = false
  extractStep.value = 0
  extractStatus.value = 'AI 正在分析对话...'
  createdProposalId = ''

  try {
    await extractProposalSSE(
      sessionStore.currentId!,
      sessionStore.currentWorkspaceId || '',
      (field, _content) => {
        const step = extractFieldMap[field]
        if (step != null && step > extractStep.value) {
          extractStep.value = step
        }
        const msgs: Record<string, string> = {
          title: '正在提炼标题...',
          background: '正在梳理业务背景...',
          pain_points: '正在整理核心痛点...',
          desired_outcome: '正在提取期望效果...',
          scope_note: '正在确定范围...',
          urgency: '正在评估紧急度...',
          priority: '正在评估优先级...',
        }
        if (msgs[field]) extractStatus.value = msgs[field]
      },
      (data) => {
        createdProposalId = data?.id || data?.proposal_id || ''
        extractStep.value = 5
        extractDone.value = true
        extracting.value = false
        extractStatus.value = ''
        ElMessage.success('提案生成完成')
      },
      (err) => {
        extracting.value = false
        extractDone.value = true
        extractStatus.value = ''
        ElMessage.error(err || '提炼失败，请重试')
      }
    )
  } catch (e: any) {
    extracting.value = false
    ElMessage.error(e?.message || '提炼失败，请重试')
  }
}

function goToProposal() {
  showExtract.value = false
  if (createdProposalId) {
    router.push(`/workspaces/${sessionStore.currentWorkspaceId}/proposals/${createdProposalId}`)
  }
}

/* ── 原有对话逻辑 ── */

function addFileReference(fp: string) {
  if (!referencedFiles.value.includes(fp))
    referencedFiles.value.push(fp)
}
function removeFileReference(fp: string) {
  referencedFiles.value = referencedFiles.value.filter((f: string) => f !== fp)
}

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
  setTimeout(() => {
    chatStore.loadHistory(sid)
    profileStore.load(sid)
  }, 500)
}

async function handleSend(text: string) {
  if (!sessionStore.currentId) {
    const id = sessionStore.newSession(sessionStore.currentWorkspaceId || undefined)
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
    workspace_id: sessionStore.currentWorkspaceId || '',
    referenced_files: referencedFiles.value,
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

  referencedFiles.value = []
}
</script>

<style scoped>
.cv-actions {
  padding: 8px 16px 0;
  display: flex;
  justify-content: flex-end;
}
.extract-start { padding: 8px 0; }
.extract-progress { padding: 8px 0; }
.extract-status-text {
  margin: 16px 0 0;
  font-size: 13px;
  color: var(--muted);
  text-align: center;
}
.extract-done-text {
  margin: 16px 0 0;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  color: var(--success, #36b37e);
}
</style>
