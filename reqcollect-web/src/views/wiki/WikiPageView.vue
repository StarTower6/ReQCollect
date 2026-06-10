<template>
  <AppLayout>
    <div class="wiki-view-page">
      <!-- Top bar -->
      <div class="wiki-topbar">
        <el-button text size="small" @click="goBack">← 返回文库</el-button>
        <div class="wiki-topbar-right">
          <el-button size="small" @click="goEdit" v-if="page">编辑</el-button>
          <el-popconfirm
            v-if="page"
            title="确定删除此页面？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            @confirm="handleDelete"
          >
            <template #reference>
              <el-button size="small" type="danger" text>删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" v-loading="loading" style="height:200px" />

      <!-- Error -->
      <el-result v-else-if="error" icon="error" :title="error" />

      <!-- Content -->
      <div v-else-if="page" class="wiki-content">
        <h1 class="wiki-title">{{ page.title }}</h1>
        <div class="wiki-meta">
          <span>最后更新: {{ formatDate(page.updated_at) }}</span>
          <span v-if="page.updated_by"> · 编辑者: {{ page.updated_by }}</span>
        </div>
        <el-divider />
        <div class="wiki-body markdown-body" v-html="renderedContent" />
      </div>

      <el-empty v-else description="页面不存在" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { fetchWikiPage, deleteWikiPage } from '@/api/wiki'
import type { WikiPage } from '@/api/wiki'
import AppLayout from '@/components/layout/AppLayout.vue'

const route = useRoute()
const router = useRouter()
const page = ref<WikiPage | null>(null)
const loading = ref(true)
const error = ref('')

const renderedContent = computed(() => {
  if (!page.value) return ''
  try {
    return marked(page.value.content || '')
  } catch {
    return page.value.content || ''
  }
})

function formatDate(d: string) {
  if (!d) return ''
  try { return new Date(d).toLocaleString('zh-CN') } catch { return '' }
}

function goBack() {
  const wsId = route.params.id
  router.push(`/workspace/${wsId}`)
}

function goEdit() {
  const wsId = route.params.id
  const pageId = route.params.pageId
  router.push(`/workspace/${wsId}/wiki/${pageId}/edit`)
}

async function handleDelete() {
  try {
    await deleteWikiPage(route.params.pageId as string)
    ElMessage.success('已删除')
    goBack()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    page.value = await fetchWikiPage(route.params.pageId as string)
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.wiki-view-page {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.wiki-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.wiki-topbar-right {
  display: flex;
  gap: 8px;
}

.wiki-title {
  font-size: 28px;
  font-weight: 700;
  color: #1d2129;
  margin: 0 0 8px;
}

.wiki-meta {
  font-size: 13px;
  color: #86909c;
}

.wiki-body {
  line-height: 1.8;
  font-size: 15px;
  color: #1d2129;
}
</style>
