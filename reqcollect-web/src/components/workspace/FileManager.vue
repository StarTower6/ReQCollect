<template>
  <div class="file-manager">
    <!-- Top bar -->
    <div class="fm-toolbar">
      <div class="fm-toolbar-left">
        <span class="fm-count" v-if="files.length">共 {{ files.length }} 个文件</span>
        <span class="fm-count" v-else>暂无文件</span>
      </div>
      <div class="fm-toolbar-actions">
        <el-upload
          :action="uploadUrl"
          :headers="uploadHeaders"
          :show-file-list="false"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :before-upload="beforeUpload"
          :disabled="uploading"
          accept=".md,.txt,.json,.yaml,.yml,.docx,.xlsx"
        >
          <el-button size="small" type="primary" :loading="uploading">
            {{ uploading ? '上传中...' : '+ 上传文件' }}
          </el-button>
        </el-upload>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!loading && files.length === 0" class="fm-empty">
      <div class="fm-empty-icon">📁</div>
      <p>暂无文件，请上传 Markdown、Office 文档</p>
      <p class="fm-empty-hint">支持 .md .txt .docx .xlsx 等格式</p>
    </div>

    <!-- File table -->
    <el-table
      v-else
      :data="files"
      v-loading="loading"
      stripe
      style="width:100%"
      size="small"
      empty-text="暂无文件"
    >
      <el-table-column label="文件名" min-width="240">
        <template #default="{ row }">
          <div class="fm-file-cell">
            <span class="fm-file-icon">{{ fileIcon(row.type) }}</span>
            <span class="fm-file-name">{{ row.path }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="70">
        <template #default="{ row }">
          <el-tag size="small">{{ row.type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="80">
        <template #default="{ row }">{{ fmtSize(row.size) }}</template>
      </el-table-column>
      <el-table-column label="来源" width="80">
        <template #default="{ row }">
          <el-tag :type="sourceTagType(row.source)" size="small">{{ sourceLabel(row.source) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上传时间" width="170">
        <template #default="{ row }">{{ fmtDate(row.uploaded_at) }}</template>
      </el-table-column>
      <el-table-column label="摘要" min-width="200">
        <template #default="{ row }">
          <span class="fm-summary">{{ row.summary || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="previewFile(row)">预览</el-button>
          <el-popconfirm title="确定删除此文件？" @confirm="handleDelete(row)">
            <template #reference>
              <el-button text size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Preview dialog -->
    <el-dialog v-model="previewVisible" :title="previewFileTitle" width="800px" top="5vh">
      <div v-if="previewLoading" v-loading="true" style="height:300px" />
      <div v-else class="fm-preview">
        <div class="fm-preview-meta">
          <span>大小: {{ fmtSize(previewContent?.size || 0) }}</span>
          <span v-if="previewContent?.truncated" class="fm-truncated-warn">
            ⚠ 文件过长，仅显示前 {{ previewMaxChars }} 字符
          </span>
        </div>
        <div v-if="previewContent?.type === 'md'" class="fm-preview-md" v-html="renderedMarkdown" />
        <pre v-else class="fm-preview-text">{{ previewContent?.text || '' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { fetchWorkspaceFiles, readWorkspaceFile, deleteWorkspaceFile } from '@/api/workspace_files'
import type { WorkspaceFile } from '@/api/workspace_files'

const props = defineProps<{ workspaceId: string }>()

const files = ref<WorkspaceFile[]>([])
const loading = ref(false)
const uploading = ref(false)

const previewVisible = ref(false)
const previewLoading = ref(false)
const previewFileTitle = ref('')
const previewContent = ref<any>(null)
const previewMaxChars = 8000

const token = computed(() => localStorage.getItem('reqcollect_token') || '')
const uploadUrl = computed(() => `/api/workspaces/${props.workspaceId}/files/upload`)
const uploadHeaders = computed(() => ({ Authorization: `Bearer ${token.value}` }))

const renderedMarkdown = computed(() => {
  if (!previewContent.value?.text) return ''
  return marked.parse(previewContent.value.text) as string
})

onMounted(loadFiles)

async function loadFiles() {
  loading.value = true
  try {
    files.value = await fetchWorkspaceFiles(props.workspaceId)
  } catch (e: any) {
    ElMessage.error('加载文件列表失败')
  } finally {
    loading.value = false
  }
}

function beforeUpload(file: File) {
  const allowed = ['.md', '.txt', '.json', '.yaml', '.yml', '.docx', '.xlsx']
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!allowed.includes(ext)) {
    ElMessage.error(`不支持的文件类型 ${ext}`)
    return false
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件超过 10MB 限制')
    return false
  }
  uploading.value = true
  return true
}

function onUploadSuccess(res: any) {
  uploading.value = false
  if (res?.success) {
    ElMessage.success('文件上传成功')
    loadFiles()
  } else {
    ElMessage.error(res?.detail || '上传失败')
  }
}

function onUploadError() {
  uploading.value = false
  ElMessage.error('上传失败')
}

async function handleDelete(row: WorkspaceFile) {
  try {
    await deleteWorkspaceFile(props.workspaceId, row.path)
    ElMessage.success('已删除')
    loadFiles()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

async function previewFile(row: WorkspaceFile) {
  previewVisible.value = true
  previewLoading.value = true
  previewFileTitle.value = row.path
  previewContent.value = null
  try {
    previewContent.value = await readWorkspaceFile(
      props.workspaceId, row.path, previewMaxChars
    )
  } catch (e: any) {
    ElMessage.error('读取文件失败')
  } finally {
    previewLoading.value = false
  }
}

function fileIcon(type: string): string {
  const icons: Record<string, string> = {
    md: '📝', txt: '📄', json: '📋', yaml: '⚙️', yml: '⚙️',
    docx: '📘', xlsx: '📊',
  }
  return icons[type] || '📄'
}

function fmtSize(size: number): string {
  if (size < 1024) return `${size}B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)}KB`
  return `${(size / 1024 / 1024).toFixed(1)}MB`
}

function sourceTagType(source: string) {
  return { upload: '', generated: 'success', linked: 'info' }[source] || 'info'
}

function sourceLabel(source: string) {
  return { upload: '上传', generated: 'AI生成', linked: '同步' }[source] || source
}

function fmtDate(d: string) {
  if (!d) return ''
  try { return new Date(d).toLocaleString('zh-CN') } catch { return '' }
}
</script>

<style scoped>
.file-manager { padding: 0; }
.fm-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; gap: 12px; }
.fm-toolbar-left { display: flex; align-items: center; gap: 8px; }
.fm-count { font-size: 13px; color: #86909c; }
.fm-file-cell { display: flex; align-items: center; gap: 6px; }
.fm-file-icon { font-size: 18px; }
.fm-file-name { font-size: 14px; }
.fm-summary { font-size: 12px; color: #86909c; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-block; }
.fm-empty { text-align: center; padding: 60px 20px; color: #86909c; }
.fm-empty-icon { font-size: 48px; margin-bottom: 12px; }
.fm-empty-hint { font-size: 12px; color: #c9cdd4; }
.fm-preview-meta { margin-bottom: 12px; font-size: 12px; color: #86909c; display: flex; gap: 16px; }
.fm-truncated-warn { color: #fa8c16; }
.fm-preview-md { padding: 16px; background: #f7f8fa; border-radius: 4px; max-height: 70vh; overflow-y: auto; }
.fm-preview-text { padding: 16px; background: #f7f8fa; border-radius: 4px; max-height: 70vh; overflow-y: auto; white-space: pre-wrap; font-size: 13px; }
</style>
