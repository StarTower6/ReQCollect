# Tasks: 修复工作空间功能问题

## 任务清单
- [x] Step 1: Session.to_dict() 添加 workspace_id — P0-1 — commit: 02bf137
- [x] Step 2: DataStore list_sessions 支持 workspace_id 过滤 — P0-2 — commit: c02ef7c
- [x] Step 3: 优化 ws_sessions 路由（直接走 DataStore 过滤） — P0-2 — commit: c02ef7c
- [x] Step 4: 修复 ws_update 空字符串处理 — P1-3 — commit: a57c30f
- [x] Step 5: 删除 workspace 清理关联 session — P1-4 — commit: e088a6f
- [x] Step 6: 前端新建会话关联 workspace — P1-1 — commit: 7b33198
- [x] Step 7: 前端 workspace 上下文持久化 (localStorage) — P2-1 — commit: 7b33198
- [x] Step 8: SideBar 按 workspace 筛选会话 (filteredSessions) — P1-6 — commit: 7b33198
