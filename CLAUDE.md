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
