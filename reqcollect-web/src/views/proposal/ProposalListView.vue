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
          <h3 class="pl-card-title">{{ p.title || '未命名提案' }}</h3>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Plus, Search } from '@element-plus/icons-vue'
import { listProposals } from '@/api/proposal'
import type { Proposal } from '@/types'

const router = useRouter()
const route = useRoute()

const proposals = ref<Proposal[]>([])
const loading = ref(false)
const statusFilter = ref('')
const urgencyFilter = ref('')
const priorityFilter = ref('')
const searchQuery = ref('')

async function loadProposals() {
  loading.value = true
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

function statusLabel(s: string): string {
  const m: Record<string, string> = {
    pending_review: '待评审', approved: '已采纳',
    in_development: '开发中', launched: '已上线', closed: '已关闭',
  }
  return m[s] || s
}

function statusTagType(s: string): 'warning' | 'success' | 'primary' | 'info' | 'danger' {
  const m: Record<string, any> = {
    pending_review: 'warning', approved: 'success',
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
</style>
