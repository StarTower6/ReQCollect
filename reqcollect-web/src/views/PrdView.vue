<template>
  <div class="prd-view">
    <div class="prd-actions" v-if="prdStore.prd">
      <template v-if="!editing">
        <el-button size="small" @click="startEdit">✏️ 编辑</el-button>
        <el-button size="small" :loading="wikiLoading" @click="showWikiDialog = true">📄 加入 Wiki</el-button>
      </template>
      <template v-else>
        <el-button size="small" @click="cancelEdit">取消</el-button>
        <el-button size="small" type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </div>
    <PrdToc
      v-if="prdStore.prd && !editing"
      :sections="sections"
      :active-index="activeIndex"
      @scroll-to="scrollToSection"
      @download="downloadMarkdown"
    />
    <div class="prd-content-wrap" ref="contentRef">
      <div v-if="!prdStore.prd" style="padding:40px;text-align:center;color:var(--muted)">正在加载 PRD...</div>
      <!-- 查看模式 -->
      <div v-else-if="!editing" ref="prdContentRef" class="prd-content" v-html="renderedMarkdown"></div>
      <!-- 编辑模式：左编辑器 + 右预览 -->
      <div v-else class="prd-edit-dual">
        <div class="prd-edit-left">
          <textarea v-model="editMarkdown" class="prd-edit-textarea" placeholder="在此编辑 Markdown..."></textarea>
        </div>
        <div class="prd-edit-right">
          <div class="prd-content" v-html="editRenderedPreview"></div>
        </div>
      </div>
    </div>

    <!-- Wiki dialog -->
    <el-dialog v-model="showWikiDialog" title="加入 Wiki" width="460px">
      <el-form :model="wikiForm" label-width="80px">
        <el-form-item label="页面标题">
          <el-input v-model="wikiForm.title" placeholder="Wiki 页面标题" />
        </el-form-item>
        <el-form-item label="工作空间">
          <el-select v-model="wikiForm.workspaceId" placeholder="选择目标工作空间" style="width:100%" filterable>
            <el-option v-for="ws in workspaces" :key="ws.id" :label="ws.name" :value="ws.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showWikiDialog = false">取消</el-button>
        <el-button type="primary" :loading="wikiLoading" @click="handleWikiCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePrdStore } from '@/stores/prd'
import { marked } from 'marked'
import hljs from 'highlight.js'
import mermaid from 'mermaid'
import PrdToc from '@/components/prd/PrdToc.vue'
import { aiCreateWikiFromPrd } from '@/api/wiki'
import { fetchWorkspaces } from '@/api/workspace'
import { updatePrd } from '@/api/prd'

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'inherit',
})

const route = useRoute()
const router = useRouter()
const prdStore = usePrdStore()

// Wiki dialog
const showWikiDialog = ref(false)
const wikiLoading = ref(false)
const workspaces = ref<any[]>([])
const wikiForm = ref({ title: '', workspaceId: '' })

async function handleWikiCreate() {
  if (!wikiForm.value.title.trim()) {
    ElMessage.warning('请输入页面标题')
    return
  }
  if (!wikiForm.value.workspaceId) {
    ElMessage.warning('请选择工作空间')
    return
  }
  wikiLoading.value = true
  try {
    const page = await aiCreateWikiFromPrd({
      workspace_id: wikiForm.value.workspaceId,
      title: wikiForm.value.title.trim(),
      prd_markdown: prdStore.prd?.markdown || '',
    })
    ElMessage.success('Wiki 页面创建成功')
    showWikiDialog.value = false
    router.push(`/workspaces/${wikiForm.value.workspaceId}/wiki/${page.id}`)
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    wikiLoading.value = false
  }
}

watch(showWikiDialog, async (val) => {
  if (val) {
    try {
      workspaces.value = await fetchWorkspaces()
    } catch { /* silent */ }
  }
})
const contentRef = ref<HTMLElement | null>(null)
const prdContentRef = ref<HTMLElement | null>(null)
const activeIndex = ref(0)

const sections = computed(() => {
  if (!prdStore.prd?.markdown) return []
  const lines = prdStore.prd.markdown.split('\n')
  const result: { title: string; id: string }[] = []
  for (const line of lines) {
    if (line.startsWith('## ')) {
      const title = line.replace(/^##\s+/, '')
      const id = title.toLowerCase().replace(/[^\w一-鿿]+/g, '-').replace(/^-+|-+$/g, '')
      result.push({ title, id })
    }
  }
  return result
})

const renderedMarkdown = computed(() => {
  if (!prdStore.prd?.markdown) return ''
  const html = marked.parse(prdStore.prd.markdown, { async: false }) as string
  // marked v12+: when async=false returns a string; sync parse is used
  // (string is returned synchronously with async:false since marked v5)
  if (typeof html !== 'string') {
    return '加载中...'
  }
  nextTick(() => afterRender())
  return html
})

async function afterRender() {
  // 1. Highlight.js — 所有代码块
  document.querySelectorAll('.prd-content pre code:not(.hljs)').forEach(block => {
    const el = block as HTMLElement
    // Skip mermaid blocks — they're rendered by mermaid
    if (el.className.includes('language-mermaid')) return
    try { hljs.highlightElement(el) } catch { /* ignore */ }
  })

  // 2. Mermaid — 所有 mermaid 代码块
  const mermaidBlocks = document.querySelectorAll('.prd-content pre code.language-mermaid')
  if (mermaidBlocks.length > 0) {
    // Replace <pre><code class="language-mermaid">...</code></pre>
    // with <div class="mermaid">...</div> for mermaid rendering
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

function scrollToSection(index: number) {
  activeIndex.value = index
  const sec = sections.value?.[index]
  if (!sec) return
  const el = document.getElementById(sec.id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  } else {
    const allHeadings = document.querySelectorAll('.prd-content h2, .prd-content h3')
    if (allHeadings[index]) allHeadings[index].scrollIntoView({ behavior: 'smooth' })
  }
}

function downloadMarkdown() {
  if (!prdStore.prd?.markdown) return
  const blob = new Blob([prdStore.prd.markdown], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `PRD-${prdStore.prd.session_id || 'export'}.md`
  a.click()
  URL.revokeObjectURL(url)
}

/* ── 编辑模式 ── */
const editing = ref(false)
const saving = ref(false)
const editMarkdown = ref('')
const editRenderedPreview = computed(() => {
  if (!editMarkdown.value) return ''
  const html = marked.parse(editMarkdown.value, { async: false }) as string
  return typeof html === 'string' ? html : ''
})

function startEdit() {
  editing.value = true
  editMarkdown.value = prdStore.prd?.markdown || ''
}

function cancelEdit() {
  editing.value = false
  editMarkdown.value = ''
}

async function saveEdit() {
  if (!prdStore.prd) return
  saving.value = true
  try {
    const prdId = (route.params.sessionId || route.params.id) as string
    await updatePrd(prdId, { markdown: editMarkdown.value })
    prdStore.prd = { ...prdStore.prd, markdown: editMarkdown.value }
    editing.value = false
    ElMessage.success('保存成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const sid = (route.params.sessionId || route.params.id) as string
  if (!sid) return
  // 优先按 prd_id 查（从需求池生成的 PRD 只有 id，没对应 session 上下文）
  await prdStore.loadById(sid)
  // fallback: 如果 by-id 查不到，再按 session_id 查
  if (!prdStore.prd) {
    await prdStore.load(sid)
  }
})
</script>

<style scoped>
.prd-actions {
  position: absolute;
  top: 12px;
  right: 16px;
  z-index: 10;
  display: flex;
  gap: 8px;
}

/* ── 编辑模式 ── */
.prd-edit-dual {
  display: flex;
  gap: 16px;
  height: calc(100vh - 120px);
  min-height: 400px;
}
.prd-edit-left {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.prd-edit-right {
  flex: 1;
  overflow-y: auto;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px;
}
.prd-edit-textarea {
  flex: 1;
  width: 100%;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px;
  resize: none;
  outline: none;
  background: var(--panel);
  color: var(--text);
}
.prd-edit-textarea:focus {
  border-color: var(--brand);
}
</style>
