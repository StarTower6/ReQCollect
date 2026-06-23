# Plan: model-refactor — 实体关系重构

## 1. 任务理解

在现有系统上做"最低侵入"的实体重命名和关系加固，不改前端显示名称，只改后端代码结构。

### 核心目标
1. **命名统一** — 按业务含义命名，消除歧义
2. **关系加固** — 松散字符串关联 → FK + relationship
3. **职责清晰** — 每个实体只做自己该做的事

### 不改的
- 表名（`sessions`, `workspaces`, `requirement_proposals`, `generated_prds`, `requirement_profiles` 等）— 不改，避免数据迁移
- 现有 API 路径 `/api/pm/*` — 不改
- 前端路由路径 — 不改
- 前端显示名称（如"会话"、"工作空间"）— 不改

---

## 2. GitNexus 波及分析

### Session 波及范围 (LOW)
- **d=1**: `repository.py`, `database.py`, `migrate_json_to_mysql.py`
- **d=2**: `main.py`, `db/__init__.py`
- **d=3**: 各 API 模块（间接 import）
- **风险**: 加 FK 和 relationship 是追加操作，不删不改，不会出问题

### Workspace 波及范围 (LOW)
- **d=1**: `repository.py`, `database.py`, `migrate_json_to_mysql.py`
- **d=2**: `main.py`, `db/__init__.py`
- **d=3**: 各 API 模块（间接 import）
- **风险**: 同 Session

### Proposal 波及范围 (LOW)
- **d=1**: `repository.py`, `compat.py`, `database.py`
- 主要在 DataStore 层，不影响 Agent 和 API

### 233 个已索引的执行流
- **不受影响** — 全是追加改，不改已有的状态机逻辑

---

## 3. 具体改动

### 模块 A: ORM 模型层 (app/db/models.py)

#### A1: 新增 Relationship —— 加固关系

```python
# Workspace — 加 relationship 到 Session/Proposal/WikiPage
class Workspace(Base):
    __tablename__ = "workspaces"
    # ... 现有字段不动
    
    discussions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="workspace_ref",
        foreign_keys="Session.workspace_id"
    )
    proposals: Mapped[list["RequirementProposal"]] = relationship(
        "RequirementProposal", back_populates="workspace_ref",
        foreign_keys="RequirementProposal.workspace_id"
    )

# Session — 加 back_populates, 不动表
class Session(Base):
    # workspace_id 字段不动，加 back reference
    workspace_ref: Mapped["Workspace | None"] = relationship(
        "Workspace", back_populates="discussions",
        foreign_keys=[workspace_id]
    )

# RequirementProposal — 加 FK + relationship + 改名
# source_session_id → discussion_ref (字段不改名，加 relationship)
class RequirementProposal(Base):
    discussion_ref: Mapped["Session | None"] = relationship(
        "Session", back_populates="proposals",
        foreign_keys=[source_session_id]
    )
    workspace_ref: Mapped["Workspace | None"] = relationship(
        "Workspace", back_populates="proposals",
        foreign_keys=[workspace_id]
    )
    submitter_ref: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[submitter_id]
    )

# Session 加 proposals 反向关系
class Session(Base):
    proposals: Mapped[list["RequirementProposal"]] = relationship(
        "RequirementProposal", back_populates="discussion_ref",
        foreign_keys="RequirementProposal.source_session_id"
    )
```

**注意**: 这些全是 `relationship()` 追加，不涉及数据库 DDL 变更。
Pubic API `to_dict()` 输出不变，只加内部关联。

#### A2: 代码内重命名（类名 + 别名）

| 当前类名 | 新增别名 | 用途 |
|----------|---------|------|
| `Session` | 别名 `Discussion` | 代码可读性 |
| `RequirementProfile` | 别名 `DiscussionContext` | 代码可读性 |
| `RequirementProposal` | 别名 `Proposal` | 代码可读性 |
| `GeneratedPRD` | 别名 `PrdDocument` | 代码可读性 |

```python
# 在 models.py 末尾
Discussion = Session  # 别名 — Session 是讨论
DiscussionContext = RequirementProfile
Proposal = RequirementProposal
PrdDocument = GeneratedPRD
```

#### A3: PRD 生成逻辑调整（关键业务调整）
`GeneratedPRD` 新增字段:
```python
source_proposal_ids: Mapped[list | None] = mapped_column(JSON, default=list)
# 记录从哪些 Proposal 生成的，为空 = 旧数据
```

---

### 模块 B: DataStore 层 (app/db/__init__.py + repository.py + compat.py)

**不改接口签名**，只加新方法（Search by discussion）：

```python
# 新增（非必须，但有用）
@abstractmethod
async def get_proposals_by_discussion(self, session_id: str) -> list[dict]:
    """Get all proposals from a discussion."""
```

DataStore 只加新方法、不删不改旧方法。

---

### 模块 C: API 层 — proposal_extractor 微调

**app/agent/pm/proposal_extractor.py**
- 创建 Proposal 时关联最新的 `submitter_id`（从 Session 的 `user_id` 获取）

**app/agent/pm/proposal_priority.py**
- 评估逻辑保持不变，输出中补充 `ai_assessment` 解释影响面

---

### 模块 D: 前端

**不改任何页面结构**。
- types/index.ts 加 `Proposal` 别名（可选）
- 不调整路由、不调整组件

---

## 4. 不改（保持原样）

| 保持原样 | 原因 |
|---------|------|
| 表名 `sessions` / `requirement_profiles` 等 | 数据迁移成本高，加别名即可 |
| API 路径 `/api/pm/*` | 项目规范 |
| 前端路由 `/workspaces/:id` | 用户习惯 |
| 前端显示中文名"会话"/"工作空间" | — |
| `list_proposals` 等 DataStore 方法签名 | 向后兼容 |
| `workspace.py` 中的 5 个 Proposal 端点 | 正常工作中 |

---

## 5. 验收标准

- [ ] P0: Workspace 类新增 `discussions` / `proposals` relationship，Mapper 不报错
- [ ] P0: Session 类新增 `workspace_ref` / `proposals` relationship
- [ ] P0: RequirementProposal 类新增 `discussion_ref` / `workspace_ref` / `submitter_ref` relationship
- [ ] P0: 应用启动后所有 relationship 可正常访问（不报 AttributeError）
- [ ] P1: `models.py` 末尾加 4 个别名（Discussion = Session 等）
- [ ] P1: `GeneratedPRD` 新增 `source_proposal_ids` JSON 字段，建表迁移幂等
- [ ] P1: 从对话提炼提案时自动填充 `submitter_id`
- [ ] P1: 运行 `python -c "from app.db.models import Discussion, Proposal"` 不报错

---

## 6. 风险与依赖
- relationship 使用 `foreign_keys` 明确指定列，避免 SQLAlchemy 自动推断错误
- 别名不是类继承，不会影响 ORM 的 Mapper 机制
- `GeneratedPRD` 加字段不影响已有 PRD 读取
- **先部署 → 再测试 → 确认无问题后提交**

---

## 7. 实施步骤

1. `app/db/models.py`: Workspace 加 relationship（discussions, proposals）
2. `app/db/models.py`: Session 加 workspace_ref, proposals relationship
3. `app/db/models.py`: RequirementProposal 加 discussion_ref, workspace_ref, submitter_ref
4. `app/db/models.py`: GeneratedPRD 加 source_proposal_ids 字段
5. `app/db/models.py`: 末尾加 4 个别名（Discussion/Proposal/DiscussionContext/PrdDocument）
6. `app/db/database.py`: GeneratedPRD 迁移（加列）幂等
7. `app/agent/pm/proposal_extractor.py`: 创建提案时填充 submitter_id
8. 部署验证 + Evaluate
