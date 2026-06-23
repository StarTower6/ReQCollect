# Report: model-refactor — 实体关系重构

## 验收标准验证
- [x] P0: Workspace 类新增 `discussions` / `proposals` relationship → ✅ OK
- [x] P0: Session 类新增 `workspace_ref` / `proposals` relationship → ✅ OK
- [x] P0: RequirementProposal 类新增 `discussion_ref` / `workspace_ref` / `submitter_ref` → ✅ OK
- [x] P0: 应用启动后所有 relationship 可正常访问 → ✅ OK（8/8）
- [x] P1: `models.py` 末尾加 4 个别名 → ✅ OK（Discussion=Session, Proposal=RequirementProposal 等）
- [x] P1: `GeneratedPRD` 新增 `source_proposal_ids` JSON 字段，建表迁移幂等 → ✅ OK
- [x] P1: 从对话提炼提案时自动填充 `submitter_id` → ✅ OK
- [x] P1: `python -c "from app.db.models import Discussion, Proposal"` 不报错 → ✅ OK

## 回归检查
- [x] `/api/health` 返回 200 → ✅ `{"status":"ok","backend":"mysql"}`
- [x] 所有 50 个 API 路由未被误删 → ✅ OK
- [x] 关键端点（/chat, /extract-proposal, /workspaces 等）全部存在 → ✅
- [x] 别名导入无错误 → ✅ OK
- [x] `app.main:app` 正常启动 → ✅（自动部署通过）
- [x] GitNexus 已重新索引 → ✅

## 代码质量
- [x] 没有硬编码密码/API Key
- [x] 没有修改已有代码（只追加）
- [x] 没有修改数据库表名或 API 路径

## 评估结论
✅ **通过** — 所有 P0/P1 验收标准已满足，全回归检查通过。

## 改动统计
| 文件 | 改动 | 说明 |
|------|------|------|
| app/db/models.py | +48 lin | 8 个 relationship + 4 个别名 + 1 个字段 |
| app/db/database.py | +11 lines | 幂等迁移 |
| app/agent/pm/proposal_extractor.py | +6 lines | submitter_id |
| app/api/pm.py | +5 lines | current_user 注入 |
