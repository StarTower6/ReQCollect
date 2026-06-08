# Plan: 08 — 去技术化：提示词与 PRD 输出聚焦业务

## 1. 任务理解
- 需求来源: commit `829e375` 确立的方向 — 挖需提示词和 PRD 输出去技术化
- 核心目标: 将 commit 829e375 的理念延伸到所有用户可见的提示词、标签、字段名

## 2. 改动清单

### 修改文件
- `app/agent/pm/prompts.py` — PRD section 6 标题 "非功能需求" → "质量与性能要求"；section 8 "技术路线约束" → "外部依赖约束"
- `app/agent/pm/prompts_import.py` — 导入 prompt 中字段名 "非功能需求" → "质量与性能要求"
- `app/agent/pm/state.py` — `non_functional` → `quality_requirements`（字段名）；`"mining"` → `"gathering"`（阶段枚举）；注释中 P0 → 业务优先级
- `app/agent/pm/phase1/sufficiency.py` — "非功能需求" 标签 → "质量与性能要求"；约束条件问题中 "技术路线" → "合规"
- `app/agent/pm/phase1/profile_extractor.py` — `non_functional` 引用 → `quality_requirements`
- `app/agent/pm/phase2/generator.py` — LLM prompt 中 "professional Markdown" → 不提及 Markdown
- `app/agent/pm/phase2/assembler.py` — 默认标题 "Product Requirements Document" → "产品需求文档"
- `app/agent/pm/tools.py` — `non_functional` 字段引用 → `quality_requirements`；`LangChain tools` → `PM agent tools`
- `app/db/models.py` — 枚举值 `mining` → `gathering`
- `app/db/compat.py` — `non_functional` 字段引用
- `reqcollect-web/src/views/ChatView.vue` — "mining" 模式文本 → "收集需求中"
- 前端各类标签

## 3. 不做的事项
- API 路由路径不改（/api/pm/chat → /api/pm/chat 保留）
- 函数签名不改（不破坏调用链）
- 数据库字段名不改（不破坏存储兼容性）
- 不改 commit 829e375 已改好的内容

## 4. 验收标准
- [x] P0: PRD section 6 标题改为 "质量与性能要求"
- [x] P0: PRD section 8 "技术路线约束" → "外部依赖约束"
- [x] P0: 字段 "非功能需求" → "质量与性能要求"
- [x] P0: "充分度/充分" → "完整度/完成"
- [x] P0: Generator prompt 不再提及 Markdown
- [x] P0: 默认文档标题改为中文
- [x] P0: "sufficiency" → "completeness" 在用户可见处
- [x] P1: 阶段名 "mining" → "gathering"（session status 枚举）
- [x] P1: 约束问题不涉及技术路线
- [x] P1: 前端会话状态标签更新

## 5. 风险与依赖
- 字段名 `non_functional` → `quality_requirements` 改的是 profile dict 的 key，影响 tools.py get_profile/save_profile 的读写
- 阶段名 `mining` → `gathering` 影响 DB 中已有的 session 数据，需兼容读取
- 前端解析 status 枚举值需同步更新
