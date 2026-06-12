<template>
  <aside class="file-tree-panel">
    <!-- Header -->
    <div class="ftp-header">
      <span class="ftp-icon">📁</span>
      <span class="ftp-title">{{ wsName }}</span>
      <input ref="fileInput" type="file" hidden :accept="acceptStr" @change="handleUpload" />
      <el-button text size="small" @click="fileInput?.click()" :disabled="!workspaceId">+</el-button>
      <el-button text size="small" @click="showNewFolder = true" :disabled="!workspaceId">📂</el-button>
    </div>

    <!-- Loading / Empty / Tree -->
    <div class="ftp-body">
      <div v-if="loading" v-loading="true" style="height:200px" />
      <div v-else-if="!workspaceId" class="ftp-hint">请选择一个工作空间</div>
      <div v-else-if="tree.length === 0 && folders.length === 0" class="ftp-hint">暂无文件</div>
      <div v-else class="ftp-tree">
        <!-- Folder nodes -->
        <div v-for="folder in folders" :key="folder.id">
          <div class="ftp-dir" @click="folder._expanded = !folder._expanded"
            @mouseenter="folder._showActions = true" @mouseleave="folder._showActions = false">
            <span class="ftp-arrow" :class="{ open: folder._expanded }">▶</span>
            <span>📂</span>
            <span class="ftp-name" v-if="renamingId !== folder.id" @dblclick="startRename(folder)">{{ folder.name }}</span>
            <input v-else class="ftp-rename-input" v-model="renamingText" @keyup.enter="doRename(folder)" @blur="doRename(folder)" @keyup.escape="renamingId = ''" ref="renameInputRef" />
            <span class="ftp-badge">{{ folder._fileCount }}</span>
            <span v-if="folder._showActions && renamingId !== folder.id" class="ftp-folder-actions">
              <button class="ftp-fa-btn" @click.stop="startRename(folder)" title="重命名">✏️</button>
              <button class="ftp-fa-btn" @click.stop="confirmDelete(folder)" title="删除">🗑️</button>
            </span>
          </div>
          <div v-if="folder._expanded" class="ftp-children">
            <div v-for="f in folder._files" :key="f.path" class="ftp-file"
              :class="{ 'ftp-referenced': isRef(f.path), 'ftp-selected': selectedFilePath === f.path }"
              @mouseenter="f._showRef = true" @mouseleave="f._showRef = false">
              <span class="ftp-ficon">{{ ficon(f.type) }}</span>
              <span class="ftp-fname" @click="preview(f)">{{ f.label }}</span>
              <span class="ftp-fsize" v-if="f.size">{{ fmtSize(f.size) }}</span>
              <span v-if="f.source === 'generated'" class="ftp-ai">AI</span>
              <span v-if="f.analysis?.tags?.length" class="ftp-tags" :title="f.analysis?.summary || ''">
                <span v-for="tag in f.analysis.tags.slice(0, 2)" :key="tag" class="ftp-tag">{{ tag }}</span>
              </span>
              <button v-if="f._showRef || isRef(f.path)" class="ftp-ref"
                @click.stop="toggleRef(f.path)">
                {{ isRef(f.path) ? '✕' : '⊕' }}
              </button>
            </div>
          </div>
        </div>
        <!-- Root-level files (no folder) -->
        <div v-for="file in rootFiles" :key="file.path" class="ftp-file ftp-root-file"
          :class="{ 'ftp-referenced': isRef(file.path), 'ftp-selected': selectedFilePath === file.path }"
          @mouseenter="file._showRef = true" @mouseleave="file._showRef = false">
          <span class="ftp-ficon">{{ ficon(file.type) }}</span>
          <span class="ftp-fname" @click="preview(file)">{{ file.label }}</span>
          <span class="ftp-fsize" v-if="file.size">{{ fmtSize(file.size) }}</span>
          <span v-if="file.source === 'generated'" class="ftp-ai">AI</span>
          <span v-if="file.analysis?.tags?.length" class="ftp-tags" :title="file.analysis?.summary || ''">
            <span v-for="tag in file.analysis.tags.slice(0, 2)" :key="tag" class="ftp-tag">{{ tag }}</span>
          </span>
          <button v-if="file._showRef || isRef(file.path)" class="ftp-ref"
            @click.stop="toggleRef(file.path)">
            {{ isRef(file.path) ? '✕' : '⊕' }}
          </button>
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

    <!-- Related files section (tag similarity) -->
    <div v-if="relatedFiles.length" class="ftp-rel-section">
      <div class="ftp-rel-title">🔗 相关文件</div>
      <div v-for="rf in relatedFiles" :key="rf.path" class="ftp-rel-item"
        @click="previewNode(rf.path)" :title="rf.summary">
        <span>📄</span>
        <span class="ftp-rfname">{{ rf.path }}</span>
        <span class="ftp-rel-sim">{{ Math.round(rf.similarity * 100) }}%</span>
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

    <!-- New folder dialog -->
    <el-dialog v-model="showNewFolder" title="新建文件夹" width="360px" append-to-body>
      <el-input v-model="newFolderName" placeholder="文件夹名称" @keyup.enter="createFolder" />
      <div style="margin-top:8px">
        <el-select v-model="newFolderParent" placeholder="父文件夹（可选）" clearable style="width:100%">
          <el-option v-for="f in allFolders" :key="f.id" :label="f.name" :value="f.id" />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="showNewFolder = false">取消</el-button>
        <el-button type="primary" @click="createFolder" :disabled="!newFolderName.trim()">创建</el-button>
      </template>
    </el-dialog>

    <!-- Delete folder confirm -->
    <el-dialog v-model="showDeleteConfirm" title="删除文件夹" width="360px" append-to-body>
      <p>确定删除文件夹「{{ deletingFolder?.name }}」？</p>
      <p style="font-size:12px;color:#909399">文件夹内的文件将移出文件夹（不会删除文件本身）。</p>
      <template #footer>
        <el-button @click="showDeleteConfirm = false">取消</el-button>
        <el-button type="danger" @click="doDelete">删除</el-button>
      </template>
    </el-dialog>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { fetchWorkspaceFiles, readWorkspaceFile, uploadWorkspaceFile, fetchRelatedFiles,
  fetchFolders, createFolder as apiCreateFolder, renameFolder as apiRenameFolder, deleteFolder as apiDeleteFolder, setFileFolder } from '@/api/workspace_files'
import { fetchWorkspace } from '@/api/workspace'
import { apiGet } from '@/api/client'

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
const relatedFiles = ref<any[]>([])
const selectedFilePath = ref('')

// Folder state
const rawFolders = ref<any[]>([])
const allFolders = ref<any[]>([])
const showNewFolder = ref(false)
const newFolderName = ref('')
const newFolderParent = ref('')
const showDeleteConfirm = ref(false)
const deletingFolder = ref<any>(null)
const renamingId = ref('')
const renamingText = ref('')
const renameInputRef = ref<HTMLInputElement | null>(null)

// Preview
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewTitle = ref('')
const previewType = ref('')
const previewText = ref('')
const previewHtml = ref('')

const acceptStr = '.md,.txt,.json,.yaml,.yml,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.gif,.bmp'

// Build flat list for select
function flattenFolders(f: any[], prefix = ''): any[] {
  const result: any[] = []
  for (const n of f) {
    result.push({ ...n, _path: prefix + n.name })
    if (n.children) result.push(...flattenFolders(n.children, prefix + n.name + ' / '))
  }
  return result
}

// Build folders with files for display
const folders = computed(() => {
  return buildFolderTree(rawFolders.value, '')
})

const rootFiles = computed(() => {
  return files.value
    .filter((f: any) => !f.folder)  // no folder assigned
    .map((f: any) => ({
      label: f.path,
      path: f.path,
      type: f.type,
      size: f.size,
      source: f.source,
      analysis: f.analysis,
      _showRef: false,
    }))
})

function buildFolderTree(nodes: any[], parentId: string): any[] {
  const result: any[] = []
  const children = nodes.filter((n: any) => (n.parent_id || '') === parentId)
  for (const n of children) {
    const sub = buildFolderTree(nodes, n.id)
    const folderFiles = files.value
      .filter((f: any) => f.folder === n.id)
      .map((f: any) => ({
        label: f.path,
        path: f.path,
        type: f.type,
        size: f.size,
        source: f.source,
        analysis: f.analysis,
        _showRef: false,
      }))
    // Count files: direct + all sub-folder files
    const subCount = sub.reduce((s: number, c: any) => s + c._fileCount, 0)
    result.push({
      ...n,
      _expanded: n._expanded !== false,
      _showActions: false,
      _files: folderFiles,
      _fileCount: folderFiles.length + subCount,
      _children: sub,
    })
    // Append sub-folders after this folder's files
    if (sub.length > 0) {
      // Sub-folders are rendered at the same level after files
    }
  }
  return result
}

// Legacy: Build tree from flat file list for path-based display (fallback)
interface TreeNode {
  label: string
  path: string
  isLeaf: boolean
  expanded: boolean
  children: TreeNode[]
  type?: string
  size?: number
  source?: string
  analysis?: { tags?: string[]; summary?: string; domain?: string }
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
        current.push({
          label: part, path: full, isLeaf: true, expanded: false,
          children: [], type: f.type, size: f.size, source: f.source, analysis: f.analysis,
        })
      } else {
        let dir = current.find(n => !n.isLeaf && n.label === part)
        if (!dir) {
          dir = { label: part, path: full + '/', isLeaf: false, expanded: true, children: [] }
          current.push(dir)
        }
        current = dir.children
      }
    }
  }
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

async function preview(node: { path: string; type?: string }) {
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
  selectedFilePath.value = node.path
  try {
    relatedFiles.value = await fetchRelatedFiles(props.workspaceId, node.path)
  } catch {
    relatedFiles.value = []
  }
}

async function previewNode(fp: string) {
  if (!props.workspaceId) return
  const node = { path: fp, type: 'md' } as TreeNode
  await preview(node)
}

async function handleUpload(e: Event) {
  const inp = e.target as HTMLInputElement
  const file = inp?.files?.[0]
  if (!file || !props.workspaceId) return
  try {
    await uploadWorkspaceFile(props.workspaceId, file, localStorage.getItem('reqcollect_token') || '')
    ElMessage.success('上传成功')
    loadFiles()
    loadFoldersData()
  } catch (err: any) {
    ElMessage.error(err.message || '上传失败')
  }
  if (inp) inp.value = ''
}

// ── Folder operations ──

async function createFolder() {
  if (!props.workspaceId || !newFolderName.value.trim()) return
  try {
    await apiCreateFolder(props.workspaceId, newFolderName.value.trim(), newFolderParent.value || undefined)
    ElMessage.success('文件夹已创建')
    showNewFolder.value = false
    newFolderName.value = ''
    newFolderParent.value = ''
    loadFoldersData()
  } catch (err: any) {
    ElMessage.error(err.message || '创建失败')
  }
}

function startRename(folder: any) {
  renamingId.value = folder.id
  renamingText.value = folder.name
  nextTick(() => {
    const el = document.querySelector('.ftp-rename-input') as HTMLInputElement
    if (el) { el.focus(); el.select() }
  })
}

async function doRename(folder: any) {
  if (renamingId.value !== folder.id) return
  const id = renamingId.value
  renamingId.value = ''
  if (!renamingText.value.trim() || renamingText.value.trim() === folder.name) return
  try {
    await apiRenameFolder(props.workspaceId!, id, renamingText.value.trim())
    ElMessage.success('重命名成功')
    loadFoldersData()
  } catch (err: any) {
    ElMessage.error(err.message || '重命名失败')
  }
}

function confirmDelete(folder: any) {
  deletingFolder.value = folder
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!props.workspaceId || !deletingFolder.value) return
  try {
    await apiDeleteFolder(props.workspaceId, deletingFolder.value.id)
    ElMessage.success('文件夹已删除')
    showDeleteConfirm.value = false
    deletingFolder.value = null
    loadFoldersData()
  } catch (err: any) {
    ElMessage.error(err.message || '删除失败')
  }
}

async function loadFoldersData() {
  if (!props.workspaceId) { rawFolders.value = []; allFolders.value = []; return }
  try {
    const treeData = await fetchFolders(props.workspaceId, true)
    rawFolders.value = treeData
    allFolders.value = flattenFolders(treeData)
  } catch {
    rawFolders.value = []
    allFolders.value = []
  }
}

async function loadFiles() {
  if (!props.workspaceId) { files.value = []; wsName.value = ''; return }
  loading.value = true
  try {
    files.value = await fetchWorkspaceFiles(props.workspaceId)
    const ws = await fetchWorkspace(props.workspaceId)
    wsName.value = ws?.name || '工作区'
    try {
      const res: any = await apiGet(`/workspaces/${props.workspaceId}/linked-status`)
      linkedStatus.value = res.status
    } catch {}
  } catch { wsName.value = '工作区' }
    finally { loading.value = false }
}

watch(() => props.workspaceId, () => {
  loadFiles()
  loadFoldersData()
}, { immediate: true })
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
.ftp-file.ftp-selected { background: #e8f3ff; }
.ftp-root-file { padding-left: 8px; }
.ftp-ficon { font-size: 14px; flex-shrink: 0; }
.ftp-fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.ftp-fsize { font-size: 10px; color: #c0c4cc; flex-shrink: 0; }
.ftp-ai { font-size: 10px; color: #67c23a; background: #f0f9eb; padding: 0 4px; border-radius: 3px; flex-shrink: 0; }
.ftp-tags { display: inline-flex; gap: 2px; flex-shrink: 0; }
.ftp-tag { font-size: 10px; color: #909399; background: #f4f4f5; padding: 0 4px; border-radius: 3px; line-height: 16px; white-space: nowrap; }
.ftp-ref { font-size: 12px; border: none; background: none; cursor: pointer; color: #409eff; padding: 0 2px; flex-shrink: 0; }
.ftp-folder-actions { display: inline-flex; gap: 2px; flex-shrink: 0; margin-left: 4px; }
.ftp-fa-btn { font-size: 10px; border: none; background: none; cursor: pointer; padding: 0 2px; line-height: 1; opacity: 0.6; }
.ftp-fa-btn:hover { opacity: 1; }
.ftp-rename-input { flex: 1; font-size: 12px; padding: 1px 4px; border: 1px solid #409eff; border-radius: 3px; outline: none; min-width: 0; }
.ftp-references { border-top: 1px solid var(--line, #f0f0f5); padding: 6px 12px; flex-shrink: 0; max-height: 120px; overflow-y: auto; }
.ftp-reftitle { font-size: 11px; color: #c0c4cc; margin-bottom: 4px; }
.ftp-reffile { display: flex; align-items: center; gap: 4px; padding: 2px 4px; font-size: 12px; color: #409eff; background: #ecf5ff; border-radius: 4px; margin-bottom: 2px; }
.ftp-rfname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ftp-rfdel { border: none; background: none; cursor: pointer; font-size: 11px; color: #c0c4cc; padding: 0; }
.ftp-footer { border-top: 1px solid var(--line, #f0f0f5); padding: 6px 12px; font-size: 11px; flex-shrink: 0; }
.ftp-ftime { color: #c0c4cc; }
.ftp-rel-section { border-top: 1px solid var(--line, #f0f0f5); padding: 6px 12px; flex-shrink: 0; max-height: 120px; overflow-y: auto; }
.ftp-rel-title { font-size: 11px; color: #c0c4cc; margin-bottom: 4px; }
.ftp-rel-item { display: flex; align-items: center; gap: 4px; padding: 2px 4px; font-size: 12px; color: #606266; border-radius: 4px; margin-bottom: 2px; cursor: pointer; }
.ftp-rel-item:hover { background: #f0f3f8; }
.ftp-rel-sim { font-size: 10px; color: #c0c4cc; flex-shrink: 0; }
.ftp-preview-md { padding: 16px; max-height: 65vh; overflow-y: auto; }
.ftp-preview-text { padding: 16px; max-height: 65vh; overflow-y: auto; white-space: pre-wrap; font-size: 13px; }
</style>
