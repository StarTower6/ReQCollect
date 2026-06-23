<template>
  <AppLayout>
    <div class="ws-detail-page">
      <!-- Top bar -->
      <div class="detail-header">
        <div class="detail-header-left">
          <el-button text size="small" @click="goBack">← 工作空间</el-button>
          <h2>{{ workspace?.name || '加载中...' }}</h2>
          <el-tag v-if="workspace?.code" size="small" type="info">{{ workspace.code }}</el-tag>
        </div>
        <div class="detail-header-actions">
          <el-button size="small" @click="showEdit = true">编辑</el-button>
          <el-popconfirm title="确定删除此工作空间？" @confirm="handleDelete">
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>

      <p v-if="workspace?.description" class="ws-description">{{ workspace.description }}</p>

      <!-- Tabs -->
      <el-tabs v-model="activeTab" class="ws-tabs">
        <el-tab-pane label="会话列表" name="sessions">
          <div v-if="!workspace" v-loading="true" style="height:200px" />
          <div v-else class="session-section">
            <div class="section-actions">
              <span class="section-count">共 {{ sessions.length }} 个会话</span>
              <el-button size="small" type="primary" @click="goNewChat">+ 新建会话</el-button>
            </div>
            <el-table :data="sessions" v-loading="loadingSessions" stripe style="width:100%" empty-text="暂无会话">
              <el-table-column prop="project_name" label="需求名称" min-width="200" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="sufficiency_score" label="完整度" width="80">
                <template #default="{ row }">{{ Math.round((row.sufficiency_score || 0) * 100) }}%</template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button size="small" text type="primary" @click="goChat(row.session_id)">进入对话</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        <el-tab-pane label="Wiki 文库" name="wiki">
          <div v-if="!workspace" v-loading="true" style="height:200px" />
          <div v-else class="wiki-section">
            <div class="section-actions">
              <span class="section-count">共 {{ wikiPages.length }} 个页面</span>
              <el-button size="small" type="primary" @click="goNewWiki">+ 新建页面</el-button>
            </div>
            <el-table :data="wikiPages" v-loading="loadingWiki" stripe style="width:100%" empty-text="暂无 Wiki 页面">
              <el-table-column prop="title" label="页面标题" min-width="240" />
              <el-table-column label="最后编辑" width="180">
                <template #default="{ row }">
                  <span>{{ formatDate(row.updated_at) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button size="small" text type="primary" @click="goWikiView(row.id)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        <el-tab-pane label="📁 文件" name="files">
          <div v-if="!workspace" v-loading="true" style="height:200px" />
          <FileManager v-else :workspace-id="route.params.id as string" />
        </el-tab-pane>
        <el-tab-pane label="需求图谱" name="graph">
          <div v-if="!workspace" v-loading="true" style="height:400px" />
          <GraphView v-else-if="activeTab === 'graph'" :workspace-id="route.params.id as string" />
        </el-tab-pane>
      </el-tabs>

      <!-- Edit dialog -->
      <el-dialog v-model="showEdit" title="编辑工作空间" width="480px">
        <el-form :model="editForm" label-width="80px">
          <el-form-item label="项目名称">
            <el-input v-model="editForm.name" />
          </el-form-item>
          <el-form-item label="项目编码">
            <el-input v-model="editForm.code" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="editForm.description" type="textarea" :rows="3" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showEdit = false">取消</el-button>
          <el-button type="primary" :loading="editing" @click="handleEdit">保存</el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchWorkspace, updateWorkspace, deleteWorkspace, fetchWorkspaceSessions } from '@/api/workspace'
import { fetchWikiPages } from '@/api/wiki'
import type { WikiPage } from '@/api/wiki'
import GraphView from '@/views/wiki/GraphView.vue'
import FileManager from '@/components/workspace/FileManager.vue'
import { useSessionStore } from '@/stores/session'
import { useChatStore } from '@/stores/chat'
import { useProfileStore } from '@/stores/profile'
import AppLayout from '@/components/layout/AppLayout.vue'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
const chatStore = useChatStore()
const profileStore = useProfileStore()

const workspace = ref<any>(null)
const sessions = ref<any[]>([])
const loadingSessions = ref(false)
const activeTab = ref('sessions')
const showEdit = ref(false)
const editing = ref(false)
const editForm = reactive({ name: '', code: '', description: '' })
const wikiPages = ref<WikiPage[]>([])
const loadingWiki = ref(false)

watch(activeTab, (tab) => {
  if (tab === 'wiki' && wikiPages.value.length === 0) {
    loadWiki()
  }
})

function statusType(s: string) {
  return { mining: 'warning', generating: 'primary', complete: 'success' }[s] || 'info'
}
function statusLabel(s: string) {
  return { mining: '收集中', generating: '生成中', complete: '已完成' }[s] || s
}

function goBack() { router.push('/workspaces') }
function goChat(sid: string) {
  sessionStore.setCurrent(sid)
  router.push(`/chat/${sid}`)
}
function goNewChat() {
  const wsId = route.params.id as string
  sessionStore.setWorkspace(wsId)
  const sid = sessionStore.newSession(wsId)
  router.push(`/chat/${sid}`)
}

async function load() {
  const id = route.params.id as string
  try {
    workspace.value = await fetchWorkspace(id)
    editForm.name = workspace.value.name
    editForm.code = workspace.value.code || ''
    editForm.description = workspace.value.description || ''
  } catch { ElMessage.error('加载工作空间失败') }

  loadingSessions.value = true
  try {
    sessions.value = await fetchWorkspaceSessions(id)
  } catch {}
  finally { loadingSessions.value = false }
}

async function handleEdit() {
  editing.value = true
  try {
    await updateWorkspace(workspace.value.id, { ...editForm })
    ElMessage.success('已更新')
    showEdit.value = false
    await load()
  } catch (e: any) { ElMessage.error(e.message || '更新失败') }
  finally { editing.value = false }
}

async function handleDelete() {
  try {
    await deleteWorkspace(workspace.value.id)
    ElMessage.success('已删除')
    router.push('/workspaces')
  } catch (e: any) { ElMessage.error(e.message || '删除失败') }
}

async function loadWiki() {
  const id = route.params.id as string
  loadingWiki.value = true
  try {
    wikiPages.value = await fetchWikiPages(id)
  } catch {}
  finally { loadingWiki.value = false }
}

function goNewWiki() {
  const wsId = route.params.id as string
  router.push(`/workspace/${wsId}/wiki/new`)
}

function goWikiView(pageId: string) {
  const wsId = route.params.id as string
  router.push(`/workspace/${wsId}/wiki/${pageId}`)
}

function formatDate(d: string) {
  if (!d) return ''
  try { return new Date(d).toLocaleString('zh-CN') } catch { return '' }
}

onMounted(load)
</script>

<style scoped>
.ws-detail-page { padding: 24px; }
.detail-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 12px; gap: 12px; }
.detail-header-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.detail-header-left h2 { margin: 0; font-size: 20px; font-weight: 600; }
.detail-header-actions { display: flex; gap: 8px; flex-shrink: 0; }
.ws-description { color: var(--muted); font-size: 14px; margin: 0 0 20px; }
.ws-tabs { margin-top: 8px; }
.section-actions { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.section-count { font-size: 13px; color: var(--muted); }
</style>
