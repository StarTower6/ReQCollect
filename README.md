<div align="center">

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Vue_3-4DD8A6?style=for-the-badge&logo=vue.js&logoColor=white" alt="Vue 3">
<img src="https://img.shields.io/badge/LangGraph-0.3+-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph">
<img src="https://img.shields.io/badge/MySQL_8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL">
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
| 部署依赖 | MySQL + Redis + 向量库 | **可选 MySQL，一键 Docker 启动** |

---

## 架构

```
┌──────────────────────────────────────────────┐
│        用户入口 (浏览器 80/9900)              │
│     Vue 3 三栏前端 + Swagger / REST API      │
└──────────────────────┬───────────────────────┘
                       │ SSE 流式
┌──────────────────────▼───────────────────────┐
│              FastAPI 服务层                    │
│  POST /api/pm/chat      Phase 1 对话挖需     │
│  POST /api/pm/generate  Phase 2 生成 PRD     │
│  POST /api/pm/agent     自动路由              │
│  GET  /api/pm/profile   查看需求画像          │
│  GET  /api/pm/sessions  会话列表 (持久化)     │
│  GET  /api/pm/dashboard/overview   数据看板   │
│  GET  /api/pm/export/sessions      导出       │
└──────────────┬──────────────┬────────────────┘
               │              │
    ┌──────────▼──┐    ┌─────▼──────────┐
    │ Phase 1     │    │ Phase 2        │
    │ 对话挖需     │    │ PRD 生成管线   │
    │ LangGraph   │    │ Planner→Gen→   │
    │ ReAct Agent │    │ →Assembler     │
    │ 正则保底提取 │    │ 9 章 Markdown │
    │ 完整度评估   │    │                │
    └──────────┬──┘    └─────┬──────────┘
               │             │
               └──────┬──────┘
                      │
         ┌────────────▼────────────┐
         │    DataStore 抽象层      │
         │    (策略模式)           │
         └──────┬────────────┬─────┘
                │            │
    ┌───────────▼──┐   ┌────▼──────────┐
    │ MySQLDataStore│   │ FileDataStore │
    │ asyncmy+SQLA │   │ JSON 文件回退 │
    │ 6 张业务表   │   │ 零配置开发    │
    └──────────────┘   └───────────────┘
```

| 层 | 技术 | 用途 |
|:--|:-----|:-----|
| 前端 | Vue 3 CDN + Element Plus + highlight.js | 三栏布局，零构建 |
| 对话 Agent | LangGraph ReAct | 多轮需求挖掘 |
| 持久化 | MySQL 8.0 / JSON 文件回退 | 会话、画像、消息、PRD |
| 生成模型 | OpenAI 兼容 API (DeepSeek/OpenAI 等) | 对话 & 文档生成 |
| 部署 | Docker Compose / uvicorn | 一键启动 |

---

## 快速开始

### 前置条件

- Python 3.11+ 或 Docker
- 一个 OpenAI 兼容的 LLM API（DeepSeek、OpenAI 等）

### 方式一：本地运行（无需 MySQL）

```bash
git clone https://github.com/StarTower6/ReQCollect.git
cd ReQCollect

python -m venv .venv && source .venv/bin/activate
pip install -e "."

cp .env.example .env   # 编辑 .env 填入你的 API Key
uvicorn app.main:app --host 0.0.0.0 --port 9900
```

打开 `http://localhost:9900` 开始对话。

### 方式二：Docker Compose（含 MySQL，推荐）

```bash
cp .env.example .env.docker   # 编辑填入 API Key
docker compose up -d
```

打开 `http://localhost`（Nginx 反向代理）或 `http://localhost:9900`（直连应用）。

### API 文档

`http://localhost:9900/docs` — Swagger UI

---

## 前端界面

三栏布局 — 会话列表 + 对话区 + 需求画像面板：

```
┌──────────┬──────────────────────┬──────────────┐
│  会话列表 │      对话区          │  需求画像     │
│  搜索框  │    消息气泡          │  ⏺ 完整度环  │
│  会话列表 │    Markdown 渲染     │  ● 已填字段  │
│  ＋新建   │    快捷回复          │  ○ 待填字段  │
│          │    输入框            │  💡 缺失引导  │
│  260px   │    flex 自适应       │  300px       │
│          │                      │  <1200→抽屉  │
└──────────┴──────────────────────┴──────────────┘
```

- 右侧**需求画像面板**实时显示完整度进度环、11 个字段状态（绿色/灰色圆点）
- 点击已填字段展开详情
- 缺失字段智能引导提示
- 窗口 <1200px 时右侧折叠为抽屉
- 消息头像 + 时间戳 + 代码高亮 + 复制按钮

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

## API

| 方法 | 端点 | 说明 |
|:-----|:-----|:-----|
| `POST` | `/api/pm/chat` | 需求挖掘对话 (SSE 流式) |
| `POST` | `/api/pm/generate` | 生成 PRD (SSE 流式) |
| `POST` | `/api/pm/continue` | 增量模式下一章 (SSE 流式) |
| `POST` | `/api/pm/agent` | 自动路由 (SSE 流式) |
| `GET` | `/api/pm/sessions` | 会话列表（持久化） |
| `GET` | `/api/pm/history/{id}` | 会话历史消息 |
| `GET` | `/api/pm/profile/{id}` | 查看需求画像 |
| `GET` | `/api/pm/prd/{id}` | 查看已生成的 PRD |
| `DELETE` | `/api/pm/sessions/{id}` | 删除会话 |
| `GET` | `/api/pm/dashboard/overview` | 数据看板概览 |
| `GET` | `/api/pm/dashboard/trend` | 趋势统计 |
| `GET` | `/api/pm/export/sessions` | 导出会话 (CSV/XLSX) |
| `GET` | `/api/pm/export/prds` | 导出 PRD (CSV/XLSX) |
| `GET` | `/api/health` | 健康检查 |

### SSE 事件流

| 事件 | 阶段 | 说明 |
|:-----|:----:|:-----|
| `content` | 挖需 | AI 回复 token 流 |
| `sufficiency` | 挖需 | 完整度评分与缺失字段 |
| `ready_to_generate` | 挖需 | 完整度达标，建议生成 PRD |
| `prd_plan` | 生成 | 9 章节目录 |
| `section_start/complete` | 生成 | 每章进度 |
| `section_content` | 生成 | 章节内容 token 流 |
| `prd_complete` | 生成 | 完整 PRD Markdown |

---

## 需求画像字段

| 字段 | 权重 | 说明 |
|:-----|:----:|:-----|
| project_name | 10% | 项目名称 |
| business_background | 15% | 业务背景与痛点 |
| current_process | 10% | 现状流程 |
| user_roles | 8% | 使用角色与部门 |
| business_flow | 12% | 核心业务流程 |
| functional_requirements | 15% | 功能需求清单 |
| existing_systems | 5% | 现有系统对接 |
| non_functional | 10% | 非功能需求 |
| data_scale | 5% | 数据量与并发 |
| constraints | 5% | 实施约束 |
| success_criteria | 5% | 验收标准 |

---

## 项目结构

```
ReQCollect/
├── app/
│   ├── agent/pm/
│   │   ├── phase1/
│   │   │   ├── mining_agent.py       ReAct Agent · 需求对话
│   │   │   ├── profile_extractor.py   正则 · 保底提取
│   │   │   └── sufficiency.py         完整度加权评分
│   │   ├── phase2/
│   │   │   ├── planner.py             章节规划
│   │   │   ├── generator.py           LLM 生成器
│   │   │   └── assembler.py           Markdown 拼装
│   │   ├── prompts.py                 业务需求分析师人设
│   │   ├── state.py                   画像字段定义
│   │   └── tools.py                   LangChain 工具
│   ├── api/pm.py                      REST API 端点
│   ├── core/llm_factory.py            LLM 适配器
│   ├── models/pm.py                   请求模型
│   ├── services/pm_agent_service.py  两阶段编排
│   ├── config.py                      配置管理
│   ├── main.py                        FastAPI 入口 + 启动校验
│   └── db/                            数据存储层
│       ├── database.py                异步 SQLAlchemy 引擎
│       ├── models.py                  6 个 ORM 模型
│       ├── repository.py              MySQLDataStore
│       └── compat.py                  FileDataStore (JSON 回退)
├── static/
│   └── index.html                     Vue 3 三栏前端
├── scripts/
│   ├── migrate_json_to_mysql.py       JSON → MySQL 迁移
│   └── init.sql                       MySQL 初始化 DDL
├── Dockerfile                         多阶段构建
├── docker-compose.yml                 Nginx + App + MySQL
├── nginx.conf                         SSE 优化反向代理
├── gunicorn.conf.py                   多 worker 配置
├── .env.example                       配置模板
├── .env.docker                        Docker 环境配置
├── pyproject.toml                     依赖管理
└── LICENSE                            Apache 2.0
```

---

## PRD 输出格式

```
1. 项目背景与目标     业务现状 · 痛点 · 目标 · 范围
2. 用户角色与用例     角色定义 · 权限矩阵 · 操作场景
3. 业务流程           主流程 · 分支流程 · 异常处理
4. 功能需求           模块 · 功能列表 · P0/P1 优先级 · 验收条件
5. 系统集成           对接系统 · 集成方式 · 数据流向
6. 非功能需求         性能 · 安全 · 合规 · 可用性
7. 数据需求           数据量 · 存储 · 归档 · 报表
8. 实施约束与风险     工期 · 预算 · 依赖 · 风险
9. 验收标准           量化指标 · 验收流程 · 交付物
```

---

## 数据迁移

从 JSON 文件迁移到 MySQL：

```bash
python scripts/migrate_json_to_mysql.py
```

---

## 开发

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 许可证

[Apache License 2.0](LICENSE)

## 致谢

基于 [PMAgent](https://github.com/Tomato-love-potato/PMAgent) (Apache 2.0) 二次开发，保留了核心的两阶段挖需→生成架构，重构了人设、字段、模板和基础设施。
