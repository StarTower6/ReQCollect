# SideBar 树状改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 SideBar 从扁平会话列表改造为树状工作空间 + 会话管理结构，互斥展开

**Architecture:** session store 扩展为缓存 workspaces 列表并提供 treeData 计算属性；SideBar.vue 全部重写为树状渲染；AppLayout.vue 微调加载逻辑

**Tech Stack:** Vue 3 + TypeScript + Pinia + Element Plus

---

### Task 1: session store — 扩展状态和计算属性

**Files:**
- Modify: `reqcollect-web/src/stores/session.ts`

- [ ] **Step 1: 新增导入和类型**

在现有 import 后添加：
```typescript
import { fetchWorkspaces } from '@/api/workspace'
```

- [ ] **Step 2: 新增 store 状态**

在 `const searchQuery = ref('')` 之后新增：
```typescript
const expandedWsId = ref<string | null>(null)  // 当前展开的 workspace id
const savedExpandedWsId = ref<string | null>(null) // 搜索前保存的展开状态
const workspaces = ref<any[]>([])
```

- [ ] **Step 3: 重构 treeData 计算属性**

替换当前 `filteredSessions` 的 `computed` 实现为：

```typescript
const filteredSessions = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  let result = sessions.value
  if (!q) return result
  return result.filter(s =>
    (s.project_name || '').toLowerCase().includes(q) ||
    (s.session_id || '').toLowerCase().includes(q)
  )
})

const treeData = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const isSearching = !!q
  const nodes: Array<{
    type: 'workspace'
    id: string
    name: string
    count: number
    sessions: Session[]
    expanded: boolean
  } | {
    type: 'ungrouped'
    id: '__ungrouped__'
    name: string
    count: number
    sessions: Session[]
    expanded: boolean
  }> = []

  // 1. Workspace nodes
  for (const ws of workspaces.value) {
    const wsSessions = sessions.value.filter(s => s.workspace_id === ws.id)
    // 搜索模式下不过滤空节点
    if (!isSearching && wsSessions.length === 0) continue

    const match = isSearching ? wsSessions.filter(s => matchesSearch(s, q)).length > 0 : true
    if (isSearching && !match && !(ws.name || '').toLowerCase().includes(q)) continue

    nodes.push({
      type: 'workspace',
      id: ws.id,
      name: ws.name,
      count: wsSessions.length,
      sessions: isSearching ? wsSessions.filter(s => matchesSearch(s, q)) : wsSessions,
      expanded: isSearching || expandedWsId.value === ws.id,
    })
  }

  // 2. Ungrouped sessions
  const ungrouped = sessions.value.filter(s => !s.workspace_id)
  if (ungrouped.length > 0) {
    nodes.push({
      type: 'ungrouped',
      id: '__ungrouped__',
      name: '未分类会话',
      count: ungrouped.length,
      sessions: isSearching ? ungrouped.filter(s => matchesSearch(s, q)) : ungrouped,
      expanded: true,  // 默认展开
    })
  }

  return nodes

  function matchesSearch(s: Session, query: string): boolean {
    return (s.project_name || '').toLowerCase().includes(query) ||
           (s.session_id || '').toLowerCase().includes(query)
  }
})
```

- [ ] **Step 4: 新增 loadWorkspaces 和 toggleWorkspace**

在 `load` 函数后新增：
```typescript
async function loadWorkspaces() {
  try {
    workspaces.value = await fetchWorkspaces()
  } catch {
    // 静默降级
  }
}

function toggleWorkspace(id: string) {
  if (expandedWsId.value === id) {
    // 点击已展开的 → 全部收起
    expandedWsId.value = null
  } else {
    expandedWsId.value = id
  }
}

function saveExpandState() {
  savedExpandedWsId.value = expandedWsId.value
}

function restoreExpandState() {
  if (savedExpandedWsId.value) {
    expandedWsId.value = savedExpandedWsId.value
    savedExpandedWsId.value = null
  }
}
```

> 注意：treeData 中的 `matchesSearch` 函数是内部函数，不需要单独暴露。

- [ ] **Step 5: 更新 return 语句**

```typescript
return {
  sessions, currentId, currentWorkspaceId, searchQuery,
  filteredSessions, treeData,   // treeData 新增
  workspaces,                   // workspaces 列表新增
  expandedWsId,                 // 展开状态新增
  load, loadWorkspaces,         // loadWorkspaces 新增
  setCurrent, newSession, remove, setWorkspace, clearWorkspace,
  toggleWorkspace,              // toggleWorkspace 新增
  saveExpandState, restoreExpandState,  // 搜索展开恢复新增
}
```

- [ ] **Step 6: 确认当前 filteredSessions 的使用情况**

搜索 `filteredSessions` 的使用：
```bash
grep -rn 'filteredSessions' reqcollect-web/src/ --include="*.vue" --include="*.ts"
```

如果只有 SideBar.vue 使用，它的角色由 treeData 取代；否则保留 filteredSessions 作为扁平备选。

- [ ] **Step 7: 提交**

```bash
git add reqcollect-web/src/stores/session.ts
git commit -m "feat: extend session store with workspace tree data and expand state"
```

---

### Task 2: SideBar.vue — 树状渲染

**Files:**
- Modify: `reqcollect-web/src/components/layout/SideBar.vue`（全部重写）

- [ ] **Step 1: 重写模板为树状结构**

```vue
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
```

- [ ] **Step 2: 重写 script 部分**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
  if (node.id === '__ungrouped__') {
    // 未分类也允许展开/折叠
    sessionStore.toggleWorkspace(node.id)
    return
  }
  sessionStore.toggleWorkspace(node.id)
}

function switchTo(sid: string) {
  sessionStore.setCurrent(sid)
  router.push(`/chat/${sid}`)
}

function handleNewChat() {
  // 如果有展开的 workspace，新会话关联到它
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
  // 搜索时保存当前展开状态
  sessionStore.saveExpandState()
  // 搜索时展开所有节点由 treeData computed 自动处理（搜索模式下所有 expanded=true）
}

function onSearchBlur() {
  // 搜索框失焦时不立即恢复——等用户清除搜索后恢复
  // 恢复逻辑在 watch searchQuery 中处理
}

// Watch search query: 清除时恢复展开状态
import { watch } from 'vue'
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
```

- [ ] **Step 3: 替换完整 CSS 样式**

新增完整的树状样式。保留现有 `.sidebar` 基础布局（flex column），替换内部样式：

```css
/* ── Sidebar base (keep existing) ── */
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

/* ── Node header ── */
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

/* ── Children (animatable) ── */
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
```

- [ ] **Step 4: 移除所有当前 SideBar 的 `<style scoped>` 并将新样式写入**

用上面的样式完全替换 `SideBar.vue` 中的 `<style scoped>` 块。

- [ ] **Step 5: 提交**

```bash
git add reqcollect-web/src/components/layout/SideBar.vue
git commit -m "feat: rewrite SideBar as tree structure with workspace expand/collapse"
```

---

### Task 3: AppLayout.vue — 调整加载和新建逻辑

**Files:**
- Modify: `reqcollect-web/src/components/layout/AppLayout.vue`

- [ ] **Step 1: 移除 onMounted 中对 sessionStore.load() 的显式调用**

当前 AppLayout 没有显式 `onMounted` 调用 `sessionStore.load()`。确认：
```bash
grep -n 'onMounted\|sessionStore.load' reqcollect-web/src/components/layout/AppLayout.vue
```

如果 AppLayout 的 `onMounted` 中已有 sessionStore.load，移除它（SideBar 自己会加载）。

- [ ] **Step 2: 确保 handleNewChat 不传 expandedWsId（已由 SideBar 自我管理）**

handleNewChat 已经在 AppLayout 中，但 SideBar.vue 自己也有了一个 handleNewChat。
我们需要**去除 AppLayout 的 handleNewChat 事件处理**，让 SideBar 完全接管。

修改 AppLayout.vue：
```diff
-   <SideBar @new-chat="handleNewChat" @import-doc="showImport = true" />
+   <SideBar @import-doc="showImport = true" />
```

移除：
```diff
- async function handleNewChat() {
-   sessionStore.clearWorkspace()
-   const id = sessionStore.newSession()
-   profileStore.clear()
-   router.push(`/chat/${id}`)
- }
```

同时移除 AppLayout 中不再需要的 `router`, `sessionStore`, `profileStore` 相关引用（如果 handleNewChat 是唯一使用处）。

- [ ] **Step 3: 提交**

```bash
git add reqcollect-web/src/components/layout/AppLayout.vue
git commit -m "refactor: remove AppLayout newChat handler — SideBar now self-manages"
```

---

### Task 4: WorkspaceDetail.vue — 清理旧逻辑

**Files:**
- Modify: `reqcollect-web/src/views/WorkspaceDetail.vue`

- [ ] **Step 1: 简化 goNewChat（SideBar 已接管 workspace 上下文）**

```diff
 function goNewChat() {
   const wsId = route.params.id as string
-  sessionStore.setWorkspace(wsId)
-  const sid = sessionStore.newSession()
+  sessionStore.setWorkspace(wsId)
+  const sid = sessionStore.newSession(wsId)
   router.push(`/chat/${sid}`)
 }
```

注意：这里仍然保留 setWorkspace 是为了 SideBar 的 expandedWsId 状态也能正确更新。
但 WorkspaceDetail 的 goNewChat 仍需要 setWorkspace 来让 SideBar 关联新会话。

- [ ] **Step 2: 提交**

```bash
git add reqcollect-web/src/views/WorkspaceDetail.vue
git commit -m "refactor: WorkspaceDetail goNewChat uses newSession(wsId)"
```

---

### Task 5: 前端构建 + 验证

**Files:**
- Modify: `reqcollect-web/`

- [ ] **Step 1: 检查 TypeScript 没有错误**

```bash
cd reqcollect-web && npx vue-tsc --noEmit 2>&1 | head -30
```

如果 `vue-tsc` 不可用或太慢，跳过这一步，直接构建。

- [ ] **Step 2: 构建前端**

```bash
cd reqcollect-web && npm run build 2>&1
```

- [ ] **Step 3: 集成测试**

启动 Docker 并确认：
1. 打开 `http://localhost:9900` → 登录 → 看到树状 SideBar 渲染
2. 有工作空间数据时，点击展开/折叠工作空间
3. 点击会话跳转到聊天页
4. 搜索框输入关键词 → 展开所有节点 + 过滤
5. 清除搜索 → 恢复之前的展开状态
6. 点击「➕ 新建工作空间」→ 跳转到 /workspaces
7. 未分类会话节点显示 workspace_id 为空的会话
8. 无工作空间时「➕ 新建工作空间」按钮不显示

- [ ] **Step 4: 提交**

```bash
git add -A && git commit -m "feat: SideBar tree structure with workspace expand/collapse"

# 注意：如果前面任务已经独立提交，这里只需 git add 构建产物
git add reqcollect-web/dist/ -f
git commit -m "build: rebuild frontend with sidebar tree"
```
