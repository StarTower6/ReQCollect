<template>
  <div class="proposal-detail" v-if="proposal">
    <!-- 顶部 -->
    <header class="pd-header">
      <div class="pd-header-left">
        <el-button text @click="goBack" class="pd-back-btn">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
      </div>
      <div class="pd-header-actions">
        <el-button size="small" @click="handleEdit">编辑</el-button>
        <el-button size="small" type="danger" plain @click="handleDelete">删除</el-button>
        <!-- 审核按钮（仅 reviewer/analyst/admin，且状态为 pending_review） -->
        <template v-if="canReview && proposal.status === 'pending_review'">
          <el-button size="small" type="success" @click="review('approve')">通过</el-button>
          <el-button size="small" type="danger" @click="review('reject')">拒绝</el-button>
        </template>
        <!-- 重新打开（状态非 pending_review 时可重新评审） -->
        <el-button v-if="canReview && proposal.status !== 'pending_review'"
                   size="small" @click="review('reopen')">重新评审</el-button>
      </div>
    </header>

    <!-- 标题 + 标签 -->
    <div class="pd-top">
      <div class="pd-top-left">
        <h1 class="pd-title">{{ proposal.title || '未命名提案' }}</h1>
        <div class="pd-tags">
          <el-tag :type="pdStatusTagType" size="small" effect="dark">
            {{ pdStatusLabel }}
          </el-tag>
          <span class="pd-priority-tag" :class="`priority-${proposal.priority?.toLowerCase()}`">
            {{ proposal.priority || '-' }}
          </span>
          <span class="pd-urgency-tag" :class="`urgency-${proposal.urgency}`">
            {{ urgencyLabel(proposal.urgency) }}
          </span>
          <el-tag v-for="t in proposal.tags" :key="t" size="small" effect="plain">
            {{ t }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 主体：左 1fr + 右 368px -->
    <div class="pd-body">
      <!-- 左侧内容 -->
      <div class="pd-main">
        <section class="pd-section">
          <h3 class="pd-section-title">业务背景</h3>
          <p class="pd-section-body">{{ proposal.background || '暂无' }}</p>
        </section>
        <section class="pd-section">
          <h3 class="pd-section-title">核心痛点</h3>
          <ul v-if="proposal.pain_points?.length" class="pd-list">
            <li v-for="(pt, i) in proposal.pain_points" :key="i">{{ pt }}</li>
          </ul>
          <p v-else class="pd-section-body muted">暂无</p>
        </section>
        <section class="pd-section">
          <h3 class="pd-section-title">期望效果</h3>
          <p class="pd-section-body">{{ proposal.desired_outcome || '暂无' }}</p>
        </section>
        <section class="pd-section">
          <h3 class="pd-section-title">范围说明</h3>
          <p class="pd-section-body">{{ proposal.scope_note || '暂无' }}</p>
        </section>
      </div>

      <!-- 右侧边栏 -->
      <aside class="pd-sidebar">
        <div class="pd-card">
          <h4 class="pd-card-title">基本信息</h4>
          <dl class="pd-info-list">
            <dt>提出人</dt>
            <dd>{{ proposal.submitter_id?.slice(0, 12) || '-' }}</dd>
            <dt>来源会话</dt>
            <dd>{{ proposal.source_session_id?.slice(0, 12) || '-' }}</dd>
            <dt>创建时间</dt>
            <dd>{{ formatDate(proposal.created_at) }}</dd>
            <dt>更新时间</dt>
            <dd>{{ formatDate(proposal.updated_at) }}</dd>
          </dl>
        </div>

        <div class="pd-card">
          <h4 class="pd-card-title">AI 评估</h4>
          <div v-if="proposal.ai_assessment" class="pd-ai-content">
            {{ proposal.ai_assessment }}
          </div>
          <p v-else class="pd-section-body muted">暂无 AI 评估</p>
        </div>
      </aside>
    </div>
  </div>

  <!-- 加载态 -->
  <div v-else-if="loading" class="pd-loading">
    <el-skeleton :rows="5" animated />
  </div>

  <!-- 404 -->
  <div v-else class="pd-empty">
    <el-empty description="提案不存在" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { apiPost } from '@/api/client'
import { getProposal, deleteProposal } from '@/api/proposal'
import { useAuthStore } from '@/stores/auth'
import type { Proposal } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const proposal = ref<Proposal | null>(null)
const loading = ref(false)

const wid = computed(() => route.params.id as string)
const pid = computed(() => route.params.pid as string)

const canReview = computed(() => ['reviewer', 'analyst', 'admin'].includes(authStore.user?.role || ''))
const canGeneratePrd = computed(() => ['analyst', 'admin'].includes(authStore.user?.role || ''))

const pdStatusLabel = computed(() => {
  const m: Record<string, string> = {
    pending_review: '待评审', approved: '已采纳', rejected: '已拒绝',
    in_development: '开发中', launched: '已上线', closed: '已关闭',
  }
  return m[proposal.value?.status || ''] || proposal.value?.status || ''
})

const pdStatusTagType = computed(() => {
  const m: Record<string, any> = {
    pending_review: 'warning', approved: 'success', rejected: 'danger',
    in_development: 'primary', launched: '', closed: 'info',
  }
  return m[proposal.value?.status || ''] || 'info'
})

function urgencyLabel(u: string): string {
  return { high: '紧急', medium: '中等', low: '低' }[u] || u
}

function formatDate(d: string): string {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}

function goBack() {
  router.push(`/workspaces/${wid.value}/proposals`)
}

async function loadProposal() {
  loading.value = true
  try {
    proposal.value = await getProposal(wid.value, pid.value)
  } catch {
    proposal.value = null
  } finally {
    loading.value = false
  }
}

async function review(action: 'approve' | 'reject' | 'reopen') {
  const comment = action === 'approve' ? '审核通过'
    : action === 'reject' ? '需求不清晰，需补充' : ''
  try {
    await apiPost(`/workspaces/${wid.value}/proposals/${pid.value}/review`, { action, comment })
    ElMessage.success('审核操作完成')
    await loadProposal()
  } catch (e: any) {
    ElMessage.error(e.message || '审核失败')
  }
}

function handleEdit() {
  // TODO: 编辑弹窗
}

async function handleDelete() {
  // TODO: 确认弹窗
}

onMounted(loadProposal)
</script>

<style scoped>
.proposal-detail {
  padding: 20px 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ── Header ── */
.pd-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.pd-header-left { display: flex; align-items: center; gap: 8px; }
.pd-back-btn { font-size: 13px; }

/* ── Top ── */
.pd-top { margin-bottom: 20px; }
.pd-top-left { display: flex; flex-direction: column; gap: 8px; }
.pd-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
  color: var(--text);
}
.pd-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.pd-priority-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 4px;
}
.priority-p0 { background: var(--danger-soft); color: var(--priority-p0); }
.priority-p1 { background: var(--warning-soft); color: var(--priority-p1); }
.priority-p2 { background: var(--brand-soft); color: var(--priority-p2); }
.priority-p3 { background: var(--sidebar); color: var(--priority-p3); }
.pd-urgency-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.urgency-high { background: var(--danger-soft); color: var(--urgency-high); }
.urgency-medium { background: var(--warning-soft); color: var(--urgency-medium); }
.urgency-low { background: var(--success-soft); color: var(--urgency-low); }

/* ── Body ── */
.pd-body {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 368px;
  gap: 20px;
  overflow: hidden;
}

/* ── Main (left) ── */
.pd-main {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pd-section {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px;
}
.pd-section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--text);
}
.pd-section-body {
  font-size: 13px;
  color: var(--text);
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
}
.pd-section-body.muted { color: var(--muted); }
.pd-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text);
}

/* ── Sidebar (right) ── */
.pd-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}
.pd-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px;
}
.pd-card-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--text);
}
.pd-info-list {
  margin: 0;
  font-size: 13px;
}
.pd-info-list dt {
  color: var(--muted);
  margin-bottom: 2px;
  font-weight: 500;
}
.pd-info-list dd {
  margin: 0 0 10px;
  color: var(--text);
}
.pd-ai-content {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
  white-space: pre-wrap;
}

/* ── Loading / Empty ── */
.pd-loading { padding: 40px 24px; }
.pd-empty { flex: 1; display: flex; align-items: center; justify-content: center; }
</style>
