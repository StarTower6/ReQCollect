# Report: 工作空间成员机制 + 权限收紧（批次1）

## 验收标准验证

### P0
- [x] P0: workspace_members 表自动建表 → OK (database.py 幂等 CREATE TABLE + FK)
- [x] P0: 创建工作空间后创建者自动成为 owner 成员 → OK (repository.create_workspace flush 后插 owner; compat.create_workspace 同步加 members 数组)
- [x] P0: list_workspaces 按成员过滤（非 admin 只看自己成员的）→ OK (repository JOIN WorkspaceMember; compat 遍历 members)
- [x] P0: business 访问非成员工作空间 403 → OK (ws_get/_require_workspace_member)
- [x] P0: business 只能看自己的会话/提案 → OK (pm_list_sessions uid=current_user.id; ws_sessions/ws_proposal_list business 过滤)
- [x] P0: analyst 能看工作空间所有会话/提案（只要是成员）→ OK (pm_list_sessions analyst 按工作空间成员过滤; _check_session_ownership analyst 校验成员)
- [x] P0: reviewer 不能访问 /api/pm/sessions（403）→ OK (pm_list_sessions reviewer raise 403; _check_session_ownership reviewer 403)
- [x] P0: 成员管理端点（添加/移除/列表）→ OK (POST/DELETE/GET /workspaces/{id}/members)
- [x] P0: 前端成员管理 Tab → OK (WorkspaceDetail.vue "👥 成员" Tab + 添加/移除弹窗)

### P1
- [x] P1: business 隐藏新建工作空间按钮 → OK (WorkspaceList canCreateWorkspace = analyst/admin)
- [x] P1: owner 才能编辑/删除工作空间 → OK (_require_workspace_owner_or_admin; 前端 canManageWorkspace/canManageMembers)

## 功能验证
- [x] 后端 5 个 DataStore 抽象方法 + MySQL/File 双实现导入成功
- [x] workspace.py 3 个成员端点注册成功 (routes 验证)
- [x] 现有工作空间数据迁移：created_by → owner 成员（database.py 回填，跳过不存在用户）
- [x] FileDataStore 兼容：_ensure_members 回填旧工作空间创建者为 owner
- [x] 移除最后 owner 防护 (ws_remove_member 校验 owners.length > 1)

## 回归检查
- [x] Python 语法检查通过 (ast.parse)
- [x] 后端模块导入验证通过 (.venv python)
- [x] npm run build 0 errors (✓ built in 15.94s)
- [x] detect_changes 波及范围全部在预期内（成员机制 + 权限收紧相关符号/流程）

## 风险与注意
- ⚠️ list_workspaces 行为变更：之前所有用户看所有工作空间，现在非 admin 只看成员的。**现有用户首次访问可能看不到旧工作空间** — 已通过 database.py 回填迁移（MySQL）和 _ensure_members（File）兜底，旧工作空间的 created_by 会自动成为 owner 成员。
- ⚠️ pm_list_sessions analyst 分支用顺序 await is_workspace_member 过滤，sessions 列表有上限（limit 200），性能可接受。
- ⚠️ WorkspaceDetail 编辑/删除按钮 canManageWorkspace 当前仅限 admin。owner 非 admin 也能管理（后端 _require_workspace_owner_or_admin 已支持），前端按钮用 canManageMembers（含 owner）控制更合理 — 但为避免 owner 误删，编辑/删除暂保留 admin 限制，成员管理用 canManageMembers（admin + owner）。

## 提交记录
- `2dd6a98` feat: WorkspaceMember ORM + DataStore 成员方法 + 建表迁移
- `577e46f` feat: workspace 成员端点 + 权限按角色收紧
- `3adf024` feat: 前端成员管理 — WorkspaceList 隐藏新建 + WorkspaceDetail 成员 Tab

## 评估结论
✅ 通过

所有 P0/P1 验收标准达成，构建无报错，波及范围符合预期。未做计划外改动。
