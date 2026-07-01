<template>
  <div class="proposal-list">
    <!-- 顶部 -->
    <header class="pl-header">
      <div class="pl-header-left">
        <el-button text @click="goBack" class="pl-back-btn">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2 class="pl-title">需求池</h2>
      </div>
      <el-button type="primary" @click="handleNew">
        <el-icon><Plus /></el-icon>
        新建提案
      </el-button>
    </header>

    <!-- 筛选区 -->
    <section class="pl-filters">
      <el-tabs v-model="statusFilter" class="pl-status-tabs" @tab-change="loadProposals">
        <el-tab-pane label="全部" name="" />
        <el-tab-pane label="待评审" name="pending_review" />
        <el-tab-pane label="已采纳" name="approved" />
        <el-tab-pane label="已拒绝" name="rejected" />
        <el-tab-pane label="开发中" name="in_development" />
        <el-tab-pane label="已上线" name="launched" />
        <el-tab-pane label="已关闭" name="closed" />
      </el-tabs>

      <div class="pl-filter-actions">
        <el-select v-model="urgencyFilter" placeholder="紧急度" clearable size="small" style="width:120px" @change="loadProposals">
          <el-option label="紧急" value="high" />
          <el-option label="中等" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
        <el-select v-model="priorityFilter" placeholder="优先级" clearable size="small" style="width:120px" @change="loadProposals">
          <el-option label="P0" value="P0" />
          <el-option label="P1" value="P1" />
          <el-option label="P2" value="P2" />
          <el-option label="P3" value="P3" />
        </el-select>
        <el-input v-model="searchQuery" placeholder="搜索提案标题…" clearable size="small" style="width:200px" @clear="loadProposals" @keyup.enter="loadProposals">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
    </section>

    <!-- 批量操作栏（有选中时显示） -->
    <div v-if="canGeneratePrd && selectedIds.length > 0" class="pl-bulk-bar">
      <el-checkbox :indeterminate="isIndeterminate" v-model="selectAll" @change="toggleAll" style="margin-right:12px">
        全选
      </el-checkbox>
      <span class="pl-bulk-info">已选 {{ selectedIds.length }} 个提案</span>
      <el-button type="primary" size="small" :disabled="!allApproved" @click="generatePrd">
        选入 PRD
      </el-button>
      <el-tag v-if="!allApproved" size="small" type="warning" effect="plain">
        仅已采纳的提案可生成 PRD
      </el-tag>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="pl-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- 空态 -->
    <div v-else-if="proposals.length === 0" class="pl-empty">
      <el-empty description="暂无提案" />
    </div>

    <!-- 卡片列表 -->
    <section v-else class="pl-cards">
      <article
        v-for="p in proposals"
        :key="p.id || p.proposal_id"
        class="pl-card"
        @click="goDetail(p.id || p.proposal_id)"
      >
        <div class="pl-card-top">
          <div class="pl-card-title-row">
            <!-- 选入 PRD 多选（仅 analyst/admin 可见） — wrapper 阻止冒泡到卡片点击 -->
            <span v-if="canGeneratePrd" class="pl-card-check-wrap" @click.stop>
              <el-checkbox
                v-model="selectedIds"
                :value="p.id || p.proposal_id"
                class="pl-card-check"
              />
            </span>
            <h3 class="pl-card-title">{{ p.title || '未命名提案' }}</h3>
          </div>
          <div class="pl-card-tags">
            <el-tag :type="statusTagType(p.status)" size="small" effect="plain">
              {{ statusLabel(p.status) }}
            </el-tag>
            <span class="pl-priority-tag" :class="`priority-${p.priority?.toLowerCase()}`">
              {{ p.priority || '-' }}
            </span>
            <span class="pl-urgency-tag" :class="`urgency-${p.urgency}`">
              {{ urgencyLabel(p.urgency) }}
            </span>
          </div>
        </div>
        <p class="pl-card-desc">{{ p.background?.slice(0, 120) }}{{ p.background?.length > 120 ? '…' : '' }}</p>
        <div class="pl-card-meta">
          <span>提出人: {{ p.submitter_id?.slice(0, 8) || '-' }}</span>
          <span>{{ formatDate(p.created_at) }}</span>
        </div>
      </article>
    </section>

    <!-- PRD 生成进度对话框（双栏：思考过程 + 实时预览） -->
    <el-dialog v-model="showPrdDialog" title="生成 PRD" width="900px" :close-on-click-modal="false" :close-on-press-escape="false">
      <div class="prd-gen-content">
        <div v-if="prdGenerating || prdProgress.includes('完成')" class="prd-gen-progress">
          <el-progress :percentage="prdSectionTotal > 0 ? Math.round(prdSectionIndex / prdSectionTotal * 100) : 0" :stroke-width="8" />
          <p class="prd-gen-status">{{ prdProgress }}</p>
          <div v-if="prdSection" class="prd-gen-section">
            <span class="prd-gen-section-label">当前章节:</span>
            <span class="prd-gen-section-title">{{ prdSection }}</span>
          </div>
        </div>
        <div v-if="prdProgress.includes('完成')" class="prd-gen-done">
          <el-result icon="success" title="PRD 生成完成" sub-title="点击下方按钮查看生成的 PRD 文档" />
        </div>
        <div v-else-if="!prdGenerating && !prdProgress.includes('完成')" class="prd-gen-error">
          <el-result icon="error" title="生成失败" :sub-title="prdProgress || '请重试'" />
        </div>
        <!-- 双栏：思考 + 实时预览 -->
        <div class="prd-gen-body" v-if="prdGenerating || previewMarkdown">
          <div class="prd-gen-left">
            <div class="prd-gen-thoughts-title">💭 思考过程</div>
            <div class="prd-gen-thoughts">
              <div v-for="(t, i) in thoughts" :key="i" class="thought-item">{{ t }}</div>
            </div>
          </div>
          <div class="prd-gen-right">
            <div class="prd-gen-preview-title">📄 实时预览</div>
            <div class="prd-gen-preview" v-html="renderedPreview"></div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button v-if="!prdGenerating" @click="showPrdDialog = false">关闭</el-button>
        <el-button v-if="createdPrdId" type="primary" @click="goToPrd">查看 PRD</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Plus, Search } from '@element-plus/icons-vue'
import { listProposals } from '@/api/proposal'
import { generatePrdFromProposalsSSE } from '@/api/proposal'
import { useAuthStore } from '@/stores/auth'
import { marked } from 'marked'
import type { Proposal } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const proposals = ref<Proposal[]>([])
const loading = ref(false)
const statusFilter = ref('')
const urgencyFilter = ref('')
const priorityFilter = ref('')
const searchQuery = ref('')
const selectedIds = ref<string[]>([])
const selectAll = ref(false)

const canGeneratePrd = computed(() => ['analyst', 'admin'].includes(authStore.user?.role || ''))

const isIndeterminate = computed(() =>
  selectedIds.value.length > 0 && selectedIds.value.length < proposals.value.length
)

const allApproved = computed(() =>
  selectedIds.value.length > 0 &&
  selectedIds.value.every(id =>
    proposals.value.find(p => (p.id || p.proposal_id) === id)?.status === 'approved'
  )
)

const showPrdDialog = ref(false)
const prdGenerating = ref(false)
const prdProgress = ref('')
const prdSection = ref('')
const prdSectionTotal = ref(0)
const prdSectionIndex = ref(0)
let createdPrdId = ''
const thoughts = ref<string[]>([])
const previewMarkdown = ref('')
const renderedPreview = ref('')

function toggleAll(checked: boolean) {
  selectedIds.value = checked ? proposals.value.map(p => p.id || p.proposal_id) : []
}

async function loadProposals() {
  loading.value = true
  selectedIds.value = []
  selectAll.value = false
  try {
    const wid = route.params.id as string
    const res = await listProposals(wid, {
      status: statusFilter.value || undefined,
      urgency: urgencyFilter.value || undefined,
      priority: priorityFilter.value || undefined,
      limit: 50,
    })
    proposals.value = res.proposals || []
  } catch {
    proposals.value = []
  } finally {
    loading.value = false
  }
}

function goBack() {
  const wid = route.params.id as string
  router.push(`/workspaces/${wid}`)
}

function goDetail(pid: string) {
  const wid = route.params.id as string
  router.push(`/workspaces/${wid}/proposals/${pid}`)
}

function handleNew() {
  // TODO: 新建提案弹窗/页面
}

async function generatePrd() {
  const wid = route.params.id as string
  showPrdDialog.value = true
  prdGenerating.value = true
  prdProgress.value = '正在准备 PRD 生成...'
  prdSection.value = ''
  prdSectionTotal.value = 0
  prdSectionIndex.value = 0
  createdPrdId = ''
  thoughts.value = []
  previewMarkdown.value = ''
  renderedPreview.value = ''

  await generatePrdFromProposalsSSE(
    wid,
    selectedIds.value,
    (msg) => { prdProgress.value = msg },
    (title, index, total) => {
      prdSection.value = title
      prdSectionIndex.value = index
      prdSectionTotal.value = total
      prdProgress.value = `正在撰写第 ${index}/${total} 章: ${title}`
    },
    (data) => {
      createdPrdId = data?.prd_id || data?.id || ''
      prdGenerating.value = false
      prdProgress.value = '✅ PRD 生成完成！'
      ElMessage.success('PRD 生成完成')
    },
    (err) => {
      prdGenerating.value = false
      prdProgress.value = ''
      ElMessage.error(err || 'PRD 生成失败')
    },
    (thoughtText) => {  // onThought
      if (thoughtText) thoughts.value.push(thoughtText)
    },
    (content) => {  // onSectionContent
      previewMarkdown.value += content
      const html = marked.parse(previewMarkdown.value, { async: false }) as string
      if (typeof html === 'string') renderedPreview.value = html
    },
  )
}

function goToPrd() {
  showPrdDialog.value = false
  if (createdPrdId) {
    router.push(`/prd/${createdPrdId}`)
  }
}

function statusLabel(s: string): string {
  const m: Record<string, string> = {
    pending_review: '待评审', approved: '已采纳', rejected: '已拒绝',
    in_development: '开发中', launched: '已上线', closed: '已关闭',
  }
  return m[s] || s
}

function statusTagType(s: string): 'warning' | 'success' | 'primary' | 'info' | 'danger' {
  const m: Record<string, any> = {
    pending_review: 'warning', approved: 'success', rejected: 'danger',
    in_development: 'primary', launched: '', closed: 'info',
  }
  return m[s] || 'info'
}

function urgencyLabel(u: string): string {
  return { high: '紧急', medium: '中等', low: '低' }[u] || u
}

function formatDate(d: string): string {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('zh-CN')
}

onMounted(loadProposals)
</script>

<style scoped>
.proposal-list {
  padding: 20px 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ── Header ── */
.pl-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.pl-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pl-back-btn { font-size: 13px; }
.pl-title { font-size: 20px; font-weight: 600; margin: 0; color: var(--text); }

/* ── Filters ── */
.pl-filters {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.pl-status-tabs { flex: 1; min-width: 0; }
.pl-filter-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* ── Bulk bar ── */
.pl-bulk-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--brand-soft);
  border: 1px solid var(--brand);
  border-radius: var(--radius);
  margin-bottom: 12px;
}
.pl-bulk-info {
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
}

/* ── Loading ── */
.pl-loading { padding: 24px; }

/* ── Empty ── */
.pl-empty { flex: 1; display: flex; align-items: center; justify-content: center; }

/* ── Cards ── */
.pl-cards {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pl-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.pl-card:hover {
  border-color: var(--brand);
  box-shadow: var(--shadow);
}
.pl-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.pl-card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}
.pl-card-check { flex-shrink: 0; }
.pl-card-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  color: var(--text);
  line-height: 1.4;
}
.pl-card-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.pl-priority-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 4px;
}
.priority-p0 { background: var(--danger-soft); color: var(--priority-p0); }
.priority-p1 { background: var(--warning-soft); color: var(--priority-p1); }
.priority-p2 { background: var(--brand-soft); color: var(--priority-p2); }
.priority-p3 { background: var(--sidebar); color: var(--priority-p3); }
.pl-urgency-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.urgency-high { background: var(--danger-soft); color: var(--urgency-high); }
.urgency-medium { background: var(--warning-soft); color: var(--urgency-medium); }
.urgency-low { background: var(--success-soft); color: var(--urgency-low); }

.pl-card-desc {
  font-size: 13px;
  color: var(--muted);
  margin: 0 0 8px;
  line-height: 1.5;
}
.pl-card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--muted-light);
}

/* ── PRD 生成对话框 ── */
.prd-gen-content { min-height: 120px; display: flex; align-items: center; justify-content: center; }
.prd-gen-progress { width: 100%; padding: 16px 0; }
.prd-gen-status { text-align: center; font-size: 14px; color: var(--text); margin: 16px 0 8px; }
.prd-gen-section { text-align: center; font-size: 13px; color: var(--muted); }
.prd-gen-section-label { margin-right: 4px; }
.prd-gen-section-title { font-weight: 500; color: var(--brand); }
.prd-gen-done, .prd-gen-error { width: 100%; }

.prd-gen-dialog { display: flex; gap: 16px; min-height: 400px; }
.prd-gen-body { display: flex; gap: 16px; margin-top: 16px; min-height: 300px; }
.prd-gen-left { flex: 0 0 280px; display: flex; flex-direction: column; gap: 8px; }
.prd-gen-right { flex: 1; border: 1px solid var(--line); border-radius: 8px; padding: 16px; overflow-y: auto; max-height: 60vh; background: var(--bg); }
.prd-gen-thoughts-title { font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 4px; }
.prd-gen-preview-title { font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 12px; }
.prd-gen-thoughts { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.thought-item { font-size: 12px; color: var(--brand); padding: 6px 8px; background: var(--brand-soft); border-radius: 6px; line-height: 1.5; }
.prd-gen-preview { font-size: 13px; line-height: 1.7; color: var(--text); }
.prd-gen-preview :deep(h1), .prd-gen-preview :deep(h2) { margin: 12px 0 8px; }
.prd-gen-preview :deep(h2) { font-size: 16px; border-bottom: 1px solid var(--line); padding-bottom: 4px; }
.prd-gen-preview :deep(p) { margin: 6px 0; }
.prd-gen-preview :deep(ul), .prd-gen-preview :deep(ol) { padding-left: 20px; }
.prd-gen-status { font-size: 14px; color: var(--text); margin: 0; }
.prd-gen-empty { text-align: center; color: var(--muted); padding-top: 40px; }

</style>
