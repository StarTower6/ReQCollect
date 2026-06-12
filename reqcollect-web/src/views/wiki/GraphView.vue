<template>
  <div class="graph-page">
    <div v-if="loading" v-loading="loading" style="height:400px" />
    <el-empty v-else-if="!hasData" description="暂无图谱数据——先创建 Wiki 页面或工作区文件并使用 [[链接]] 建立关联" />
    <div v-else ref="graphContainer" class="graph-container" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { fetchWikiGraph } from '@/api/wiki'

const props = defineProps<{ workspaceId: string }>()
const router = useRouter()

const loading = ref(true)
const graphContainer = ref<HTMLElement | null>(null)
const graphData = ref<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] })
let network: any = null

const hasData = computed(() => graphData.value.nodes.length > 0)

async function loadGraph() {
  loading.value = true
  try {
    graphData.value = await fetchWikiGraph(props.workspaceId)
  } catch { /* silent */ }
  finally { loading.value = false }
}

function nodeColor(type: string): string {
  return type === 'file' ? '#67c23a' : '#409eff'
}

function renderGraph() {
  if (!graphContainer.value || graphData.value.nodes.length === 0) return

  // Dynamic import vis-network (vanilla JS, no TS types needed)
  const { Network } = (window as any).vis || {}

  // Actually, vis-network needs to be imported properly
  // Use the globally available version or import dynamically
  import('vis-network').then(mod => {
    const Network = mod.Network
    const { DataSet } = mod

    const nodes = new (DataSet as any)(graphData.value.nodes.map((n: any) => ({
      id: n.id,
      label: n.label,
      title: `${n.title} (${n.type === 'file' ? '文件' : 'Wiki'})`,
      value: n.value || 1,
      shape: 'dot',
      size: Math.min(30, Math.max(10, (n.value || 1) * 6)),
      font: { size: 13, face: '-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif' },
      borderWidth: 2,
      color: {
        background: nodeColor(n.type),
        border: nodeColor(n.type),
        highlight: { background: nodeColor(n.type), border: nodeColor(n.type) },
      },
      group: n.type,
    })))

    const edges = new (DataSet as any)(graphData.value.edges.map((e: any) => ({
      from: e.from,
      to: e.to,
      title: e.title || '引用',
      color: e.dashes ? { color: '#c0c4cc' } : { color: '#c0c4cc', highlight: '#409eff' },
      width: e.width || 1.5,
      dashes: e.dashes || false,
      arrows: e.dashes ? false : { to: { enabled: true, scaleFactor: 0.6 } },
      smooth: { type: 'continuous' },
    })))

    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -40,
          centralGravity: 0.005,
          springLength: 180,
          springConstant: 0.04,
          damping: 0.4,
        },
        stabilization: { iterations: 200 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true,
      },
      height: '100%',
    } as any

    network = new Network(graphContainer.value!, { nodes, edges }, options)

    // Click node → navigate to wiki page or file
    network.on('click', (params: any) => {
      const nodeId = params.nodes?.[0]
      if (!nodeId) return
      const node = graphData.value.nodes.find((n: any) => n.id === nodeId)
      if (!node) return
      if (node.type === 'wiki') {
        router.push(`/workspace/${props.workspaceId}/wiki/${nodeId.replace('wiki:', '')}`)
      } else {
        router.push(`/workspace/${props.workspaceId}`)
      }
    })
  }).catch(() => {
    // vis-network not loaded
    console.warn('vis-network not available')
  })
}

onMounted(async () => {
  await loadGraph()
  if (hasData.value) {
    // Wait for DOM render
    setTimeout(renderGraph, 100)
  }
})

onUnmounted(() => {
  if (network) {
    network.destroy()
    network = null
  }
})
</script>

<style scoped>
.graph-page {
  width: 100%;
  min-height: 400px;
}

.graph-container {
  width: 100%;
  height: 500px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafbfc;
}
</style>
