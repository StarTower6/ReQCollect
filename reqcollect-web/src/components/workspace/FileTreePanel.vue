<template>
  <aside class="file-tree-panel">
    <!-- Header -->
    <div class="ftp-header">
      <span class="ftp-icon">📁</span>
      <span class="ftp-title">{{ wsName }}</span>
      <input ref="fileInput" type="file" hidden :accept="acceptStr" @change="handleUpload" />
      <el-button text size="small" @click="chooseUploadFolder || fileInput?.click()" :disabled="!workspaceId">+</el-button>
      <el-button text size="small" @click="showNewFolder = true" :disabled="!workspaceId">📂</el-button>
    </div>

    <!-- Loading / Empty / Tree -->
    <div class="ftp-body">
      <div v-if="loading" v-loading="true" style="height:200px" />
      <div v-else-if="!workspaceId" class="ftp-hint">请选择一个工作空间</div>
      <div v-else-if="files.length === 0 && allFolders.length === 0" class="ftp-hint">暂无文件</div>
      <div v-else class="ftp-tree">
        <!-- Render folder tree recursively -->
        <template v-for="fnode in folderTree" :key="fnode.folder.id">
          <FolderNode
            :node="fnode"
            :referenced-files="referencedFiles"
            :selected-path="selectedFilePath"
            :renaming-id="renamingId"
            :renaming-text="renamingText"
            :all-folders="allFolders"
            @toggle="fnode.expanded = !fnode.expanded"
            @preview="preview"
            @toggle-ref="toggleRef"
            @start-rename="startRename"
            @do-rename="doRename"
            @cancel-rename="renamingId = ''"
            @confirm-delete-folder="confirmDelete"
            @move-file="startMoveFile"
            @delete-file="confirmDeleteFile"
            @update:renaming-text="renamingText = $event"
          />
        </template>

        <!-- Root-level files (no folder) -->
        <div v-if="rootFiles.length > 0" class="ftp-root-separator" v-show="folderTree.length > 0">— 未分类 —</div>
        <div v-for="file in rootFiles" :key="file.path" class="ftp-file ftp-root-file"
          :class="{ 'ftp-referenced': isRef(file.path), 'ftp-selected': selectedFilePath === file.path }"
          @mouseenter="file._showActions = true" @mouseleave="file._showActions = false">
          <span class="ftp-ficon">{{ ficon(file.type) }}</span>
          <span class="ftp-fname" @click="preview(file)">{{ file.label }}</span>
          <span class="ftp-fsize" v-if="file.size">{{ fmtSize(file.size) }}</span>
          <span v-if="file.source === 'generated'" class="ftp-ai">AI</span>
          <span v-if="file.analysis?.tags?.length" class="ftp-tags" :title="file.analysis?.summary || ''">
            <span v-for="tag in file.analysis.tags.slice(0, 2)" :key="tag" class="ftp-tag">{{ tag }}</span>
          </span>
          <span v-if="file._showActions" class="ftp-file-actions">
            <button class="ftp-fa-btn" @click.stop="startMoveFile(file.path)" title="移动到文件夹">📁</button>
            <button class="ftp-fa-btn" @click.stop="confirmDeleteFile(file.path)" title="删除">🗑️</button>
          </span>
          <button v-if="file._showActions || isRef(file.path)" class="ftp-ref"
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

    <!-- Upload target folder picker -->
    <el-dialog v-model="showUploadPicker" title="上传到文件夹" width="360px" append-to-body>
      <p style="font-size:12px;color:#909399;margin-bottom:8px">选择上传文件的存放位置（可选）</p>
      <el-select v-model="uploadFolderId" placeholder="根目录（不放入文件夹）" clearable style="width:100%">
        <el-option v-for="f in allFolders" :key="f.id" :label="f.name" :value="f.id" />
      </el-select>
      <template #footer>
        <el-button @click="showUploadPicker = false">取消</el-button>
        <el-button type="primary" @click="doUploadWithFolder">上传</el-button>
      </template>
    </el-dialog>

    <!-- Move file to folder dialog -->
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

    <!-- Delete file confirm -->
    <el-dialog v-model="showDeleteFileConfirm" title="删除文件" width="360px" append-to-body>
      <p>确定删除文件「{{ deletingFilePath }}」？</p>
      <p style="font-size:12px;color:#909399">此操作不可恢复。</p>
      <template #footer>
        <el-button @click="showDeleteFileConfirm = false">取消</el-button>
        <el-button type="danger" @click="doDeleteFile">删除</el-button>
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
import { ref, computed, watch, nextTick, reactive, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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

// Upload folder picker
const showUploadPicker = ref(false)
const uploadFolderId = ref('')
const pendingUploadFile = ref<File | null>(null)
const chooseUploadFolder = ref(false)

// Move file
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

interface FolderItem {
  folder: any
  expanded: boolean
  files: any[]
  children: FolderItem[]
  fileCount: number
}

// Build flat list for select
function flattenFolders(f: any[], prefix = ''): any[] {
  const result: any[] = []
  for (const n of f) {
    result.push({ ...n, _path: prefix + n.name })
    if (n.children) result.push(...flattenFolders(n.children, prefix + n.name + ' / '))
  }
  return result
}

const expandedState = reactive<Record<string, boolean>>({})

// Build recursive folder tree
const folderTree = computed<FolderItem[]>(() => {
  return buildRecursive(rawFolders.value, '')
})

function buildRecursive(nodes: any[], parentId: string): FolderItem[] {
  const result: FolderItem[] = []
  const children = nodes.filter((n: any) => (n.parent_id || '') === parentId)
  for (const n of children) {
    const subs = buildRecursive(nodes, n.id)
    const dirFiles = files.value
      .filter((f: any) => f.folder === n.id)
      .map((f: any) => ({
        label: f.path, path: f.path, type: f.type, size: f.size,
        source: f.source, analysis: f.analysis, _showActions: false,
      }))
    if (expandedState[n.id] === undefined) expandedState[n.id] = true
    const subCount = subs.reduce((s: number, c: FolderItem) => s + c.fileCount, 0)
    result.push({
      folder: n,
      expanded: expandedState[n.id],
      files: dirFiles,
      children: subs,
      fileCount: dirFiles.length + subCount,
    })
  }
  return result
}

const rootFiles = computed(() => {
  return files.value
    .filter((f: any) => !f.folder)
    .map((f: any) => ({
      label: f.path, path: f.path, type: f.type, size: f.size,
      source: f.source, analysis: f.analysis, _showActions: false,
    }))
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

async function preview(p: { path: string; type?: string }) {
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
  // Show folder picker before upload
  pendingUploadFile.value = file
  uploadFolderId.value = ''
  showUploadPicker.value = true
  if (inp) inp.value = ''
}

async function doUploadWithFolder() {
  if (!props.workspaceId || !pendingUploadFile.value) return
  try {
    const result = await uploadWorkspaceFile(props.workspaceId, pendingUploadFile.value, localStorage.getItem('reqcollect_token') || '')
    // Assign to folder if selected
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

// ── FolderNode recursive component ──
// Registered as a local component for recursive rendering
const FolderNode = {
  name: 'FolderNode',
  props: {
    node: Object, referencedFiles: Array, selectedPath: String,
    renamingId: String, renamingText: String, allFolders: Array,
    depth: { type: Number, default: 0 },
  },
  emits: ['toggle', 'preview', 'toggle-ref', 'start-rename', 'do-rename', 'cancel-rename',
    'confirm-delete-folder', 'move-file', 'delete-file', 'update:renaming-text'],
  template: `
    <div>
      <div class="ftp-dir" :style="{ paddingLeft: (8 + depth * 16) + 'px' }"
        @click="$emit('toggle')"
        @mouseenter="sH = true" @mouseleave="sH = false">
        <span class="ftp-arrow" :class="{ open: node.expanded }">▶</span>
        <span>📂</span>
        <span class="ftp-name" v-if="renamingId !== node.folder.id" @dblclick="$emit('start-rename', node.folder)">{{ node.folder.name }}</span>
        <input v-else class="ftp-rename-input" :value="renamingText" @input="$emit('update:renaming-text', $event.target.value)"
          @keyup.enter="$emit('do-rename', node.folder)" @blur="$emit('do-rename', node.folder)" @keyup.escape="$emit('cancel-rename')" ref="ri" />
        <span class="ftp-badge">{{ node.fileCount }}</span>
        <span v-if="sH && renamingId !== node.folder.id" class="ftp-folder-actions">
          <button class="ftp-fa-btn" @click.stop="$emit('start-rename', node.folder)" title="重命名">✏️</button>
          <button class="ftp-fa-btn" @click.stop="$emit('confirm-delete-folder', node.folder)" title="删除">🗑️</button>
        </span>
      </div>
      <div v-if="node.expanded">
        <!-- Files in folder -->
        <div v-for="f in node.files" :key="f.path" class="ftp-file"
          :style="{ paddingLeft: (24 + depth * 16) + 'px' }"
          :class="{ 'ftp-referenced': referencedFiles.includes(f.path), 'ftp-selected': selectedPath === f.path }"
          @mouseenter="f._sA = true" @mouseleave="f._sA = false">
          <span class="ftp-ficon">{{ ficon(f.type) }}</span>
          <span class="ftp-fname" @click="$emit('preview', f)">{{ f.label }}</span>
          <span class="ftp-fsize" v-if="f.size">{{ fmtSize(f.size) }}</span>
          <span v-if="f.source === 'generated'" class="ftp-ai">AI</span>
          <span v-if="f.analysis?.tags?.length" class="ftp-tags" :title="f.analysis?.summary || ''">
            <span v-for="tag in f.analysis.tags.slice(0, 2)" :key="tag" class="ftp-tag">{{ tag }}</span>
          </span>
          <span v-if="f._sA" class="ftp-file-actions">
            <button class="ftp-fa-btn" @click.stop="$emit('move-file', f.path)" title="移动到文件夹">📁</button>
            <button class="ftp-fa-btn" @click.stop="$emit('delete-file', f.path)" title="删除">🗑️</button>
          </span>
          <button v-if="f._sA || referencedFiles.includes(f.path)" class="ftp-ref"
            @click.stop="$emit('toggle-ref', f.path)">
            {{ referencedFiles.includes(f.path) ? '✕' : '⊕' }}
          </button>
        </div>
        <!-- Sub-folders (recursive) -->
        <FolderNode v-for="child in node.children" :key="child.folder.id"
          :node="child" :referenced-files="referencedFiles" :selected-path="selectedPath"
          :renaming-id="renamingId" :renaming-text="renamingText" :all-folders="allFolders"
          :depth="depth + 1"
          @toggle="child.expanded = !child.expanded"
          @preview="$emit('preview', $event)"
          @toggle-ref="$emit('toggle-ref', $event)"
          @start-rename="$emit('start-rename', $event)"
          @do-rename="$emit('do-rename', $event)"
          @cancel-rename="$emit('cancel-rename')"
          @confirm-delete-folder="$emit('confirm-delete-folder', $event)"
          @move-file="$emit('move-file', $event)"
          @delete-file="$emit('delete-file', $event)"
          @update:renaming-text="$emit('update:renaming-text', $event)"
        />
      </div>
    </div>
  `,
  setup() {
    const sH = ref(false)
    return { sH, ficon, fmtSize }
  }
}

watch(() => props.workspaceId, () => {
  reloadAll()
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
.ftp-file { padding: 3px 8px 3px 24px; display: flex; align-items: center; gap: 4px; border-radius: 4px; cursor: pointer; }
.ftp-file:hover { background: #f0f3f8; }
.ftp-file.ftp-referenced { background: #ecf5ff; }
.ftp-file.ftp-selected { background: #e8f3ff; }
.ftp-root-file { padding-left: 8px; }
.ftp-root-separator { font-size: 11px; color: #c0c4cc; padding: 8px 8px 4px; text-align: center; border-top: 1px dashed #eee; margin-top: 4px; }
.ftp-ficon { font-size: 14px; flex-shrink: 0; }
.ftp-fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.ftp-fsize { font-size: 10px; color: #c0c4cc; flex-shrink: 0; }
.ftp-ai { font-size: 10px; color: #67c23a; background: #f0f9eb; padding: 0 4px; border-radius: 3px; flex-shrink: 0; }
.ftp-tags { display: inline-flex; gap: 2px; flex-shrink: 0; }
.ftp-tag { font-size: 10px; color: #909399; background: #f4f4f5; padding: 0 4px; border-radius: 3px; line-height: 16px; white-space: nowrap; }
.ftp-ref { font-size: 12px; border: none; background: none; cursor: pointer; color: #409eff; padding: 0 2px; flex-shrink: 0; }
.ftp-folder-actions { display: inline-flex; gap: 2px; flex-shrink: 0; margin-left: 4px; }
.ftp-file-actions { display: inline-flex; gap: 2px; flex-shrink: 0; }
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
