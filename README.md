<div align="center">

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Vue_3-4DD8A6?style=for-the-badge&logo=vue.js&logoColor=white" alt="Vue 3">
<img src="https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
<img src="https://img.shields.io/badge/LangGraph-0.3+-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph">
<img src="https://img.shields.io/badge/MySQL_8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL">
<img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
<img src="https://img.shields.io/badge/License-Apache_2.0-D22128?style=for-the-badge&logo=apache&logoColor=white" alt="License">

</div>

<br>

# ReQCollect

> 企业 IT 业务需求分析师 — 通过多轮对话挖掘业务需求，自动产出可供开发团队直接落地的需求文档。

<br>

<details open>
<summary><b>工作流程预览</b></summary>

```
用户: "我想做一个企业内部的报销审批系统"

ReQCollect: 您好！很高兴能帮您梳理这个报销审批系统的需求。
           先问两个最基础的问题：

           【单选】目前公司的报销业务是怎么操作的？
           A. 完全纸质单据，手工流转审批
           B. 部分电子化（钉钉/企微填单，但审批还是线下）
           C. 有现成的系统但不好用想替换
           D. 其他情况

           【单选】这次做报销系统，主要为了解决什么核心痛点？
           A. 审批流程太慢，员工垫资周期长
           B. 报销标准难管控，经常超标
           C. 财务审核工作量大，手工对账易出错
           D. 以上都有

用户: "A 和 C，纸质报销太慢了，财务也累"

ReQCollect: 明白了 [更新: 业务背景与痛点 ✅, 现状流程 ✅]

           【多选】这个流程涉及哪些角色？
           A. 普通员工 — 提交报销
           B. 部门经理 — 审批
           C. 财务人员 — 复核、付款
           D. 总经理 — 查看汇总报表
           E. 以上都有，还有其他

           【单选】目前跟哪些系统有数据交互？
           A. 用友ERP
           B. OA系统
           C. 没有对接，全是手工
           D. 其他

用户: "涉及员工、经理、财务、总经理。跟用友要对接收付款数据"

ReQCollect: 好的 [更新: 使用角色 ✅, 系统对接 ✅]

           ── 当前需求完整度: 52% ──
           已覆盖: 项目名称, 业务背景, 现状流程, 使用角色, 系统对接
           待挖掘: 业务流程, 功能需求, 非功能需求, 数据量级...

          接下来确认一下核心业务流程...

...

ReQCollect: ── 当前需求完整度: 78% ──
           信息比较充分了，要我生成需求文档吗？

用户: "生成"

ReQCollect: [开始生成 9 章 PRD]
           1. 项目背景与目标 ✅
           2. 用户角色与用例 ✅
           3. 业务流程 ✅
           4. 功能需求 ✅
           5. 系统集成 ✅
           ...
           9. 验收标准 ✅
           ── 需求文档生成完毕 ──
```

</details>

---

## 设计理念

ReQCollect 专注于**企业内部 IT 系统的需求采集与分析**场景，与通用的产品经理类工具不同：

| 维度 | 传统产品经理工具 | ReQCollect |
|------|----------------|------------|
| 人设 | 产品经理，关注市场定位 | **企业 IT 需求分析师**，关注业务现状 |
| 对话引导 | "行业领域？核心价值？" | **"现在怎么跑的？痛点是什么？跟什么系统对接？"** |
| 画像字段 | product_type, industry, elevator_pitch | **business_background, current_process, existing_systems, data_scale** |
| PRD 章节 | 项目概述、功能需求、附录 | **项目背景、业务流程、系统集成、数据需求、实施约束** |
| 组织方式 | 扁平会话列表 | **工作空间（项目级）+ 树状导航 + Wiki 文库 + 需求图谱** |
| 部署依赖 | MySQL + Redis + 向量库 | **可选 MySQL，一键 Docker 启动** |

---

## 功能架构

```
┌────────────────────────────────────────────────────────┐
│                   用户入口 (浏览器)                       │
│         Vue 3 SPA + Vite + Element Plus + TypeScript    │
├────────────────────────────────────────────────────────┤
│                       左侧栏                             │
│  Brand · 搜索 · 新建工作空间                              │
│  ┌─ 📁 工作空间 A (展开)                                 │
│  │   ├ ＋ 新建会话                                       │
│  │   ├ 📄 导入需求文档                                    │
│  │   ├ 💬 会话 1                                         │
│  │   └ 💬 会话 2                                         │
│  ├ 📁 工作空间 B (折叠)                                   │
│  └ 📋 未分类会话                                         │
├────────────────────────────────────────────────────────┤
│    Main Area (对话区 / 工作空间详情 / Wiki / 图谱)        │
├────────────────────────────────────────────────────────┤
│               FileTreePanel (文件侧栏)                    │
└────────────────────────────────────────────────────────┘
```

### 模块关系

```
工作空间（项目级组织单元）
  ├── 对话 Session（挖需求）
  │   └── 需求条目 → 关联 Wiki 页面
  ├── Wiki 文库（需求详情 / 知识沉淀）
  │   └── [[Wikilink]] 页面间链接 → 反向索引
  └── 需求图谱（Graph View）
        └── vis-network 力导向图
        └── 节点 = Wiki 页面，边 = [[链接]]
```

---

## 技术栈

| 层 | 技术 | 用途 |
|:--|:-----|:-----|
| 前端 | Vue 3 + Vite + TypeScript + Element Plus | SPA 三栏布局 |
| 状态管理 | Pinia | 会话/认证/画像 |
| 图谱 | vis-network + vis-data | 需求可视化 |
| 对话 Agent | LangGraph ReAct | 多轮需求挖掘 |
| 持久化 | MySQL 8.0 / JSON 文件回退 | 7 张业务表 |
| 生成模型 | OpenAI 兼容 API (DeepSeek/OpenAI 等) | 对话 & PRD 生成 |
| 部署 | Docker Compose / Vite + uvicorn | 一键启动 |

---

## 快速开始

### 前置条件

- Node.js 18+（前端构建） + Python 3.11+（后端） 或 Docker
- 一个 OpenAI 兼容的 LLM API（DeepSeek、OpenAI 等）

### 方式一：Docker Compose（推荐，含 MySQL + 全功能）

```bash
git clone https://github.com/StarTower6/ReQCollect.git
cd ReQCollect

# 1. 配置环境变量
cp .env.example .env.docker
# 编辑 .env.docker 填入 LLM_API_KEY

# 2. 构建前端（Docker 会从本地 dist/ 复制）
cd reqcollect-web
npm install && npm run build
cd ..

# 3. 启动
docker compose up -d

# 4. 访问
# http://localhost:8082          — Nginx 反向代理（推荐）
# http://localhost:9900          — 直连应用
# http://localhost:9900/docs     — Swagger API 文档
```

### 方式二：本地开发（无 MySQL，JSON 文件回退）

**后端：**

```bash
git clone https://github.com/StarTower6/ReQCollect.git
cd ReQCollect

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # 编辑 .env 填入 LLM_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 9900
```

**前端（另一终端）：**

```bash
cd reqcollect-web
npm install
npm run dev
```

打开 `http://localhost:5173`（Vite 开发服务器，自动代理 API 到后端）。

### 默认账号

```
管理员: admin / admin123
```

---

## 核心功能

| 功能 | 说明 |
|:-----|:-----|
| **工作空间管理** | 项目级 CRUD，会话隔离，成员管理（开发中） |
| **多轮需求挖掘** | AI 驱动的对话式需求采集，11 个画像字段加权评估 |
| **PRD 自动生成** | 9 章标准 PRD，支持一次性生成与增量续写 |
| **Wiki 文库** | 工作空间内 Markdown 知识沉淀，分栏编辑 + 实时预览 |
| **[[链接]] 系统** | Wiki 页面间引用，自动解析与反向索引 |
| **需求图谱** | 工作空间级力导向图，节点 = Wiki 页面，边 = 引用关系 |
| **文件管理** | 工作空间内文件目录树，AI 自动关联到会话上下文 |
| **用户管理** | 管理员后台，CRUD + 状态管理 |
| **数据看板** | 会话/PRO 趋势统计 |
| **数据导出** | CSV / XLSX 导出会话和 PRD |

---

## API 概览

| 方法 | 端点 | 说明 |
|:-----|:-----|:-----|
| `POST` | `/api/auth/login` | 登录 (JWT) |
| `POST` | `/api/pm/chat` | 需求挖掘对话 (SSE) |
| `POST` | `/api/pm/generate` | 生成 PRD (SSE) |
| `POST` | `/api/pm/agent` | 自动路由 (SSE) |
| `GET` | `/api/pm/sessions` | 会话列表 |
| `GET` | `/api/pm/profile/{id}` | 查看需求画像 |
| `GET` | `/api/pm/prd/{id}` | 查看 PRD |
| `POST/GET/PATCH/DELETE` | `/api/workspaces` | 工作空间 CRUD |
| `POST/GET/PATCH/DELETE` | `/api/wiki` | Wiki 页面 CRUD |
| `GET` | `/api/wiki/graph/{id}` | 需求图谱数据 |
| `POST` | `/api/auth/register` | 注册用户 |
| `GET/PATCH/DELETE` | `/api/auth/users` | 用户管理 (admin) |
| `GET` | `/api/health` | 健康检查 |

---

## 配置

| 变量 | 默认值 | 说明 |
|:-----|:-------|:-----|
| `LLM_API_KEY` | **必填** | LLM API Key |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | API 地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名 |
| `SUFFICIENCY_THRESHOLD` | `0.75` | 触发 PRD 生成的完整度阈值 |
| `DATA_DIR` | `./pm_data` | 数据持久化目录 |
| `MYSQL_HOST` | `(空)` | MySQL 地址，留空自动回退 JSON 文件 |
| `MYSQL_USER` | `reqcollect` | MySQL 用户 |
| `MYSQL_DATABASE` | `reqcollect` | MySQL 数据库名 |

---

## 项目结构

```
ReQCollect/
├── app/
│   ├── agent/pm/              PM Agent 两阶段管线
│   │   ├── phase1/            Phase 1: 对话挖需
│   │   │   ├── mining_agent.py    ReAct Agent
│   │   │   ├── profile_extractor.py  正则保底提取
│   │   │   └── sufficiency.py    完整度评分
│   │   ├── phase2/            Phase 2: PRD 生成
│   │   │   ├── planner.py        章节规划
│   │   │   ├── generator.py      LLM 生成
│   │   │   └── assembler.py      Markdown 拼装
│   │   ├── prompts.py          人设提示词
│   │   ├── state.py            画像字段定义
│   │   └── tools.py            LangChain 工具
│   ├── api/
│   │   ├── pm.py              核心 API (SSE 流式)
│   │   ├── auth.py             认证 & 用户管理
│   │   ├── workspace.py        工作空间 CRUD
│   │   └── wiki.py             Wiki + 图谱 API
│   ├── core/
│   │   ├── auth.py             JWT 认证
│   │   ├── llm_factory.py      LLM 适配器
│   │   └── workspace.py        数据迁移工具
│   ├── db/
│   │   ├── __init__.py         DataStore 抽象协议
│   │   ├── models.py           8 个 ORM 模型
│   │   ├── repository.py       MySQLDataStore
│   │   ├── compat.py           FileDataStore (JSON)
│   │   └── database.py         异步 SQLAlchemy 引擎
│   ├── services/
│   │   └── pm_agent_service.py 业务编排
│   ├── main.py                 FastAPI 入口
│   └── config.py               配置管理
├── reqcollect-web/             Vue 3 前端 (Vite + TS)
│   ├── src/
│   │   ├── components/         UI 组件
│   │   ├── views/              页面
│   │   │   ├── wiki/           Wiki 阅读/编辑器 + 图谱
│   │   │   └── admin/          用户管理
│   │   ├── stores/             Pinia 状态
│   │   ├── api/                API 客户端
│   │   └── router/             路由
│   ├── vite.config.ts
│   └── package.json
├── scripts/
│   ├── migrate_json_to_mysql.py
│   └── init.sql
├── Dockerfile                  多阶段构建（含前端编译）
├── docker-compose.yml          Nginx + App + MySQL
├── nginx.conf                  SSE 优化反向代理
└── .env.example                配置模板
```

---

## 许可

[Apache License 2.0](LICENSE)

## 致谢

基于 [PMAgent](https://github.com/Tomato-love-potato/PMAgent) (Apache 2.0) 二次开发，保留了核心的两阶段挖需→生成架构，重构了人设、字段、模板和基础设施。
