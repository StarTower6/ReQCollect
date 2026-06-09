# Plan: 14 — 新建会话归属工作空间

## 1. 根因
新建会话时前端不传 workspace_id，`POST /api/pm/chat` 创建 session 没有 workspace_id。

## 2. 改动清单
- `app/models/pm.py` — ChatRequest / AgentRequest 加 workspace_id 字段
- `app/api/pm.py` — 传递 workspace_id 给 service
- `app/services/pm_agent_service.py` — chat() 传 workspace_id 给 create_session
- `reqcollect-web/src/views/ChatView.vue` — SSE 请求体加 workspace_id
- `reqcollect-web/src/stores/session.ts` — 加 setWorkspace() / currentWorkspaceId
- `reqcollect-web/src/views/WorkspaceDetail.vue` — 新建会话时保存 workspace_id

## 3. 验收标准
- [ ] P0: 从工作空间新建的会话自动归属该工作空间
- [ ] P0: 侧栏直接新建会话（不选工作空间）不报错
