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
      <div v-else-if="page" class="wiki-content" @click="onContentClick">
        <h1 class="wiki-title">{{ page.title }}</h1>
        <div class="wiki-meta">
          <span>创建于: {{ formatDate(page.created_at) }}</span>
          <span v-if="page.created_by_name"> · 创建者: {{ page.created_by_name }}</span>
        </div>
        <div class="wiki-meta" v-if="page.updated_at">
          <span>最后更新: {{ formatDate(page.updated_at) }}</span>
          <span v-if="page.updated_by_name"> · 编辑者: {{ page.updated_by_name }}</span>
        </div>
        <el-divider />
        <div class="wiki-body markdown-body" v-html="renderedContent" />

        <!-- Backlinks section -->
        <div v-if="backlinks.length > 0" class="backlinks-section">
          <el-divider />
          <h3 class="backlinks-title">被以下页面引用</h3>
          <div class="backlinks-list">
            <div
              v-for="bl in backlinks"
              :key="bl.id"
              class="backlink-item"
              @click="goToPage(bl.id)"
            >
              <span class="backlink-icon">📄</span>
              <span class="backlink-title">{{ bl.title }}</span>
            </div>
          </div>
        </div>
      </div>

      <el-empty v-else description="页面不存在" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import hljs from 'highlight.js'
import mermaid from 'mermaid'
import { fetchWikiPageDetail, fetchWikiPages, deleteWikiPage } from '@/api/wiki'
import type { WikiPage, BacklinkRef } from '@/api/wiki'
import AppLayout from '@/components/layout/AppLayout.vue'

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'inherit',
})

const route = useRoute()
const router = useRouter()
const page = ref<WikiPage | null>(null)
const backlinks = ref<BacklinkRef[]>([])
const loading = ref(true)
const error = ref('')

// Map of page title -> page id for resolving [[wikilinks]]
const allPageTitles = ref<Record<string, string>>({})

// Regex to match [[Title]] and [[Title|alias]]
const WIKILINK_REGEX = /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g

const renderedContent = computed(() => {
  if (!page.value) return ''
  try {
    let html = marked.parse(page.value.content || '', { async: false }) as string
    if (typeof html === 'object') {
      nextTick(async () => {
        const h = await marked.parse(page.value?.content || '')
        const el = document.querySelector('.wiki-body')
        if (el) {
          el.innerHTML = renderWikilinks(h)
        }
        await afterRender()
      })
      return '加载中...'
    }
    html = renderWikilinks(html)
    nextTick(() => afterRender())
    return html
  } catch {
    return page.value?.content || ''
  }
})

function renderWikilinks(html: string): string {
  const wsId = route.params.id as string
  return html.replace(WIKILINK_REGEX, (_match: string, title: string, alias?: string) => {
    const text = alias || title
    const pageId = allPageTitles.value[title]
    if (pageId) {
      return `<a href="#/workspaces/${wsId}/wiki/${pageId}" class="wiki-link">${text}</a>`
    } else {
      return `<span class="wiki-link-missing">${text}</span>`
    }
  })
}

async function afterRender() {
  // 1. Highlight.js — 所有代码块
  document.querySelectorAll('.wiki-body pre code:not(.hljs)').forEach(block => {
    const el = block as HTMLElement
    if (el.className.includes('language-mermaid')) return
    try { hljs.highlightElement(el) } catch { /* ignore */ }
  })

  // 2. Mermaid — 所有 mermaid 代码块
  const mermaidBlocks = document.querySelectorAll('.wiki-body pre code.language-mermaid')
  if (mermaidBlocks.length > 0) {
    mermaidBlocks.forEach((block, i) => {
      const pre = block.parentElement
      const text = block.textContent || ''
      if (!pre) return
      const div = document.createElement('div')
      div.className = 'mermaid'
      div.id = `mermaid-${Date.now()}-${i}`
      div.textContent = text
      pre.replaceWith(div)
    })
    try {
      await mermaid.run({ querySelector: '.mermaid' })
    } catch { /* some diagrams may fail, skip */ }
  }
}

function formatDate(d: string) {
  if (!d) return ''
  try { return new Date(d).toLocaleString('zh-CN') } catch { return '' }
}

function goBack() {
  const wsId = route.params.id
  router.push(`/workspaces/${wsId}`)
}

function goEdit() {
  router.push(`/workspaces/${route.params.id}/wiki/${route.params.pageId}/edit`)
}

function goToPage(pageId: string) {
  router.push(`/workspaces/${route.params.id}/wiki/${pageId}`)
}

function onContentClick(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('a.wiki-link') as HTMLElement
  if (target && target.getAttribute('href')) {
    e.preventDefault()
    const href = target.getAttribute('href')!
    router.push(href.replace(/^#/, ''))
  }
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
    const wsId = route.params.id as string
    const [detail, pages] = await Promise.all([
      fetchWikiPageDetail(route.params.pageId as string),
      fetchWikiPages(wsId),
    ])
    page.value = detail.page
    backlinks.value = detail.backlinks
    // Build title→id map for wikilink resolution
    for (const p of pages) {
      allPageTitles.value[p.title] = p.id
    }
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
  overflow-y: auto;
  height: 100%;
  box-sizing: border-box;
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
  color: var(--text);
  margin: 0 0 8px;
}

.wiki-meta {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.6;
}

.wiki-body {
  line-height: 1.8;
  font-size: 15px;
  color: var(--text);
}

.wiki-body :deep(.wiki-link) {
  color: var(--brand);
  text-decoration: underline;
  cursor: pointer;
}

.wiki-body :deep(.wiki-link-missing) {
  color: var(--muted-light);
  border-bottom: 1px dashed var(--line);
  cursor: default;
}

/* Table styling for markdown */
.wiki-body :deep(table) {
  display: table;
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  overflow: auto;
  margin: 12px 0;
}
.wiki-body :deep(table th) {
  font-weight: 600;
  background: var(--sidebar);
  border: 1px solid var(--line);
  padding: 8px 12px;
  text-align: left;
}
.wiki-body :deep(table td) {
  border: 1px solid var(--line);
  padding: 8px 12px;
}
.wiki-body :deep(table tr:nth-child(2n)) {
  background: var(--sidebar);
}

/* Backlinks */
.backlinks-section {
  margin-top: 8px;
}

.backlinks-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--muted);
  margin: 0 0 12px;
}

.backlinks-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.backlink-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.12s;
}

.backlink-item:hover {
  background: var(--sidebar-hover);
}

.backlink-icon {
  font-size: 14px;
}

.backlink-title {
  color: var(--brand);
  font-weight: 500;
}
</style>
