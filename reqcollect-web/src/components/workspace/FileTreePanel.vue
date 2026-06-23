<template>
  <aside class="file-tree-panel">
    <div class="ftp-header">
      <span class="ftp-icon">📁</span>
      <span class="ftp-title">{{ wsName }}</span>
      <input ref="fileInput" type="file" hidden :accept="acceptStr" @change="handleUpload" />
      <el-button text size="small" @click="fileInput?.click()" :disabled="!workspaceId">+</el-button>
      <el-button text size="small" @click="showNewFolder = true" :disabled="!workspaceId">📂</el-button>
    </div>

    <div class="ftp-body">
      <div v-if="loading" v-loading="true" style="height:200px" />
      <div v-else-if="!workspaceId" class="ftp-hint">请选择一个工作空间</div>
      <div v-else-if="files.length === 0 && allFolders.length === 0" class="ftp-hint">暂无文件</div>
      <div v-else class="ftp-tree">
        <!-- Flattened folder + file tree -->
        <template v-for="item in allFlatItems" :key="item.key">
          <!-- Separator -->
          <div v-if="item.key === '---separator---'" class="ftp-root-separator">{{ item.label }}</div>
          <!-- Folder header -->
          <div v-else-if="item.type === 'folder'" class="ftp-dir"
            :style="{ paddingLeft: (item.depth * 16 + 8) + 'px' }"
            @click="item.id && toggleFolder(item.id)"
            @mouseenter="hoverFolderId = item.id || ''" @mouseleave="hoverFolderId = ''">
            <span class="ftp-arrow" :class="{ open: item.id ? expandedState[item.id] : false }">▶</span>
            <span>📂</span>
            <span v-if="renamingId !== item.id" class="ftp-name" @dblclick="startRename(item)">{{ item.label }}</span>
            <input v-else class="ftp-rename-input" v-model="renamingText"
              @keyup.enter="doRename(item.id, item.label)" @blur="doRename(item.id, item.label)"
              @keyup.escape="renamingId = ''" ref="renameInputRef" />
            <span class="ftp-badge">{{ item.fileCount }}</span>
            <span v-if="hoverFolderId === item.id && renamingId !== item.id" class="ftp-folder-actions">
              <button class="ftp-fa-btn" @click.stop="startRename(item)" title="重命名">✏️</button>
              <button class="ftp-fa-btn" @click.stop="confirmDelete(item)" title="删除">🗑️</button>
            </span>
          </div>
          <!-- File inside a folder -->
          <div v-else-if="item.type === 'file'" class="ftp-file"
            :style="{ paddingLeft: (item.depth * 16 + 24) + 'px' }"
            :class="{ 'ftp-referenced': isRef(item.path), 'ftp-selected': selectedFilePath === item.path }"
            @mouseenter="hoverFilePath = item.path" @mouseleave="hoverFilePath = ''">
            <span class="ftp-ficon">{{ ficon(item.fileType) }}</span>
            <span class="ftp-fname" @click="preview(item)">{{ item.label }}</span>
            <span class="ftp-fsize" v-if="item.size">{{ fmtSize(item.size) }}</span>
            <span v-if="item.source === 'generated'" class="ftp-ai">AI</span>
            <span v-if="item.analysis?.tags?.length" class="ftp-tags" :title="item.analysis?.summary || ''">
              <span v-for="tag in item.analysis.tags.slice(0, 2)" :key="tag" class="ftp-tag">{{ tag }}</span>
            </span>
            <span v-if="hoverFilePath === item.path" class="ftp-file-actions">
              <button class="ftp-fa-btn" @click.stop="startMoveFile(item.path)" title="移动到文件夹">📁</button>
              <button class="ftp-fa-btn" @click.stop="confirmDeleteFile(item.path)" title="删除">🗑️</button>
            </span>
            <button v-if="hoverFilePath === item.path || isRef(item.path)" class="ftp-ref"
              @click.stop="toggleRef(item.path)">
              {{ isRef(item.path) ? '✕' : '⊕' }}
            </button>
          </div>
          <!-- Separator -->
          <div v-else-if="item.key === '---separator---'" class="ftp-root-separator">{{ item.label }}</div>
          <!-- Root-level file -->
          <div v-else-if="item.type === 'rootFile'" class="ftp-file ftp-root-file"
            :class="{ 'ftp-referenced': isRef(item.path), 'ftp-selected': selectedFilePath === item.path }"
            @mouseenter="hoverFilePath = item.path" @mouseleave="hoverFilePath = ''">
            <span class="ftp-ficon">{{ ficon(item.fileType) }}</span>
            <span class="ftp-fname" @click="preview(item)">{{ item.label }}</span>
            <span class="ftp-fsize" v-if="item.size">{{ fmtSize(item.size) }}</span>
            <span v-if="item.source === 'generated'" class="ftp-ai">AI</span>
            <span v-if="item.analysis?.tags?.length" class="ftp-tags" :title="item.analysis?.summary || ''">
              <span v-for="tag in item.analysis.tags.slice(0, 2)" :key="tag" class="ftp-tag">{{ tag }}</span>
            </span>
            <span v-if="hoverFilePath === item.path" class="ftp-file-actions">
              <button class="ftp-fa-btn" @click.stop="startMoveFile(item.path)" title="移动到文件夹">📁</button>
              <button class="ftp-fa-btn" @click.stop="confirmDeleteFile(item.path)" title="删除">🗑️</button>
            </span>
            <button v-if="hoverFilePath === item.path || isRef(item.path)" class="ftp-ref"
              @click.stop="toggleRef(item.path)">
              {{ isRef(item.path) ? '✕' : '⊕' }}
            </button>
          </div>
        </template>
      </div>
    </div>

    <div v-if="referencedFiles.length" class="ftp-references">
      <div class="ftp-reftitle">📎 当前引用</div>
      <div v-for="rf in referencedFiles" :key="rf" class="ftp-reffile">
        <span>📝</span><span class="ftp-rfname">{{ rf }}</span>
        <button class="ftp-rfdel" @click="$emit('removeReference', rf)">✕</button>
      </div>
    </div>

    <div v-if="relatedFiles.length" class="ftp-rel-section">
      <div class="ftp-rel-title">🔗 相关文件</div>
      <div v-for="rf in relatedFiles" :key="rf.path" class="ftp-rel-item"
        @click="previewNode(rf.path)" :title="rf.summary">
        <span>📄</span>
        <span class="ftp-rfname">{{ rf.path }}</span>
        <span class="ftp-rel-sim">{{ Math.round(rf.similarity * 100) }}%</span>
      </div>
    </div>

    <div class="ftp-footer">
      <span v-if="linkedStatus?.linked" class="ftp-ftime">🔄 {{ syncTime }}</span>
      <span v-else class="ftp-ftime" style="color:var(--muted-light)">未关联目录</span>
    </div>

    <el-dialog v-model="previewVisible" :title="previewTitle" width="700px" top="5vh" destroy-on-close>
      <div v-if="previewLoading" v-loading="true" style="height:200px" />
      <div v-else-if="previewType === 'md'" class="ftp-preview-md" v-html="previewHtml" />
      <pre v-else class="ftp-preview-text">{{ previewText }}</pre>
    </el-dialog>

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

    <el-dialog v-model="showUploadPicker" title="上传到文件夹" width="360px" append-to-body>
      <p style="font-size:12px;color:var(--muted);margin-bottom:8px">选择上传文件的存放位置（可选）</p>
      <el-select v-model="uploadFolderId" placeholder="根目录（不放入文件夹）" clearable style="width:100%">
        <el-option v-for="f in allFolders" :key="f.id" :label="f.name" :value="f.id" />
      </el-select>
      <template #footer>
        <el-button @click="showUploadPicker = false">取消</el-button>
        <el-button type="primary" @click="doUploadWithFolder">上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showMovePicker" title="移动到文件夹" width="360px" append-to-body>
      <el-select v-model="moveTargetFolderId" placeholder="选择目标文件夹" style="width:100%">
        <el-option v-for="f in allFolders" :key="f.id" :label="f.name" :value="f.id" />
        <el-option label="根目录（移出文件夹）" value="" />
      </el-select>
      <template #footer>
        <el-button @click="showMovePicker = false">取消</el-button>
        <el-button type="primary" @click="doMoveFile">移动</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDeleteFileConfirm" title="删除文件" width="360px" append-to-body>
      <p>确定删除文件「{{ deletingFilePath }}」？</p>
      <p style="font-size:12px;color:var(--muted)">此操作不可恢复。</p>
      <template #footer>
        <el-button @click="showDeleteFileConfirm = false">取消</el-button>
        <el-button type="danger" @click="doDeleteFile">删除</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDeleteConfirm" title="删除文件夹" width="360px" append-to-body>
      <p>确定删除文件夹「{{ deletingFolder?.name }}」？</p>
      <p style="font-size:12px;color:var(--muted)">文件夹内的文件将移出文件夹（不会删除文件本身）。</p>
      <template #footer>
        <el-button @click="showDeleteConfirm = false">取消</el-button>
        <el-button type="danger" @click="doDelete">删除</el-button>
      </template>
    </el-dialog>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { fetchWorkspaceFiles, readWorkspaceFile, uploadWorkspaceFile, fetchRelatedFiles,
  fetchFolders, createFolder as apiCreateFolder, renameFolder as apiRenameFolder,
  deleteFolder as apiDeleteFolder, setFileFolder, deleteWorkspaceFile } from '@/api/workspace_files'
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
const hoverFilePath = ref('')
const hoverFolderId = ref('')

// Folders
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

// Upload
const showUploadPicker = ref(false)
const uploadFolderId = ref('')
const pendingUploadFile = ref<File | null>(null)

// Move
const showMovePicker = ref(false)
const moveTargetFolderId = ref('')
const movingFilePath = ref('')

// Delete file
const showDeleteFileConfirm = ref(false)
const deletingFilePath = ref('')

// Preview
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewTitle = ref('')
const previewType = ref('')
const previewText = ref('')
const previewHtml = ref('')

const acceptStr = '.md,.txt,.json,.yaml,.yml,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.gif,.bmp'

const expandedState = reactive<Record<string, boolean>>({})

function toggleFolder(id: string) {
  expandedState[id] = !expandedState[id]
}

// Flat tree: one flat array with all folders + files, depth-ordered
interface FlatItem {
  key: string
  id: string
  type: 'folder' | 'file' | 'rootFile'
  label: string
  depth: number
  path: string
  fileType?: string
  size?: number
  source?: string
  analysis?: any
  fileCount?: number
}

const flatTree = computed<FlatItem[]>(() => {
  const result: FlatItem[] = []

  function walk(nodes: any[], parentId: string, depth: number) {
    const children = nodes.filter((n: any) => (n.parent_id || '') === parentId)
    for (const n of children) {
      // Get files in this folder
      const folderFiles = files.value.filter((f: any) => f.folder === n.id)
      const subFolders = nodes.filter((f: any) => (f.parent_id || '') === n.id)
      const subFileCount = folderFiles.length + subFolders.length
      // Count recursively for badge
      let totalFileCount = folderFiles.length
      function countSub(fid: string): number {
        let c = 0
        for (const f of nodes) {
          if ((f.parent_id || '') === fid) {
            const ff = files.value.filter((x: any) => x.folder === f.id)
            c += ff.length + countSub(f.id)
          }
        }
        return c
      }
      totalFileCount += countSub(n.id)

      result.push({
        key: 'folder-' + n.id,
        id: n.id,
        path: '',
        type: 'folder',
        label: n.name,
        depth,
        fileCount: totalFileCount,
      })

      if (expandedState[n.id]) {
        // Files
        for (const f of folderFiles) {
          result.push({
            key: 'file-' + f.path,
            id: f.path,
            path: f.path,
            type: 'file',
            label: f.path,
            depth: depth + 1,
            fileType: f.type,
            size: f.size,
            source: f.source,
            analysis: f.analysis,
          })
        }
        // Sub-folders
        walk(nodes, n.id, depth + 1)
      }
    }
  }

  walk(rawFolders.value, '', 0)
  return result
})

// Root-level files (no folder)
const rootFiles = computed(() => {
  return files.value
    .filter((f: any) => !f.folder)
    .map((f: any) => ({
      label: f.path, path: f.path, type: f.type, size: f.size,
      source: f.source, analysis: f.analysis,
    }))
})

// Flat list also includes root-level files after folders
const allFlatItems = computed<FlatItem[]>(() => {
  const items = [...flatTree.value]
  const rf = rootFiles.value
  if (rf.length > 0) {
    if (flatTree.value.length > 0) {
      // Insert a separator before root-level files when there are folders
      items.push({
        key: '---separator---',
        id: '__sep__',
        path: '',
        type: 'folder',
        label: '— 未分类 —',
        depth: -1,
      })
    }
    for (const f of rf) {
      items.push({
        key: 'root-' + f.path,
        id: f.path,
        path: f.path,
        type: 'rootFile',
        label: f.label,
        depth: 0,
        fileType: f.type,
        size: f.size,
        source: f.source,
        analysis: f.analysis || undefined,
      })
    }
  }
  return items
})

function flattenFolders(f: any[], prefix = ''): any[] {
  const result: any[] = []
  for (const n of f) {
    result.push({ ...n, _path: prefix + n.name })
    if (n.children) result.push(...flattenFolders(n.children, prefix + n.name + ' / '))
  }
  return result
}

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

async function preview(p: { path?: string; type?: string }) {
  if (!p.path || !props.workspaceId) return
  previewVisible.value = true
  previewLoading.value = true
  previewTitle.value = p.path
  previewText.value = ''
  previewHtml.value = ''
  previewType.value = p.type || 'txt'
  try {
    const content = await readWorkspaceFile(props.workspaceId, p.path, 8000)
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
  selectedFilePath.value = p.path
  try {
    relatedFiles.value = await fetchRelatedFiles(props.workspaceId, p.path)
  } catch {
    relatedFiles.value = []
  }
}

async function previewNode(fp: string) {
  if (!props.workspaceId) return
  await preview({ path: fp, type: 'md' })
}

async function handleUpload(e: Event) {
  const inp = e.target as HTMLInputElement
  const file = inp?.files?.[0]
  if (!file || !props.workspaceId) return
  pendingUploadFile.value = file
  uploadFolderId.value = ''
  showUploadPicker.value = true
  if (inp) inp.value = ''
}

async function doUploadWithFolder() {
  if (!props.workspaceId || !pendingUploadFile.value) return
  try {
    const result = await uploadWorkspaceFile(props.workspaceId, pendingUploadFile.value, localStorage.getItem('reqcollect_token') || '')
    if (uploadFolderId.value && result?.path) {
      await setFileFolder(props.workspaceId, result.path, uploadFolderId.value)
    }
    ElMessage.success('上传成功')
    showUploadPicker.value = false
    pendingUploadFile.value = null
    reloadAll()
  } catch (err: any) {
    ElMessage.error(err.message || '上传失败')
  }
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

function startRename(item: any) {
  renamingId.value = item.id
  renamingText.value = item.label
  nextTick(() => {
    const el = document.querySelector('.ftp-rename-input') as HTMLInputElement
    if (el) { el.focus(); el.select() }
  })
}

async function doRename(id: string, oldLabel: string) {
  if (renamingId.value !== id) return
  renamingId.value = ''
  if (!renamingText.value.trim() || renamingText.value.trim() === oldLabel) return
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
    reloadAll()
  } catch (err: any) {
    ElMessage.error(err.message || '删除失败')
  }
}

// ── Move file ──

function startMoveFile(filePath: string) {
  movingFilePath.value = filePath
  moveTargetFolderId.value = ''
  showMovePicker.value = true
}

async function doMoveFile() {
  if (!props.workspaceId || !movingFilePath.value) return
  try {
    await setFileFolder(props.workspaceId, movingFilePath.value, moveTargetFolderId.value)
    ElMessage.success('已移动')
    showMovePicker.value = false
    reloadAll()
  } catch (err: any) {
    ElMessage.error(err.message || '移动失败')
  }
}

// ── Delete file ──

function confirmDeleteFile(filePath: string) {
  deletingFilePath.value = filePath
  showDeleteFileConfirm.value = true
}

async function doDeleteFile() {
  if (!props.workspaceId || !deletingFilePath.value) return
  try {
    await deleteWorkspaceFile(props.workspaceId, deletingFilePath.value)
    ElMessage.success('文件已删除')
    showDeleteFileConfirm.value = false
    deletingFilePath.value = ''
    reloadAll()
  } catch (err: any) {
    ElMessage.error(err.message || '删除失败')
  }
}

function reloadAll() {
  loadFiles()
  loadFoldersData()
}

async function loadFoldersData() {
  if (!props.workspaceId) { rawFolders.value = []; allFolders.value = []; return }
  try {
    const treeData = await fetchFolders(props.workspaceId, true)
    rawFolders.value = treeData
    allFolders.value = flattenFolders(treeData)
    // Initialize expand state for all folders (default: expanded)
    function initExpand(folders: any[]) {
      for (const f of folders) {
        if (expandedState[f.id] === undefined) expandedState[f.id] = true
        if (f.children) initExpand(f.children)
      }
    }
    initExpand(treeData)
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
  reloadAll()
}, { immediate: true })
</script>

<style scoped>
.file-tree-panel { width: 260px; min-width: 260px; border-left: 1px solid var(--line); background: var(--panel); display: flex; flex-direction: column; height: 100vh; font-size: 13px; overflow: hidden; }
.ftp-header { padding: 10px 12px; border-bottom: 1px solid var(--line); display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.ftp-icon { font-size: 16px; }
.ftp-title { flex: 1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.ftp-body { flex: 1; overflow-y: auto; padding: 4px 0; }
.ftp-hint { text-align: center; padding: 40px 16px; color: var(--muted-light); font-size: 13px; }
.ftp-dir { padding: 4px 8px; display: flex; align-items: center; gap: 4px; cursor: pointer; font-size: 12px; color: var(--muted); }
.ftp-dir:hover { background: var(--sidebar); }
.ftp-arrow { font-size: 10px; transition: transform .15s; width: 10px; }
.ftp-arrow.open { transform: rotate(90deg); }
.ftp-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ftp-badge { font-size: 10px; color: var(--muted-light); }
.ftp-file { padding: 3px 8px 3px 24px; display: flex; align-items: center; gap: 4px; border-radius: 4px; cursor: pointer; }
.ftp-file:hover { background: var(--sidebar-hover); }
.ftp-file.ftp-referenced { background: var(--brand-soft); }
.ftp-file.ftp-selected { background: var(--brand-soft); }
.ftp-root-file { padding-left: 8px; }
.ftp-ficon { font-size: 14px; flex-shrink: 0; }
.ftp-fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.ftp-fsize { font-size: 10px; color: var(--muted-light); flex-shrink: 0; }
.ftp-ai { font-size: 10px; color: #67c23a; background: #f0f9eb; padding: 0 4px; border-radius: 3px; flex-shrink: 0; }
.ftp-tags { display: inline-flex; gap: 2px; flex-shrink: 0; }
.ftp-tag { font-size: 10px; color: var(--muted); background: var(--sidebar-hover); padding: 0 4px; border-radius: 3px; line-height: 16px; white-space: nowrap; }
.ftp-ref { font-size: 12px; border: none; background: none; cursor: pointer; color: var(--brand); padding: 0 2px; flex-shrink: 0; }
.ftp-folder-actions { display: inline-flex; gap: 2px; flex-shrink: 0; margin-left: 4px; }
.ftp-file-actions { display: inline-flex; gap: 2px; flex-shrink: 0; }
.ftp-fa-btn { font-size: 10px; border: none; background: none; cursor: pointer; padding: 0 2px; line-height: 1; opacity: 0.6; }
.ftp-fa-btn:hover { opacity: 1; }
.ftp-rename-input { flex: 1; font-size: 12px; padding: 1px 4px; border: 1px solid var(--brand); border-radius: 3px; outline: none; min-width: 0; }
.ftp-references { border-top: 1px solid var(--line); padding: 6px 12px; flex-shrink: 0; max-height: 120px; overflow-y: auto; }
.ftp-reftitle { font-size: 11px; color: var(--muted-light); margin-bottom: 4px; }
.ftp-reffile { display: flex; align-items: center; gap: 4px; padding: 2px 4px; font-size: 12px; color: var(--brand); background: var(--brand-soft); border-radius: 4px; margin-bottom: 2px; }
.ftp-rfname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ftp-rfdel { border: none; background: none; cursor: pointer; font-size: 11px; color: var(--muted-light); padding: 0; }
.ftp-footer { border-top: 1px solid var(--line); padding: 6px 12px; font-size: 11px; flex-shrink: 0; }
.ftp-ftime { color: var(--muted-light); }
.ftp-rel-section { border-top: 1px solid var(--line); padding: 6px 12px; flex-shrink: 0; max-height: 120px; overflow-y: auto; }
.ftp-rel-title { font-size: 11px; color: var(--muted-light); margin-bottom: 4px; }
.ftp-rel-item { display: flex; align-items: center; gap: 4px; padding: 2px 4px; font-size: 12px; color: var(--muted); border-radius: 4px; margin-bottom: 2px; cursor: pointer; }
.ftp-rel-item:hover { background: var(--sidebar-hover); }
.ftp-rel-sim { font-size: 10px; color: var(--muted-light); flex-shrink: 0; }
.ftp-preview-md { padding: 16px; max-height: 65vh; overflow-y: auto; }
.ftp-preview-text { padding: 16px; max-height: 65vh; overflow-y: auto; white-space: pre-wrap; font-size: 13px; }

/* ── Focus visible ── */
.ftp-dir:focus-visible,
.ftp-file:focus-visible,
.ftp-rename-input:focus-visible,
.ftp-ref:focus-visible,
.ftp-fa-btn:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}
</style>
