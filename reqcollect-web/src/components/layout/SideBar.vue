<template>
  <aside class="sidebar" aria-label="会话导航">
    <!-- Brand + Search only -->
    <div class="sidebar-header">
      <div class="brand-row">
        <div class="brand-mark" aria-hidden="true"></div>
        <div class="brand-name">ReQCollect</div>
        <el-button text size="small" class="ws-mgr-btn" @click="goWorkspaceList">📁</el-button>
      </div>
      <input class="sidebar-search"
             type="search"
             placeholder="搜索会话"
             v-model="sessionStore.searchQuery"
             @focus="onSearchFocus"
             @blur="onSearchBlur" />
    </div>

    <!-- New workspace button (only when workspaces exist) -->
    <button v-if="sessionStore.workspaces.length > 0"
            class="add-ws-btn" type="button" @click="goWorkspaceList">
      ＋ 新建工作空间
    </button>

    <!-- Tree -->
    <div class="sidebar-tree" id="session-list">
      <!-- 空状态 -->
      <div v-if="sessionStore.treeData.length === 0 && !loading" class="tree-empty">
        {{ sessionStore.searchQuery ? '未找到匹配的会话' : '暂无会话' }}
      </div>
      <!-- 加载中占位 -->
      <div v-if="loading" class="tree-loading">
        <div v-for="i in 3" :key="i" class="tree-skeleton"></div>
      </div>

      <template v-for="node in sessionStore.treeData" :key="node.id">
        <!-- Workspace / Ungrouped node -->
        <div class="tree-node">
          <div class="tree-header"
               :class="{ 'tree-expanded': node.expanded, 'tree-active': node.id === sessionStore.expandedWsId }"
               @click="onToggle(node)">
            <span class="tree-arrow" :class="{ 'arrow-open': node.expanded }">▶</span>
            <span class="tree-icon">{{ node.type === 'ungrouped' ? '📋' : '📁' }}</span>
            <span class="tree-label">{{ node.name }}</span>
            <span class="tree-badge">{{ node.count }}</span>
          </div>
          <!-- Children -->
          <div class="tree-children" :class="{ 'children-open': node.expanded, 'children-closed': !node.expanded }">
            <!-- Inline action buttons for workspace nodes -->
            <div v-if="node.expanded && node.type === 'workspace'" class="inline-actions">
              <div class="inline-action" @click="handleNewChatInWs(node.id)">
                ＋ 新建会话
              </div>
              <div class="inline-action" @click="handleImportInWs(node.id)">
                📄 导入需求文档
              </div>
            </div>
            <!-- Inline new chat for ungrouped -->
            <div v-if="node.expanded && node.type === 'ungrouped'" class="inline-actions">
              <div class="inline-action" @click="handleNewChatInWs(null)">
                ＋ 新建会话
              </div>
            </div>
            <div v-for="s in node.sessions"
                 :key="s.session_id"
                 class="session-leaf"
                 :class="{ active: s.session_id === sessionStore.currentId }"
                 @click="switchTo(s.session_id)">
              <span class="leaf-bullet">💬</span>
              <span class="leaf-name">{{ s.project_name || '未命名项目' }}</span>
              <span class="leaf-meta">{{ formatDate(s.updated_at) }}</span>
            </div>
            <!-- 空子节点提示 -->
            <div v-if="node.expanded && node.sessions.length === 0" class="leaf-empty">
              暂无会话
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Footer -->
    <div class="sidebar-footer">
      <router-link class="sidebar-link" to="/dashboard">📊 数据看板</router-link>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()
const router = useRouter()
const loading = ref(false)

const emit = defineEmits<{ importDoc: [wsId: string] }>()

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  try {
    const now = Date.now()
    const d = new Date(dateStr).getTime()
    const diff = now - d
    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
    if (diff < 604800000) return Math.floor(diff / 86400000) + '天前'
    return new Date(dateStr).toLocaleDateString('zh-CN')
  } catch { return '' }
}

function onToggle(node: any) {
  sessionStore.toggleWorkspace(node.id)
}

function switchTo(sid: string) {
  sessionStore.setCurrent(sid)
  router.push(`/chat/${sid}`)
}

function handleNewChatInWs(wsId: string | null) {
  if (wsId) {
    sessionStore.setWorkspace(wsId)
  } else {
    sessionStore.clearWorkspace()
  }
  const id = sessionStore.newSession(sessionStore.currentWorkspaceId || undefined)
  router.push(`/chat/${id}`)
}

function handleImportInWs(wsId: string) {
  if (wsId) {
    sessionStore.setWorkspace(wsId)
  }
  emit('importDoc', wsId)
}

function goWorkspaceList() {
  router.push('/workspaces')
}

function onSearchFocus() {
  sessionStore.saveExpandState()
}

function onSearchBlur() {
  // no-op: restoreExpandState is handled by watch on searchQuery
}

watch(() => sessionStore.searchQuery, (val) => {
  if (!val.trim()) {
    sessionStore.restoreExpandState()
  }
})

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      sessionStore.load(),
      sessionStore.loadWorkspaces(),
    ])
  } catch { /* silent */ }
  finally { loading.value = false }
})
</script>

<style scoped>
/* ── Sidebar base ── */
.sidebar {
  width: 280px; min-width: 280px;
  display: flex; flex-direction: column;
  background: var(--panel);
  border-right: 1px solid var(--line);
  height: 100vh; overflow: hidden;
}

/* ── Header area ── */
.sidebar-header {
  padding: 16px 12px 8px;
  flex-shrink: 0;
}

.brand-row {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px;
}
.brand-mark {
  width: 24px; height: 24px;
  background: var(--brand); border-radius: 6px;
  flex-shrink: 0;
}
.brand-name {
  flex: 1;
  font-weight: 600; font-size: 15px; color: var(--text);
}
.ws-mgr-btn {
  font-size: 15px !important;
}

.sidebar-search {
  width: 100%; padding: 7px 10px;
  border-radius: 8px; border: 1px solid var(--line);
  background: var(--sidebar);
  font-size: 13px; color: var(--text);
  outline: none; transition: border-color 0.2s;
  box-sizing: border-box;
}
.sidebar-search:focus { border-color: var(--brand); background: var(--panel); }
.sidebar-search::placeholder { color: var(--muted-light); }

/* ── Add workspace button ── */
.add-ws-btn {
  display: flex; align-items: center; gap: 6px;
  margin: 0 12px 8px; padding: 6px 12px;
  border-radius: 6px;
  border: 1px dashed var(--line);
  background: none; font-size: 13px; color: var(--brand);
  cursor: pointer; transition: border-color 0.15s;
  flex-shrink: 0;
}
.add-ws-btn:hover { border-color: var(--brand); background: var(--brand-soft); }

/* ── Tree area (scrollable) ── */
.sidebar-tree {
  flex: 1; overflow-y: auto;
  padding: 0 4px 8px;
}

.tree-empty {
  padding: 32px 16px; text-align: center;
  font-size: 13px; color: var(--muted);
}
.tree-loading { padding: 8px; }
.tree-skeleton {
  height: 32px; margin-bottom: 4px;
  background: linear-gradient(90deg, var(--line) 25%, var(--sidebar-hover) 50%, var(--line) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 6px;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ── Tree node ── */
.tree-node { margin-bottom: 1px; }

.tree-header {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 8px; border-radius: 6px;
  cursor: pointer; font-size: 13px;
  transition: background 0.12s;
  user-select: none;
}
.tree-header:hover { background: var(--sidebar-hover); }
.tree-header.tree-expanded { color: var(--brand); font-weight: 500; }

.tree-arrow { font-size: 10px; width: 14px; text-align: center;
  transition: transform 0.15s; color: var(--muted-light); flex-shrink: 0; }
.tree-arrow.arrow-open { transform: rotate(90deg); }

.tree-icon { font-size: 14px; flex-shrink: 0; }
.tree-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-badge {
  font-size: 11px; color: var(--muted);
  background: var(--line); padding: 0 6px;
  border-radius: 8px; line-height: 18px;
  flex-shrink: 0;
}

/* ── Tree children ── */
.tree-children { overflow: hidden; transition: max-height 0.2s ease; }
.tree-children.children-open { max-height: 400px; }
.tree-children.children-closed { max-height: 0; }

.session-leaf {
  display: flex; align-items: center; gap: 4px;
  padding: 5px 8px 5px 26px;
  border-radius: 6px; cursor: pointer;
  font-size: 13px; transition: background 0.12s;
}
.session-leaf:hover { background: var(--sidebar-hover); }
.session-leaf.active { background: var(--brand-soft); color: var(--brand); font-weight: 500; }

.leaf-bullet { font-size: 11px; flex-shrink: 0; opacity: 0.6; }
.leaf-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.leaf-meta { font-size: 11px; color: var(--muted-light); flex-shrink: 0; white-space: nowrap; }
.leaf-empty { padding: 8px 8px 8px 26px; font-size: 12px; color: var(--muted-light); }

/* ── Inline action buttons inside workspace nodes ── */
.inline-actions {
  padding: 4px 0 4px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.inline-action {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 8px; border-radius: 6px;
  font-size: 12px; color: var(--brand);
  cursor: pointer; user-select: none;
  transition: background 0.12s;
}
.inline-action:hover { background: var(--brand-soft); }

/* ── Footer ── */
.sidebar-footer {
  border-top: 1px solid var(--line);
  padding: 8px 12px; flex-shrink: 0;
}
.sidebar-link {
  display: block; padding: 6px 8px;
  border-radius: 6px; font-size: 13px;
  color: var(--muted); text-decoration: none;
  transition: background 0.12s;
}
.sidebar-link:hover { background: var(--sidebar); }

/* ── Focus visible ── */
.sidebar-search:focus-visible,
.add-ws-btn:focus-visible,
.tree-header:focus-visible,
.session-leaf:focus-visible,
.inline-action:focus-visible,
.sidebar-link:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}
</style>
