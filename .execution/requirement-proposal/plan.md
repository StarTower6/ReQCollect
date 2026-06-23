# Plan: requirement-proposal — 需求提案系统

## 1. 任务理解

### 核心定位变更
当前系统: "AI 对话 → 需求画像 → PRD"（以文档生成为终点）
目标系统: "AI 对话 → 需求提案 → 需求池 → 产品经理审核 → 批量生成 PRD"（以需求管理为中心）

一次对话深入挖掘一个业务问题，产出 **一份需求提案**。业务提急迫性，AI 评影响面。产品经理从池子里挑出来生成 PRD。

### 关键术语统一
- **需求提案 (RequirementProposal)** — AI 从对话中梳理的结构化需求描述，给产品经理看
- **需求池 (Proposal Pool)** — 工作空间下所有提案的汇总视图
- **PRD** — 产品经理从池中选中若干已采纳提案后批量生成

---

## 2. 数据模型

### 新增 ORM 模型: RequirementProposal

```python
class RequirementProposal(Base):
    __tablename__ = "requirement_proposals"

    id: str              # UUID hex
    workspace_id: str     # 所属工作空间
    source_session_id: str # 来源对话 (Session.id)
    submitter_id: str     # 提出人 (User.id)

    title: str            # 提案标题（AI提炼）
    background: str       # 业务背景与当前现状（Text）
    pain_points: list     # 核心痛点列表 (JSON)
    desired_outcome: str  # 期望效果（Text）
    scope_note: str       # 范围说明 (Text) — 做什么/不做什么

    urgency: str          # 业务紧急度 (high/medium/low) — 提出人判断
    priority: str         # AI 评估优先级 (P0/P1/P2/P3)
    ai_assessment: str    # AI 评估理由 (Text) — 影响面、依赖、建议

    status: str           # 待评审/已采纳/开发中/已上线/已关闭
    tags: list            # 分类标签 (JSON)

    created_at: datetime
    updated_at: datetime
```

### 数据关系
- `RequirementProposal.workspace_id` → 与现有 Workspace 体系一致
- `RequirementProposal.source_session_id` → 可以回头追溯对话原文
- `RequirementProposal.submitter_id` → 归属到人

### 不做
- 不改动 Session、Profile、ChatMessage 现有表结构
- 不改动 GeneratedPRD 现有表结构

---

## 3. 技术方案

### 后端改动

#### A) 数据层 (app/db/)

**models.py — 新增 RequirementProposal ORM**
- 字段如上述数据模型
- to_dict() 序列化
- 索引: (workspace_id, status), (submitter_id), (source_session_id)

**__init__.py — DataStore 新增方法**
- `create_proposal(workspace_id, ...)  -> dict`
- `get_proposal(proposal_id)           -> dict | None`
- `list_proposals(workspace_id, status, urgency, priority, limit, offset) -> list[dict]`
- `update_proposal(proposal_id, **kwargs) -> dict | None`
- `delete_proposal(proposal_id)        -> bool`
- `count_proposals(workspace_id)       -> dict` (按状态统计)

**repository.py — MySQLDataStore 实现**
**compat.py — FileDataStore 实现（JSON 文件）**

**database.py — 幂等建表迁移**
- `CREATE TABLE IF NOT EXISTS requirement_proposals`

#### B) API 层

**app/api/workspace.py — 新增提案端点**（不用新文件，复用 workspace 路由体系）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/workspaces/{id}/proposals` | 创建提案 |
| GET | `/api/workspaces/{id}/proposals` | 列出提案 (?status=&urgency=&priority=) |
| GET | `/api/workspaces/{id}/proposals/{pid}` | 获取提案详情 |
| PATCH | `/api/workspaces/{id}/proposals/{pid}` | 更新提案 (状态、标签、优先级) |
| DELETE | `/api/workspaces/{id}/proposals/{pid}` | 删除提案 |

#### C) Agent 层 — 新增提案提炼方法

**app/agent/pm/proposal_extractor.py** （新文件）
- 方法: `extract_proposal_from_session(session_id, ds) -> dict`
- 流程: 读取 Session 的对话历史 → LLM 提炼 → 返回结构化提案字段
- LLM 温度 0.3（低温确保准确性），不修改会话
- 如某字段信息不足，标注而非编造

**app/agent/pm/proposal_priority.py** （新文件）
- 方法: `assess_priority(proposal) -> (priority, assessment)`
- 流程: LLM 根据影响面/紧迫性/依赖/实施难度评估 P0-P3
- 有评审记录供产品经理审查

**app/api/pm.py — 新增 SSE 端点**
- POST `/api/pm/extract-proposal` — 从当前会话提炼需求提案（SSE 流式返回字段）
  - 事件类型: `title` / `background` / `pain_points` / `desired_outcome` / `done`

### 前端改动

#### 新页面/组件

| 组件 | 文件 | 说明 |
|------|------|------|
| ProposalListView | views/ProposalListView.vue | 需求池列表视图（筛选/搜索/排序） |
| ProposalKanbanView | views/ProposalKanbanView.vue | 看板视图（按状态列） |
| ProposalDetailView | views/ProposalDetailView.vue | 提案详情页 |
| ProposalCard | components/proposal/ProposalCard.vue | 卡片组件 |
| ProposalExtractPanel | components/chat/ProposalExtractPanel.vue | 对话中的"提炼提案"面板 |

#### 改动现有组件

| 现有组件 | 改动 |
|----------|------|
| ChatView.vue | 在对话顶部或侧栏增加"提炼提案"按钮 |
| WorkspaceDetail.vue | 增加"需求池"Tab 入口 |
| router/index.ts | 增加 3 条新路由 |
| api/ 目录 | 新增 proposal.ts 客户端 |
| types/index.ts | 新增 Proposal 类型定义 |

#### 路由
| 路径 | 视图 |
|------|------|
| `/workspace/:id/proposals` | ProposalListView |
| `/workspace/:id/proposals/kanban` | ProposalKanbanView |
| `/workspace/:id/proposals/:pid` | ProposalDetailView |

### 不动
- `/api/pm/*` 现有 4 个端点不动
- `prompts.py` 的 `PM_SYSTEM_PROMPT` 不动
- `phase1/mining_agent.py` 不动
- `phase2/` 全部不动
- `Session` / `Profile` / `ChatMessage` 表不动
- existing pipes (pm_agent_service.py) 不动

---

## 4. 验收标准

### P0 (核心功能)
- [ ] 新建 `requirement_proposals` 表，应用启动自动建表
- [ ] DataStore 实现 7 个 CRUD 方法（MySQL + File 双后端）
- [ ] POST /api/workspaces/{id}/proposals 创建提案
- [ ] GET /api/workspaces/{id}/proposals 列出提案（支持状态/优先级/紧急度筛选）
- [ ] PATCH .../proposals/{pid} 更新提案状态/标签/优先级
- [ ] DELETE .../proposals/{pid} 删除提案
- [ ] POST /api/pm/extract-proposal SSE 流式提炼提案
- [ ] 前端提案列表页可正常展示、筛选、搜索
- [ ] 前端提案详情页可正常展示
- [ ] 前端对话页"提炼提案"按钮触发生成提案

### P1 (体验优化)
- [ ] 前端提案看板视图（拖拽排序）
- [ ] AI 优先级自动评估（提案创建后触发）
- [ ] 提案从"已采纳"状态支持"选入 PRD"（触发现有 Phase 2 管线）

---

## 5. GitNexus 波及分析

### 索引状态
- 仓库: ReQCollect (2,658 nodes / 6,725 edges / 84 clusters / 229 flows)
- 索引版本: `66ba3c8`

### DataStore 波及范围 (MEDIUM 风险)
新增 RequirementProposal CRUD 方法的波及:
- **d=1 (必须改的)**: `FileDataStore`, `MySQLDataStore`, `__init__.py` (接口), `main.py` (注册)
- **d=2 (会受影响但不需改)**: `pm.py`, `auth.py`, `workspace.py`, `wiki.py`, `tools.py` (import DataStore 但不是改 DataStore 接口)

### pm.py 波及范围 (LOW 风险)
新增 `/api/pm/extract-proposal` SSE 端点:
- 与现有 4 个 SSE 端点 `/chat`, `/generate`, `/agent` 同级，不修改现有端点
- 只新增路由，零改动风险

### workspace.py 波及范围 (LOW 风险)
新增 5 个 proposal CRUD 端点:
- 完全新增路由，挂载在 `workspace_router` 下
- 不改动现有任何端点 (ws_create, ws_list 等)

### 不改动零风险的模块
- `app/agent/pm/phase1/` — 挖需引擎 (229 flows 中不涉及)
- `app/agent/pm/prompts.py` — 提示词
- `app/agent/pm/phase2/` — PRD 管线
- `app/services/pm_agent_service.py` — 业务编排 (只 import DataStore，不修改)
- `app/core/auth.py` — JWT 认证

## 6. 风险与依赖
- 提炼提案的 LLM Prompt 需要充分测试 —— 防止 AI 编造不存在的信息
- SSE 流式提炼需要正确解析 fragment 事件，保持与现有 /api/pm/chat 一致的流式格式
- 前端需要新增 3 个页面 + 3 个组件 + 2 个路由，前端工作量是后端的两倍

---

## 6. 角色分工

| 角色 | 队友 | 任务 |
|------|------|------|
| 后端 | 后端开发者 | A) 数据模型 + DataStore B) API 端点 C) Agent 提炼方法 |
| 前端 | 前端开发者 | D) 提案列表/详情/看板页面 E) 对话页提炼按钮 F) API 对接 |
| 设计 | UI设计师 | G) 提案页面 UI 规范 H) 需求池/看板交互设计 I) 全局一致性审查 |

---

## 7. 实施步骤

1. 后端开发者: 新增 ORM 模型 + DataStore 接口 + 双后端实现 + 建表迁移
2. 后端开发者: 新增提案 CRUD API 端点
3. 后端开发者: 新增提案提炼 Agent 方法 + SSE 端点
4. 前端开发者: 新增类型定义 + API 客户端
5. 前端开发者 + UI设计师: 提案列表页 + 详情页
6. 前端开发者: 对话页提炼按钮 + SSE 对接
7. 前端开发者 + UI设计师: 看板视图（P1）
8. Evaluate: 全量回归验证
