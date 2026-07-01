<template>
  <AppLayout>
    <div class="prd-list-page">
      <div class="page-header">
        <el-button text size="small" @click="goBack">← 工作空间</el-button>
        <h2>PRD 文档</h2>
      </div>
      <div v-if="loading" v-loading="true" style="height:200px" />
      <div v-else>
        <div class="section-actions">
          <span class="section-count">共 {{ prds.length }} 个 PRD</span>
        </div>
        <div v-if="prds.length === 0" class="empty-state">暂无 PRD 文档</div>
        <div v-else class="prd-grid">
          <div
            v-for="prd in prds"
            :key="prd.id"
            class="prd-card"
            @click="goPrd(prd.id)"
          >
            <h3>{{ prd.project_name || '未命名 PRD' }}</h3>
            <div class="prd-meta">
              <el-tag size="small" type="info">{{ prd.mode === 'one_shot' ? '一次性生成' : '逐章生成' }}</el-tag>
              <span v-if="prd.source_proposal_ids?.length" class="source-tag">从提案池</span>
              <span v-else class="source-tag">从会话</span>
            </div>
            <div class="prd-time">{{ formatDate(prd.created_at) }}</div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiGet } from '@/api/client'
import AppLayout from '@/components/layout/AppLayout.vue'

const route = useRoute()
const router = useRouter()
const prds = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  const wsId = route.params.id as string
  try {
    const data = await apiGet<{ prds: any[] }>(`/workspaces/${wsId}/prds`)
    prds.value = data.prds || []
  } catch { /* */ }
  loading.value = false
})

function goBack() { router.push(`/workspaces/${route.params.id}`) }
function goPrd(prdId: string) { router.push(`/prd/${prdId}`) }
function formatDate(d: string) {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.prd-list-page { padding: 20px; max-width: 960px; margin: 0 auto; }
.page-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; color: var(--text); }
.section-actions { margin-bottom: 16px; }
.section-count { font-size: 14px; color: var(--muted); }
.empty-state { text-align: center; padding: 60px 0; color: var(--muted); font-size: 15px; }
.prd-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.prd-card {
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  padding: 16px; cursor: pointer; transition: box-shadow 0.2s;
}
.prd-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
.prd-card h3 { margin: 0 0 8px; font-size: 16px; color: var(--text); }
.prd-meta { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.source-tag { font-size: 12px; color: var(--brand); background: color-mix(in srgb, var(--brand) 10%, transparent); padding: 2px 8px; border-radius: 4px; }
.prd-time { font-size: 12px; color: var(--muted); }
</style>
