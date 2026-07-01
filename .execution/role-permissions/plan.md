# Plan: role-permissions — 角色权限完善 + 缺失功能实现

## 1. 任务理解

### 当前问题
- 代码定义了 4 个角色（admin/analyst/reviewer/business），但**只有 admin 做了权限校验**
- analyst/reviewer/business 三个角色权限完全等价
- 需求提案流程缺少"审核"环节——任何登录用户都能改提案状态
- 缺少"批量选入 PRD"功能
- 缺少评审端点

### 核心目标
1. 完善角色权限矩阵——让 4 个角色各司其职
2. 补齐需求提案审核流程
3. 补齐"选入 PRD"功能

---

## 2. GitNexus 波及分析

### `get_current_user` 波及范围
- **被 50+ 个 API 端点调用**（auth/pm/workspace/wiki/wiki_ai）
- 风险：MEDIUM — 改动权限校验逻辑会影响所有端点

### 改动策略
- **不改 `get_current_user` 本身**（它只负责解析 token）
- **新增依赖项函数**：`require_role(*roles)` / `require_analyst` / `require_reviewer`
- **在需要权限的端点追加 Depends**——不改动现有端点路径和响应

### 受影响的端点（需追加权限校验）
| 端点 | 当前 | 改成 |
|------|------|------|
| PATCH `/workspaces/{id}/proposals/{pid}` (改状态) | 任何用户 | analyst/admin |
| POST `/pm/generate` (生成PRD) | 任何用户 | analyst/admin（业务人员只能挖需） |
| GET `/pm/sessions?all=true` | 已校验 admin | 保持 |
| 导出端点 | 任何用户 | analyst/admin |

---

## 3. 角色权限矩阵（目标）

| 功能 | admin | analyst | reviewer | business |
|------|:-----:|:-------:|:--------:|:--------:|
| 登录 / 查看自己会话 / 对话挖需 | ✅ | ✅ | ✅ | ✅ |
| 提炼需求提案 | ✅ | ✅ | ✅ | ✅ |
| **审核提案**（改状态 pending_review→approved/rejected） | ✅ | ✅ | ✅ | ❌ |
| **评审提案**（approved→in_development 打回） | ✅ | ✅ | ✅ | ❌ |
| **批量选入 PRD**（从 approved 提案生成 PRD） | ✅ | ✅ | ❌ | ❌ |
| 生成 PRD（从会话直出） | ✅ | ✅ | ❌ | ❌ |
| 查看所有用户会话 | ✅ | ❌ | ❌ | ❌ |
| 用户管理 | ✅ | ❌ | ❌ | ❌ |
| 数据看板 / 导出 | ✅ | ✅ | ✅ | ❌ |

---

## 4. 技术方案

### A) 新增权限依赖（app/core/auth.py）
```python
def require_role(*allowed_roles: str):
    """依赖工厂：要求用户角色在 allowed_roles 中"""
    async def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(403, detail=f"需要 {allowed_roles} 角色权限")
        return current_user
    return _check

# 常用快捷依赖
require_analyst = require_role("analyst", "admin")
require_reviewer = require_role("reviewer", "analyst", "admin")
require_prd_generator = require_role("analyst", "admin")
```

### B) 新增提案审核端点（app/api/workspace.py）
```python
@router.post("/workspaces/{wid}/proposals/{pid}/review")
async def review_proposal(
    wid, pid, body: ReviewBody,  # {action: "approve"|"reject", comment: str}
    current_user = Depends(require_reviewer),
):
    """审核提案：pending_review → approved/rejected"""
```

### C) 新增"选入 PRD"端点（app/api/pm.py）
```python
@router.post("/pm/generate-from-proposals")
async def generate_from_proposals(
    body: GenerateFromProposalsBody,  # {workspace_id, proposal_ids: [...], session_id?}
    current_user = Depends(require_prd_generator),
):
    """从已采纳的提案批量生成 PRD（SSE）"""
    # 1. 校验所有 proposal 状态都是 approved
    # 2. 合并提案内容作为 PRD 输入
    # 3. 复用现有 Phase 2 planner/generator/assembler
    # 4. 保存 PRD 时记录 source_proposal_ids
```

### D) 调整现有端点权限
| 端点 | 改动 |
|------|------|
| `PATCH /workspaces/{wid}/proposals/{pid}` | 改状态时校验 reviewer 权限（改其他字段仍放开） |
| `POST /pm/generate` | 加 `Depends(require_prd_generator)` |
| `POST /pm/continue` | 加 `Depends(require_prd_generator)` |
| 导出端点 | 加 `Depends(require_analyst)` |

### E) 前端适配
- ProposalDetailView 加"审核"按钮（仅 reviewer/analyst/admin 可见）
- ProposalListView 加"选入 PRD"多选操作（仅 analyst/admin 可见）
- 路由级权限守卫（基于 `auth.user.role`）
- 隐藏无权限的入口

---

## 5. 验收标准

### P0（核心权限）
- [ ] `require_role()` 依赖工厂实现
- [ ] 提案审核端点 `POST /workspaces/{id}/proposals/{pid}/review`
- [ ] business 角色尝试审核提案返回 403
- [ ] business 角色尝试生成 PRD 返回 403
- [ ] analyst 角色可以审核提案、生成 PRD
- [ ] reviewer 角色可以审核但不能生成 PRD

### P1（选入 PRD）
- [ ] `POST /pm/generate-from-proposals` SSE 端点
- [ ] 前端"选入 PRD"多选 + 生成按钮
- [ ] 生成的 PRD 记录 source_proposal_ids

### P1（前端权限）
- [ ] ProposalDetailView 审核按钮按角色显示
- [ ] 路由守卫拦截无权限访问

---

## 6. 风险与依赖
- 改 `get_current_user` 调用方的 Depends 会影响 50+ 端点——但都是追加 Depends，不改逻辑
- 现有 admin 账号不受影响（admin 在所有 require_role 中都允许）
- 需要为 analyst/reviewer 创建测试账号验证

---

## 7. 角色分工

| 角色 | 队友 | 任务 |
|------|------|------|
| 后端 | 后端开发者 | A) require_role 依赖 B) 审核端点 C) 选入PRD端点 D) 现有端点权限调整 |
| 前端 | 前端开发者 | E) 审核按钮 F) 选入PRD UI G) 路由守卫 |
| 设计 | UI设计师 | H) 审核状态可视化（通过/拒绝/打回的视觉反馈） |

---

## 8. 实施步骤

1. 后端: `app/core/auth.py` 新增 `require_role` 依赖工厂
2. 后端: `app/api/workspace.py` 新增审核端点 + 调整 PATCH 权限
3. 后端: `app/api/pm.py` 新增"选入 PRD"SSE 端点 + 调整 generate 权限
4. 前端: ProposalDetailView 加审核按钮 + 状态流转 UI
5. 前端: ProposalListView 加"选入 PRD"多选
6. 前端: 路由守卫 + 入口隐藏
7. Evaluate: 创建测试账号验证权限矩阵
