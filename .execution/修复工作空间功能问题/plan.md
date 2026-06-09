# Plan: 修复工作空间功能问题

## 1. 任务理解

修复在之前评估中发现的 8 个工作空间功能问题，按 P0→P1→P2 优先级排序。
所有修复必须 Surgical（只改必要代码），不引入新功能。

## 2. 改动清单

| 文件 | 改动 | 问题编号 |
|------|------|---------|
| `app/db/models.py` | Session.to_dict() 添加 workspace_id | P0-1 |
| `app/db/__init__.py` | DataStore.list_sessions 添加 workspace_id 参数 | P0-2 |
| `app/db/compat.py` | FileDataStore.list_sessions 支持 workspace_id 过滤；delete_workspace 清理 session | P0-2, P1-4 |
| `app/db/repository.py` | MySQLDataStore.list_sessions 支持 workspace_id 过滤；delete_workspace 清理 session | P0-2, P1-4 |
| `app/api/workspace.py` | ws_update 修复空字符串更新；ws_sessions 用 DataStore 过滤 | P1-3, P0-2 |
| `app/services/pm_agent_service.py` | list_sessions 透传 workspace_id | P0-2 |
| `reqcollect-web/src/stores/session.ts` | newSession 接受可选 workspaceId；currentWorkspaceId 持久化 | P1-1, P2-1 |
| `reqcollect-web/src/views/ChatView.vue` | 新建会话传 workspace_id | P1-1 |
| `reqcollect-web/src/components/layout/SideBar.vue` | 按 workspace 筛选会话列表 | P1-6 |

## 3. 验收标准

- [ ] P0: Session.to_dict() 返回的字典包含 workspace_id 字段 → MySQL 下 workspace 详情页会话列表正常显示
- [ ] P0: DataStore.list_sessions 支持按 workspace_id 过滤 → ws_sessions 不再全表扫描
- [ ] P0: ws_sessions 改用 DataStore 过滤 → 不需要在 API 层遍历过滤
- [ ] P1: SideBar 新建的会话关联到当前 workspace（若在 workspace 上下文中）
- [ ] P1: 删除 workspace 时清理关联 session 的 workspace_id（置空而非删除 session）
- [ ] P1: ws_update 支持将 code/description 改回空字符串
- [ ] P1: 刷新页面后 workspace 上下文不丢失（localStorage 持久化）
- [ ] P2: SideBar 会话列表按 workspace 筛选
- [ ] P2: workspace_id 默认值统一为 `""`

## 4. 风险与依赖

- **无风险**: 所有修改都是 additive（加字段/参数）或 bugfix，不改变现有行为
- **向后兼容**: `list_sessions(workspace_id=...)` 使用默认值 `None`，不修改不影响
- **删除 workspace 不清除 session**: 采用置空策略而非级联删除，不丢失数据

## 5. 实施步骤

### Step 1: 修复 Session ORM to_dict() — P0-1
- `app/db/models.py` — `to_dict()` 加一行 `"workspace_id": self.workspace_id or ""`

### Step 2: DataStore 协议支持 workspace_id 过滤 — P0-2
- `app/db/__init__.py` — `list_sessions` 签名加 `workspace_id: str | None = None`
- `app/db/compat.py` — 实现过滤逻辑
- `app/db/repository.py` — 实现过滤逻辑

### Step 3: 优化 ws_sessions 路由 — P0-2
- `app/api/workspace.py` — 传 workspace_id 到 list_sessions，去掉内存过滤
- `app/services/pm_agent_service.py` — list_sessions 透传参数

### Step 4: 修复 ws_update 空字符串 — P1-3
- `app/api/workspace.py` — 重构 kwargs 构建逻辑

### Step 5: 删除 workspace 清理关联 session — P1-4
- `app/db/compat.py` — delete_workspace 内调用 update_session 置空 workspace_id
- `app/db/repository.py` — 同上

### Step 6: 前端新建会话关联 workspace — P1-1
- `reqcollect-web/src/stores/session.ts` — newSession 接受 workspaceId 参数
- `reqcollect-web/src/views/ChatView.vue` — 发消息时传 workspace_id

### Step 7: 前端 workspace 上下文持久化 — P2-1
- `reqcollect-web/src/stores/session.ts` — currentWorkspaceId 用 localStorage 持久化

### Step 8: SideBar 按 workspace 筛选 — P1-6
- `reqcollect-web/src/components/layout/SideBar.vue` — 检测当前 route 参数，filter sessions
