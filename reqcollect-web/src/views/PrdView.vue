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
  const result: string[] = []
  for (const line of lines) {
    if (line.startsWith('## ')) result.push(line.replace(/^##\s+/, ''))
    if (line.startsWith('# ')) result.push(line.replace(/^#\s+/, ''))
  }
  return result
})

const renderedMarkdown = computed(() => {
  if (!prdStore.prd?.markdown) return ''
  const html = marked.parse(prdStore.prd.markdown, { async: false }) as string
  nextTick(() => {
    document.querySelectorAll('.prd-content pre code').forEach(block => {
      hljs.highlightElement(block as HTMLElement)
    })
  })
  return html
})

function scrollToSection(index: number) {
  activeIndex.value = index
  const el = document.getElementById(`section-${index}`)
  el?.scrollIntoView({ behavior: 'smooth' })
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
