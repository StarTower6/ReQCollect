# ReQCollect — 企业级业务需求采集与分析平台

## 项目概述

AI 驱动的多轮对话需求挖掘平台。业务人员通过对话描述需求，AI 引导完善画像，
自动生成结构化需求文档（PRD）。位于格力大数据中心。

## 技术栈

- **后端**: Python 3.11+ / FastAPI / LangGraph / langchain-openai
- **数据库**: MySQL 8.0 (开发环境可使用 JSON 文件回退)
- **前端**: 原生 HTML/CSS/JS + marked.js (保留原版设计系统)
- **LLM**: DeepSeek V4 (兼容 OpenAI API 格式)
- **部署**: uvicorn 单进程 / Docker

## 目录结构

```
├── app/
│   ├── main.py              FastAPI 入口
│   ├── config.py            配置 (pydantic-settings)
│   ├── api/pm.py            REST API 端点 (SSE 流式)
│   ├── agent/pm/
│   │   ├── prompts.py       人设提示词 + PRD 模板
│   │   ├── tools.py         需求画像工具函数
│   │   ├── state.py         状态定义
│   │   └── phase1/          Phase 1: 对话挖需 (ReAct Agent)
│   │       ├── mining_agent.py
│   │       ├── sufficiency.py    完整度评估器
│   │       └── profile_extractor.py  规则提取器
│   │   └── phase2/          Phase 2: PRD 生成管线
│   │       ├── planner.py
│   │       ├── generator.py
│   │       └── assembler.py
│   ├── core/llm_factory.py  LLM 适配
│   ├── models/pm.py         请求模型
│   └── services/pm_agent_service.py  业务编排
├── static/index.html        前端 (1828 行)
├── docs/requirements/       需求文档 (7 个模块)
│   ├── 01-对话挖需引擎/
│   ├── 02-PRD生成管线/
│   ├── 03-用户与权限/
│   ├── 04-存储与数据/
│   ├── 05-企业微信集成/
│   ├── 06-部署与运维/
│   └── 07-前端界面/
├── .claude/skills/          安装的 Claude Code 技能
│   ├── design/              UI/UX Pro Max
│   └── impeccable/          Impeccable 设计系统
├── .env                     配置 (不提交)
└── pyproject.toml           依赖管理
```

## Git 规范

- post-commit hook 自动推送到 GitHub: git@github.com:StarTower6/ReQCollect.git
- 分支策略: 直接操作 master (small team)
- post-commit hook 在 .git/hooks/post-commit

## 设计约束

- **保留原版 CSS 设计系统**，不要用框架默认样式替换
- 前端是原生 HTML/CSS/JS (1828 行单页)，不要转成 React/Vue 全家桶
- 存储先用 JSON 文件，后期迁移 MySQL 8.0
- 所有 API 端点路径 /api/pm/* 不要改

## 开发流程（PGE 三段式强制规则）

任何代码改动——包括新功能、bug 修复、提示词调整——必须严格遵循 PGE 三段式：

### Plan
- 写入 `.execution/<feature-name>/plan.md`
- 包含：任务理解、**使用 gitnexus 分析和判断改动文件**、验收标准（P0/P1）、实施步骤
- **MUST 使用 `mcp__gitnexus__query` 查找相关符号和 execution flow**
- **MUST 使用 `mcp__gitnexus__context` 获取要修改符号的完整上下文**
- **MUST 使用 `mcp__gitnexus__impact` 分析修改的波及范围并在 plan.md 中记录**
- 展示给用户确认后再进入 Generate

### Generate
- 写入 `.execution/<feature-name>/tasks.md`，每步 `- [ ]`
- 按 plan 执行，实时更新 tasks.md（完成后改为 `- [x]` + commit 引用）
- 不做计划外的改动

### Evaluate
- 写入 `.execution/<feature-name>/report.md`
- 逐条验证验收标准
- 回归检查、冲突检测
- 提交所有改动（plan.md + tasks.md + report.md + 代码）

> 不允许跳过任一阶段。不允许"顺便改一下"。

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **ReQCollect** (3367 symbols, 6898 relationships, 249 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/ReQCollect/context` | Codebase overview, check index freshness |
| `gitnexus://repo/ReQCollect/clusters` | All functional areas |
| `gitnexus://repo/ReQCollect/processes` | All execution flows |
| `gitnexus://repo/ReQCollect/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
