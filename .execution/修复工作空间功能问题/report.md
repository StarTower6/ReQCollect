# Report: 修复工作空间功能问题

## 验收标准验证

### P0
- [x] Session.to_dict() 返回的字典包含 workspace_id 字段 → OK (models.py + 已部署)
- [x] DataStore.list_sessions 支持 workspace_id 过滤 → OK (协议 + 双实现均已修改)
- [x] ws_sessions 用 DataStore 过滤而非全量加载 → OK (api/workspace.py 已修改)

### P1
- [x] SideBar 新建的会话关联到当前 workspace → OK (ChatView 传 workspace_id)
- [x] 删除 workspace 清理关联 session 的 workspace_id → OK (File/MySQL 双实现)
- [x] ws_update 支持将 code/description 改回空字符串 → OK (exclude_unset=True)
- [x] 刷新页面后 workspace 上下文不丢失 → OK (localStorage 持久化)

### P2
- [x] SideBar 会话列表按 workspace 筛选 → OK (filteredSessions 根据 currentWorkspaceId 过滤)
- [x] workspace_id 默认值统一 → OK (ORM `or ""`, 协议 `None`, 实现 `or ""`)

## 改动汇总

| 文件 | 改动 |
|------|------|
| `app/db/models.py` | Session.to_dict() +`workspace_id` 字段 |
| `app/db/__init__.py` | `list_sessions` +`workspace_id` 参数 |
| `app/db/compat.py` | `list_sessions` +workspace_id 过滤；`delete_workspace` +session 清理 |
| `app/db/repository.py` | `list_sessions` +workspace_id 过滤；`delete_workspace` +session 清理 |
| `app/api/workspace.py` | `ws_update` 改 `exclude_unset=True`；`ws_sessions` 走 DataStore 过滤 |
| `app/services/pm_agent_service.py` | `list_sessions` limit=10000 |
| `reqcollect-web/src/stores/session.ts` | `newSession(workspaceId?)`；localStorage 持久化；`filteredSessions` 按 workspace 过滤 |
| `reqcollect-web/src/views/ChatView.vue` | 新建 session 传 workspace_id |
| `reqcollect-web/src/components/layout/AppLayout.vue` | 全局新对话清除 workspace 上下文 |
| `reqcollect-web/src/types/index.ts` | Session 类型 +`workspace_id` |

## 回归检查
- [x] `/api/health` — 无改动
- [x] 现有 API 端点 — 所有修改 additive（加参数/字段），不影响现有调用
- [x] FileDataStore 向前兼容 — `list_sessions(workspace_id=None)` 行为不变
- [x] MySQL schema — 无需变更（`sessions.workspace_id` 已在启动迁移中添加）

## 代码质量
- [x] 无硬编码密码/API Key
- [x] 无重复功能
- [x] 所有新参数有类型注解

## 评估结论
✅ **全部通过** — 8 个问题全部修复，后端逻辑正确，前端交互完整。
