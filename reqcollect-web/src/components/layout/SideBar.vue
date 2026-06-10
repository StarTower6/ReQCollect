<template>
  <aside class="sidebar" aria-label="会话导航">
    <!-- Brand -->
    <div class="sidebar-header">
      <div class="brand-row">
        <div class="brand-mark" aria-hidden="true"></div>
        <div class="brand-name">ReQCollect</div>
        <el-button text size="small" class="ws-mgr-btn" @click="goWorkspaceList">📁</el-button>
      </div>
      <!-- New chat -->
      <button class="sidebar-action" type="button" @click="handleNewChat">
        <span aria-hidden="true">＋</span>
        <span>新对话</span>
      </button>
      <!-- Import -->
      <button class="sidebar-action import-btn" type="button" @click="$emit('importDoc')">
        <span aria-hidden="true">📄</span>
        <span>导入记录</span>
      </button>
      <!-- Search -->
      <input class="sidebar-search"
             type="search"
             placeholder="搜索会话"
             v-model="sessionStore.searchQuery"
             @focus="onSearchFocus"
             @blur="onSearchBlur" />
    </div>

    <!-- New workspace button (只有在有 ws 时才显示) -->
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

defineEmits<{ importDoc: [] }>()

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

function handleNewChat() {
  // 如果有展开的 workspace 且不是未分类，新会话关联到它
  const expandedId = sessionStore.expandedWsId
  if (expandedId && expandedId !== '__ungrouped__') {
    sessionStore.setWorkspace(expandedId)
  } else {
    sessionStore.clearWorkspace()
  }
  const id = sessionStore.newSession(sessionStore.currentWorkspaceId || undefined)
  router.push(`/chat/${id}`)
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
  background: var(--panel, #fff);
  border-right: 1px solid var(--line, #f0f0f5);
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
  background: #409eff; border-radius: 6px;
  flex-shrink: 0;
}
.brand-name {
  flex: 1;
  font-weight: 600; font-size: 15px; color: #1d2129;
}
.ws-mgr-btn {
  font-size: 15px !important;
}

.sidebar-action {
  display: flex; align-items: center; gap: 6px;
  width: 100%; padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
  background: #f7f8fa;
  cursor: pointer; font-size: 13px; color: #4e5969;
  margin-bottom: 6px;
  transition: background 0.15s;
}
.sidebar-action:hover { background: #eef0f4; }

.sidebar-search {
  width: 100%; padding: 7px 10px;
  border-radius: 8px; border: 1px solid #e5e6eb;
  background: #f7f8fa;
  font-size: 13px; color: #1d2129;
  outline: none; transition: border-color 0.2s;
  box-sizing: border-box;
}
.sidebar-search:focus { border-color: #409eff; background: #fff; }
.sidebar-search::placeholder { color: #c0c4cc; }

/* ── Add workspace button ── */
.add-ws-btn {
  display: flex; align-items: center; gap: 6px;
  margin: 0 12px 8px; padding: 6px 12px;
  border-radius: 6px;
  border: 1px dashed #d9d9d9;
  background: none; font-size: 13px; color: #409eff;
  cursor: pointer; transition: border-color 0.15s;
  flex-shrink: 0;
}
.add-ws-btn:hover { border-color: #409eff; background: #f0f7ff; }

/* ── Tree area (scrollable) ── */
.sidebar-tree {
  flex: 1; overflow-y: auto;
  padding: 0 4px 8px;
}

.tree-empty {
  padding: 32px 16px; text-align: center;
  font-size: 13px; color: #86909c;
}
.tree-loading { padding: 8px; }
.tree-skeleton {
  height: 32px; margin-bottom: 4px;
  background: linear-gradient(90deg, #f0f0f5 25%, #e8e8ee 50%, #f0f0f5 75%);
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
.tree-header:hover { background: #f0f3f8; }
.tree-header.tree-expanded { color: #409eff; font-weight: 500; }

.tree-arrow { font-size: 10px; width: 14px; text-align: center;
  transition: transform 0.15s; color: #c0c4cc; flex-shrink: 0; }
.tree-arrow.arrow-open { transform: rotate(90deg); }

.tree-icon { font-size: 14px; flex-shrink: 0; }
.tree-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-badge {
  font-size: 11px; color: #4e5969;
  background: #f0f0f5; padding: 0 6px;
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
.session-leaf:hover { background: #f0f3f8; }
.session-leaf.active { background: #e8f3ff; color: #409eff; font-weight: 500; }

.leaf-bullet { font-size: 11px; flex-shrink: 0; opacity: 0.6; }
.leaf-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.leaf-meta { font-size: 11px; color: #c0c4cc; flex-shrink: 0; white-space: nowrap; }
.leaf-empty { padding: 8px 8px 8px 26px; font-size: 12px; color: #c0c4cc; }

/* ── Footer ── */
.sidebar-footer {
  border-top: 1px solid #f0f0f5;
  padding: 8px 12px; flex-shrink: 0;
}
.sidebar-link {
  display: block; padding: 6px 8px;
  border-radius: 6px; font-size: 13px;
  color: #4e5969; text-decoration: none;
  transition: background 0.12s;
}
.sidebar-link:hover { background: #f7f8fa; }
</style>
