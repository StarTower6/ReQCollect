# Plan: 13 — 工作空间（P0 核心 MVP）

## 1. 范围评估

08 模块包含三大块：**工作空间管理** ｜ **Wiki 文库** ｜ **需求图谱**

这不是一个"一轮做完"的模块，建议按以下优先级分步实施：

### P0 批次（本轮）— 工作空间基础
- 工作空间 CRUD（创建/列表/编辑/删除）
- Session 从属工作空间（sessions 表加 workspace_id）
- 现有数据迁移（project_name → workspace）
- 前端入口：工作空间列表页取代扁平首页
- 工作空间内会话列表

### P1 批次（下轮）— 成员管理 + Wiki
- 工作空间成员（4 种角色）
- 权限校验
- Wiki 页面自动/手动创建
- [[链接]] 解析

### P2 批次（远期）— 图谱
- force-graph 渲染
- 全局/局部图谱
- 关系类型标注

## 2. 本轮改动（工作空间基础）
- 新增: `app/db/__init__.py` — Workspace CRUD 抽象方法
- 新增: `app/db/compat.py` — FileDataStore 实现
- 新增: `app/db/repository.py` — MySQLDataStore 实现
- 新增: `app/api/workspace.py` — Workspace API 路由
- 新增: `app/core/workspace.py` — 迁移工具
- 修改: `app/api/pm.py` — 创建 session 时关联 workspace
- 修改: `app/db/models.py` — Session 模型加 workspace_id
- 修改: `app/services/pm_agent_service.py` — 创建 session 传 workspace_id
- 新增: 前端 WorkspaceList.vue / WorkspaceDetail.vue
- 修改: 前端路由 + AppLayout 导航

## 3. 验收标准
- [ ] P0: 创建工作空间（名称必填）
- [ ] P0: 工作空间列表页展示所有可访问空间
- [ ] P0: 工作空间详情页（概览 + 会话列表）
- [ ] P0: 编辑/删除工作空间
- [ ] P0: 会话创建时选择所属工作空间
- [ ] P0: 工作空间内仅显示本空间会话
- [ ] P0: 现有 session 的 project_name 自动迁移为工作空间
- [ ] P1: 工作空间编辑（名称/描述/编码）
- [ ] P1: 删除确认弹窗
