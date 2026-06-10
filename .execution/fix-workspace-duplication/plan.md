# Plan: 修复工作空间重复创建问题 (fixes #6)

## 1. 任务理解
- **问题**: GitHub Issue #6 — 工作空间项目存在重复
- **根因**: `app/core/workspace.py` 的 `migrate_sessions_to_workspaces()` 每次应用启动都会运行，且：
  1. 不检查 session 是否已经分配了 `workspace_id`（重复迁移）
  2. 不检查同名 workspace 是否已存在（重复创建）
- **后果**: 每次服务重启都会产生一批重复的工作空间

## 2. 改动清单
- **修改文件**:
  - `app/core/workspace.py` — 修复迁移逻辑，增加去重检查

## 3. 数据模型 (无变更)

## 4. 验收标准

- [ ] **P0**: 服务重启后不再产生重复工作空间
- [ ] **P0**: 已有 workspace_id 的 session 不会被重复迁移
- [ ] **P0**: 已有同名 workspace 的不会重复创建（复用已有 workspace）
- [ ] **P1**: 尚未迁移的 session (无 workspace_id) 仍能正常迁移

## 5. 风险与依赖
- `list_workspaces()` 在 FileDataStore 中 **忽略 `user_id` 参数**，遍历全部 workspace 文件——这正好适合去重检查
- 该修复只修改一个文件，风险低

## 6. 实施步骤 (按顺序)

1. 修改 `app/core/workspace.py`:
   - 在分组前过滤掉已有 `workspace_id` 的 session
   - 在创建 workspace 前，通过 `datastore.list_workspaces()` 检查同名 workspace 是否已存在
   - 如果存在则复用其 id，否则创建新的
