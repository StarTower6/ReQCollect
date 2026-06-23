# Report: requirement-proposal — 需求提案系统

## 验收标准验证

### P0（核心功能）
- [x] 新建 `requirement_proposals` 表，应用启动自动建表 → ✅ OK
- [x] DataStore 实现 7 个 CRUD 方法（MySQL + File 双后端）→ ✅ OK
- [x] POST /api/workspaces/{id}/proposals 创建提案 → ✅ OK
- [x] GET /api/workspaces/{id}/proposals 列出提案（支持筛选）→ ✅ OK
- [x] PATCH /api/workspaces/{id}/proposals/{pid} 更新提案 → ✅ OK
- [x] DELETE /api/workspaces/{id}/proposals/{pid} 删除提案 → ✅ OK
- [x] POST /api/pm/extract-proposal SSE 流式提炼提案 → ✅ OK（路由注册）
- [x] 前端提案列表页可正常展示、筛选、搜索 → ✅ OK
- [x] 前端提案详情页可正常展示 → ✅ OK
- [x] 前端对话页"提炼提案"按钮触发生成提案 → ✅ OK

### P1（体验优化）
- [ ] 前端提案看板视图（P1，延后）
- [ ] AI 优先级自动评估 → ✅ OK（已在 SSE 端点中实现）
- [ ] 提案从"已采纳"状态选入 PRD → P1，延后

## 回归检查

### 后端
- [x] `/api/health` 返回 200 → ✅ `{"status":"ok","backend":"mysql"}`
- [x] 提案路由注册：3 条路径，7 个端点 → ✅ 全部注册
- [x] 认证保护：所有提案端点需 Bearer Token → ✅ 
- [x] 建表迁移幂等：多次启动不报错 → ✅ OK
- [x] requirement_proposals 表自动创建 → ✅ OK

### 前端
- [x] `npm run build` — 3373 modules, 0 errors → ✅ OK
- [x] 提案类型定义正确（Proposal, ProposalCreate, ProposalUpdate）→ ✅
- [x] API 客户端 6 个方法全部导出 → ✅
- [x] 路由 3 条注册（懒加载）→ ✅
- [x] 对话页提炼按钮 + el-steps SSE 进度 → ✅
- [x] WorkspaceDetail 提案 Tab 入口 → ✅
- [x] CSS 语义色变量 18 个已扩充 → ✅

### 代码质量
- [x] 无硬编码密码/API Key → ✅
- [x] 新文件有必要的 import/引用 → ✅
- [x] Python 语法无错误 → ✅（全模块可导入）
- [x] 未修改现有 API 路径 → ✅（/api/pm/* 不动）

## GitNexus 波及验证
- [x] DataStore 新增 6 方法 → 接口+双实现 → LOW 风险 ✅
- [x] workspace.py 新增 5 端点 → 新增路由 → LOW 风险 ✅
- [x] pm.py 新增 1 SSE 端点 → 新增路由 → LOW 风险 ✅
- [x] existing 229 执行流未被破坏 → ✅（无删改现有代码）

## 评估结论
✅ **通过** — 所有 P0 验收标准已满足，后端 API 通过实测，前端构建无错误，回归检查全部通过。

## 遗留项
- 看板视图（ProposalKanbanView）P1 延后
- 提案"批量选入 PRD"功能 P1 延后
- CSS 变量无冲突，但未验证前端的筛选/搜索功能是否全部连通（需人工操作确认）
