<template>
  <div class="prd-view">
    <PrdToc
      v-if="prdStore.prd"
      :sections="sections"
      :active-index="activeIndex"
      @scroll-to="scrollToSection"
      @download="downloadMarkdown"
    />
    <div class="prd-content-wrap" ref="contentRef">
      <div v-if="!prdStore.prd" style="padding:40px;text-align:center;color:var(--muted)">正在加载 PRD...</div>
      <div v-else class="prd-content" v-html="renderedMarkdown"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { usePrdStore } from '@/stores/prd'
import { marked } from 'marked'
import hljs from 'highlight.js'
import PrdToc from '@/components/prd/PrdToc.vue'

const route = useRoute()
const prdStore = usePrdStore()
const contentRef = ref<HTMLElement | null>(null)
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
  if (typeof html === 'object') {
    // Fallback for async marked
    nextTick(async () => {
      const h = await marked.parse(prdStore.prd?.markdown || '')
      const el = document.querySelector('.prd-content')
      if (el) el.innerHTML = h
    })
    return '加载中...'
  }
  nextTick(() => {
    document.querySelectorAll('.prd-content pre code').forEach(block => {
      try { hljs.highlightElement(block as HTMLElement) } catch { /* skip */ }
    })
  })
  return html
})

function scrollToSection(index: number) {
  activeIndex.value = index
  const sec = sections.value?.[index]
  if (!sec) return
  // marked renders headings with auto-generated IDs from the heading text
  const el = document.getElementById(sec.id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  } else {
    // Fallback: try to find by inner text
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

onMounted(() => {
  const sid = route.params.sessionId as string
  if (sid) prdStore.load(sid)
})
</script>
