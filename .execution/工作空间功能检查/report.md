# Report: 工作空间功能异常检查

## 概述

对最近 5 个 commit（`d6d5a17` ~ `edf15bb`）引入的 workspace 功能进行系统性代码审查，
从数据层、API 层、业务逻辑、前端交互四个维度检查异常和不合理之处。

---

## 一、P0 级问题 — 功能无法正常工作的 Bug

### 1.1 MySQL 后端下 Session.to_dict() 缺少 workspace_id ❌ 严重

**文件**: `app/db/models.py:120-131`

```python
def to_dict(self) -> dict:
    return {
        "session_id": self.id,
        "user_id": self.user_id,
        "project_name": ...
        # ❌ 缺少 workspace_id 字段
    }
```

**影响路径**:
1. MySQLDataStore.create_session() 返回 `session.to_dict()` → 不含 workspace_id
2. `GET /api/workspaces/{id}/sessions` 调用 `svc.list_sessions()` → 返回的 session 无 workspace_id
3. 前端 `fetchWorkspaceSessions()` 接收 sessions 后，无法通过 `s.get("workspace_id") == workspace_id` 匹配 → **会话列表永远为空**

**对比**: FileDataStore 直接返回完整 dict（包含 workspace_id），因此文件存储后端工作正常。

**修复**: 在 `to_dict()` 添加 `"workspace_id": self.workspace_id or ""`

### 1.2 `ws_sessions` 全量加载 + 客户端过滤，无法扩展 ❌ 严重

**文件**: `app/api/workspace.py:130-145`

```python
async def ws_sessions(workspace_id, current_user):
    ws = await ds.get_workspace(workspace_id)
    # 没有先校验 workspace 存在？已校验
    svc = _svc()
    sessions = await svc.list_sessions()  # ❌ 获取所有 session
    ws_sessions = [s for s in sessions if s.get("workspace_id") == workspace_id]
    # 客户端过滤，当 sessions 表有上万条记录时性能灾难
```

**问题**:
- DataStore 协议中 `list_sessions` 不支持按 `workspace_id` 过滤（参数只有 user_id/status/limit/offset）
- 每次请求都加载所有 sessions（限 50 条，但遍历整个 sessions 目录的文件）

---

## 二、P1 级问题 — 功能设计缺陷

### 2.1 新建会话不传递 workspace_id，碎片化

**文件**: `reqcollect-web/src/stores/session.ts:29-33`、`reqcollect-web/src/views/ChatView.vue`

**流程**:
- SideBar "新对话" → `sessionStore.newSession()` → 只生成 session ID，**不设置 workspace_id**
- `ChatView.handleSend()` 第一次发消息时才通过 SSE 传 `workspace_id: sessionStore.currentWorkspaceId || ''`
- 但 `startNewChat` 只在从 WorkspaceDetail 进入时才设置 `currentWorkspaceId`（`goNewChat()` 调用 `sessionStore.setWorkspace(wsId)`）

**后果**: 
- 所有从 SideBar 新建的会话 **不会关联到任何 workspace**
- `currentWorkspaceId` 是一个内存状态，刷新页面后丢失

### 2.2 删除 workspace 不清理关联 session

**文件**: `app/core/workspace.py`、`app/db/compat.py:588-598`

- `FileDataStore.delete_workspace()` 只删 workspace 文件
- `MySQLDataStore.delete_workspace()` 只删 workspace 行
- 都没有清理关联 session 的 `workspace_id`

**后果**: session 变成"孤儿"——workspace_id 指向一个不存在的 workspace

### 2.3 `ws_update` 无法将字段改回空字符串

**文件**: `app/api/workspace.py:105`

```python
kwargs = {k: v for k, v in body.model_dump().items() if v}  # ❌ if v 过滤 falsy
```

- `body.model_dump()` 会包含所有字段（因为 WorkspaceUpdate 每个字段默认 `""`）
- `if v` 过滤掉空字符串 `""`、`None` 等 falsy 值
- 用户无法将 `code` 或 `description` 从有值改回空值

### 2.4 `list_workspaces` 的 user_id 参数形同虚设

**DataStore 协议**: `list_workspaces(self, user_id: str | None = None) → list[dict]`

| 实现 | 是否使用 user_id |
|------|-----------------|
| `FileDataStore.list_workspaces` | ❌ 忽略，返回所有 active workspace |
| `MySQLDataStore.list_workspaces` | ❌ 忽略，返回所有 active workspace |
| `workspace.py ws_list` | 不传 user_id |

**后果**: 所有用户看到所有 workspace，没有用户隔离。

### 2.5 Session.to_dict() 不返回 workspace_id（MySQL）— 已列为 P0

同上 1.1，列在这里作为补充说明。

### 2.6 SideBar 按 workspace 筛选

**缺失**: 
- `sessionStore.load()` 获取所有 sessions，不按当前 workspace 过滤
- SideBar 展示了所有 workspace 的 session，跨 workspace 混淆

---

## 三、P2 级问题 — 可优化项

### 3.1 `Workspace.code` 在 UI 中无校验

**文件**: `WorkspaceCreate` 中 `code: str = ""` 没有格式校验、唯一性校验
- 数据库层面也没有 unique index

### 3.2 前端创建 session 未预关联 workspace

**`WorkspaceDetail.goNewChat()`**:
```typescript
sessionStore.setWorkspace(wsId)  // 存储内存
const sid = sessionStore.newSession()  // 生成前端 session ID
router.push(`/chat/${sid}`)
```

刷新页面后 `currentWorkspaceId` 丢失 → 用户发消息时 workspace_id 为空

### 3.3 `create_workspace` 不生成 code

`WorkspaceCreate` 有 code 字段，但创建 dialog 中 code 是选填，用户可能忘记填写。
如果有默认值生成逻辑（如自动从名称生成编码缩写）更好，但不强制。

### 3.4 Session ORM 中 workspace_id 默认值不一致

- MySQL Session model: `workspace_id: Mapped[str | None] = mapped_column(String(64), default="")`
- DataStore 协议: `create_session(..., workspace_id: str | None = None)`
- MySQL 实现: `workspace_id=workspace_id or ""`
- File 实现: `workspace_id or ""`

空字符串和 None 混用，虽然功能上 `""` 是 falsy 不影响判断，但语义不清晰。

---

## 四、评估结论

### 影响范围

| 后端 | 影响 |
|------|------|
| MySQL | **严重** — P0 问题导致 workspace 详情页会话列表永远为空 |
| File (JSON) | **中等** — 无 P0，有 P1/P2 设计缺陷 |

### FIX 优先级

```
P0-1: Session.to_dict() 添加 workspace_id       → [数据层] models.py
P0-2: ws_sessions 支持按 workspace_id 过滤      → [数据层] DataStore 协议 + 实现
P1-1: 新建会话传递 workspace_id                  → [前端] ChatView.vue + session store
P1-2: 删除 workspace 清理 session.workspace_id   → [数据层] compat.py + repository.py
P1-3: ws_update 支持清空字段                     → [API层] workspace.py
P1-4: list_workspaces 用户隔离或明确设计意图     → [数据层] 协议定义
P2-1: Frontend workspace context 持久化          → [前端] session store
P2-2: workspace_id 默认值统一                     → [数据层] ORM + 实现统一
```

### 结论

⚠️ **严重程度: 高** — MySQL 后端下 workspace 核心功能（会话列表）无法正常工作。
FileDataStore 后端下核心功能可用，存在设计缺陷但不影响基本使用。

建议优先修复 P0 两个问题，然后按 P1 优先级逐一修复。
