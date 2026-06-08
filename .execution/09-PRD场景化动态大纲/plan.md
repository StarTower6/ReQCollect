# Plan: 09 — PRD 场景化动态大纲

## 1. 任务理解
- 需求来源: docs/requirements/02-PRD生成管线/README.md
- 核心目标: PRD 生成时根据需求画像自动识别项目类型 → 生成匹配的场景化大纲，不再固定 9 章
- 现状: planner.py 固定 PRD_SECTION_ORDER 9 章，所有项目同模板
- 改动限制: 不改 assembler、generator、service、API、前端

## 2. 改动清单
- 修改: `app/agent/pm/phase2/planner.py` — 新增 SceneRecognizer + DynamicPlanner
- 修改: `app/agent/pm/prompts.py` — 新增场景化 prompt 覆盖层
- 不改: generator.py、assembler.py、service.py、api/pm.py、前端

## 3. 验收标准
- [x] P0: AI 自动识别场景（改造/报表/审批/新建等），不依赖用户选择
- [x] P0: 不同场景输出不同的大纲长度和章节组合
- [x] P0: 场景识别仅用关键词匹配，不额外调用 LLM
- [x] P0: SSE 事件格式完全不变，前端无需改动
- [x] P0: `plan()` 签名不变，调用方（service/assembler）无需改动
- [x] P1: 7 种场景 + 1 默认覆盖

## 4. 风险与依赖
- 向后兼容：现有 profile 无场景字段，SceneRecognizer 从已有字段推断
- 与现有测试不冲突：plan() 签名不变，返回的 sections 结构不变

## 5. 实施步骤
1. 重写 planner.py — SceneRecognizer + SceneType + DynamicPlanner
2. 扩展 prompts.py — PRD_SCENE_PROMPT_OVERRIDES 覆盖层
3. 验证 — 测试各场景输出正确的大纲
