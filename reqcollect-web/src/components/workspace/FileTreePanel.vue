<template>
  <aside class="file-tree-panel">
    <!-- Header -->
    <div class="ftp-header">
      <span class="ftp-icon">📁</span>
      <span class="ftp-title">{{ wsName }}</span>
      <input ref="fileInput" type="file" hidden :accept="acceptStr" @change="handleUpload" />
      <el-button text size="small" @click="fileInput?.click()" :disabled="!workspaceId">+</el-button>
    </div>

    <!-- Loading / Empty / Tree -->
    <div class="ftp-body">
      <div v-if="loading" v-loading="true" style="height:200px" />
      <div v-else-if="!workspaceId" class="ftp-hint">请选择一个工作空间</div>
      <div v-else-if="tree.length === 0" class="ftp-hint">暂无文件</div>
      <div v-else class="ftp-tree">
        <div v-for="node in tree" :key="node.path">
          <!-- Directory -->
          <div v-if="!node.isLeaf" class="ftp-dir" @click="node.expanded = !node.expanded">
            <span class="ftp-arrow" :class="{ open: node.expanded }">▶</span>
            <span>📂</span>
            <span class="ftp-name">{{ node.label }}</span>
            <span class="ftp-badge">{{ node.children?.length || 0 }}</span>
          </div>
          <!-- Children -->
          <div v-if="!node.isLeaf && node.expanded" class="ftp-children">
            <div v-for="child in node.children" :key="child.path" class="ftp-file"
              :class="{ 'ftp-referenced': isRef(child.path) }"
              @mouseenter="child._showRef = true" @mouseleave="child._showRef = false">
              <span class="ftp-ficon">{{ ficon(child.type) }}</span>
              <span class="ftp-fname" @click="preview(child)">{{ child.label }}</span>
              <span class="ftp-fsize" v-if="child.size">{{ fmtSize(child.size) }}</span>
              <span v-if="child.source === 'generated'" class="ftp-ai">AI</span>
              <button v-if="child._showRef || isRef(child.path)" class="ftp-ref"
                @click.stop="toggleRef(child.path)">
                {{ isRef(child.path) ? '✕' : '⊕' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Referenced files section -->
    <div v-if="referencedFiles.length" class="ftp-references">
      <div class="ftp-reftitle">📎 当前引用</div>
      <div v-for="rf in referencedFiles" :key="rf" class="ftp-reffile">
        <span>📝</span><span class="ftp-rfname">{{ rf }}</span>
        <button class="ftp-rfdel" @click="$emit('removeReference', rf)">✕</button>
      </div>
    </div>

    <!-- Footer -->
    <div class="ftp-footer">
      <span v-if="linkedStatus?.linked" class="ftp-ftime">🔄 {{ syncTime }}</span>
      <span v-else class="ftp-ftime" style="color:#c0c4cc">未关联目录</span>
    </div>

    <!-- Preview dialog -->
    <el-dialog v-model="previewVisible" :title="previewTitle" width="700px" top="5vh" destroy-on-close>
      <div v-if="previewLoading" v-loading="true" style="height:200px" />
      <div v-else-if="previewType === 'md'" class="ftp-preview-md" v-html="previewHtml" />
      <pre v-else class="ftp-preview-text">{{ previewText }}</pre>
    </el-dialog>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { fetchWorkspaceFiles, readWorkspaceFile, uploadWorkspaceFile } from '@/api/workspace_files'

const props = defineProps<{
  workspaceId: string | null
  referencedFiles: string[]
}>()

const emit = defineEmits<{
  reference: [path: string]
  removeReference: [path: string]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const files = ref<any[]>([])
const loading = ref(false)
const wsName = ref('')
const linkedStatus = ref<any>(null)

// Preview
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewTitle = ref('')
const previewType = ref('')
const previewText = ref('')
const previewHtml = ref('')

const acceptStr = '.md,.txt,.json,.yaml,.yml,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.gif,.bmp'

// Build tree from flat file list
interface TreeNode {
  label: string
  path: string
  isLeaf: boolean
  expanded: boolean
  children: TreeNode[]
  type?: string
  size?: number
  source?: string
  _showRef?: boolean
}

const tree = computed<TreeNode[]>(() => {
  const result: TreeNode[] = []

  for (const f of files.value) {
    const parts = f.path.split('/')
    let current = result
    let full = ''
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      full = full ? full + '/' + part : part
      if (i === parts.length - 1) {
        // Leaf
        current.push({
          label: part, path: full, isLeaf: true, expanded: false,
          children: [], type: f.type, size: f.size, source: f.source,
        })
      } else {
        // Directory
        let dir = current.find(n => !n.isLeaf && n.label === part)
        if (!dir) {
          dir = { label: part, path: full + '/', isLeaf: false, expanded: true, children: [] }
          current.push(dir)
        }
        current = dir.children
      }
    }
  }

  // Sort: directories first, then files
  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.isLeaf !== b.isLeaf) return a.isLeaf ? 1 : -1
      return a.label.localeCompare(b.label)
    })
    for (const n of nodes) n.children && sortNodes(n.children)
  }
  sortNodes(result)
  return result
})

const syncTime = computed(() => {
  if (!linkedStatus.value) return ''
  return linkedStatus.value.linked ? '已关联' : ''
})

function ficon(type: string | undefined) {
  if (!type) return '📄'
  const m: Record<string, string> = { md: '📝', txt: '📄', json: '📋', yaml: '⚙️', yml: '⚙️',
    docx: '📘', xlsx: '📊', pptx: '📙', png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🖼️', bmp: '🖼️' }
  return m[type] || '📄'
}

function fmtSize(s: number) {
  if (s < 1024) return `${s}B`
  if (s < 1024 * 1024) return `${(s / 1024).toFixed(0)}K`
  return `${(s / 1024 / 1024).toFixed(1)}M`
}

function isRef(path: string) {
  return props.referencedFiles.includes(path)
}

function toggleRef(path: string) {
  if (isRef(path)) emit('removeReference', path)
  else emit('reference', path)
}

async function preview(node: TreeNode) {
  if (!node.path || !props.workspaceId) return
  previewVisible.value = true
  previewLoading.value = true
  previewTitle.value = node.path
  previewText.value = ''
  previewHtml.value = ''
  previewType.value = node.type || 'txt'
  try {
    const content = await readWorkspaceFile(props.workspaceId, node.path, 8000)
    previewType.value = content.type
    if (content.type === 'md') {
      previewHtml.value = marked.parse(content.text || '') as string
    } else {
      previewText.value = content.text || ''
    }
  } catch {
    previewText.value = '读取文件失败'
  } finally {
    previewLoading.value = false
  }
}

async function handleUpload(e: Event) {
  const inp = e.target as HTMLInputElement
  const file = inp?.files?.[0]
  if (!file || !props.workspaceId) return
  try {
    await uploadWorkspaceFile(props.workspaceId, file, localStorage.getItem('reqcollect_token') || '')
    ElMessage.success('上传成功')
    loadFiles()
  } catch (err: any) {
    ElMessage.error(err.message || '上传失败')
  }
  if (inp) inp.value = ''
}

async function loadFiles() {
  if (!props.workspaceId) { files.value = []; wsName.value = ''; return }
  loading.value = true
  try {
    files.value = await fetchWorkspaceFiles(props.workspaceId)
    // Try to get workspace name
    const { fetchWorkspace } = await import('@/api/workspace')
    const ws = await fetchWorkspace(props.workspaceId)
    wsName.value = ws?.name || '工作区'
    // Try linked status
    try {
      const { apiGet } = await import('@/api/client')
      const res: any = await apiGet(`/workspaces/${props.workspaceId}/linked-status`)
      linkedStatus.value = res.status
    } catch {}
  } catch { wsName.value = '工作区' }
    finally { loading.value = false }
}

watch(() => props.workspaceId, () => { loadFiles() })
</script>

<style scoped>
.file-tree-panel { width: 260px; min-width: 260px; border-left: 1px solid var(--line, #e5e6eb); background: var(--panel, #fff); display: flex; flex-direction: column; height: 100vh; font-size: 13px; overflow: hidden; }
.ftp-header { padding: 10px 12px; border-bottom: 1px solid var(--line, #f0f0f5); display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.ftp-icon { font-size: 16px; }
.ftp-title { flex: 1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.ftp-body { flex: 1; overflow-y: auto; padding: 4px 0; }
.ftp-hint { text-align: center; padding: 40px 16px; color: #c0c4cc; font-size: 13px; }
.ftp-dir { padding: 4px 8px; display: flex; align-items: center; gap: 4px; cursor: pointer; font-size: 12px; color: #666; }
.ftp-dir:hover { background: #f7f8fa; }
.ftp-arrow { font-size: 10px; transition: transform .15s; width: 10px; }
.ftp-arrow.open { transform: rotate(90deg); }
.ftp-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ftp-badge { font-size: 10px; color: #c0c4cc; }
.ftp-children { }
.ftp-file { padding: 3px 8px 3px 28px; display: flex; align-items: center; gap: 4px; border-radius: 4px; cursor: pointer; }
.ftp-file:hover { background: #f0f3f8; }
.ftp-file.ftp-referenced { background: #ecf5ff; }
.ftp-ficon { font-size: 14px; flex-shrink: 0; }
.ftp-fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.ftp-fsize { font-size: 10px; color: #c0c4cc; flex-shrink: 0; }
.ftp-ai { font-size: 10px; color: #67c23a; background: #f0f9eb; padding: 0 4px; border-radius: 3px; flex-shrink: 0; }
.ftp-ref { font-size: 12px; border: none; background: none; cursor: pointer; color: #409eff; padding: 0 2px; flex-shrink: 0; }
.ftp-references { border-top: 1px solid var(--line, #f0f0f5); padding: 6px 12px; flex-shrink: 0; max-height: 120px; overflow-y: auto; }
.ftp-reftitle { font-size: 11px; color: #c0c4cc; margin-bottom: 4px; }
.ftp-reffile { display: flex; align-items: center; gap: 4px; padding: 2px 4px; font-size: 12px; color: #409eff; background: #ecf5ff; border-radius: 4px; margin-bottom: 2px; }
.ftp-rfname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ftp-rfdel { border: none; background: none; cursor: pointer; font-size: 11px; color: #c0c4cc; padding: 0; }
.ftp-footer { border-top: 1px solid var(--line, #f0f0f5); padding: 6px 12px; font-size: 11px; flex-shrink: 0; }
.ftp-ftime { color: #c0c4cc; }
.ftp-preview-md { padding: 16px; max-height: 65vh; overflow-y: auto; }
.ftp-preview-text { padding: 16px; max-height: 65vh; overflow-y: auto; white-space: pre-wrap; font-size: 13px; }
</style>
