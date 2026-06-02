<div align="center">

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/LangGraph-0.3+-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph">
<img src="https://img.shields.io/badge/DeepSeek-V4-4B32C3?style=for-the-badge&logo=openai&logoColor=white" alt="DeepSeek V4">
<img src="https://img.shields.io/badge/Milvus-2.4+-00AEAE?style=for-the-badge&logo=milvus&logoColor=white" alt="Milvus">
<img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">

</div>

<br>

# PM Agent

> 资深 AI 产品经理 — 像真人 PM 一样对话挖掘需求，自动生成专业 PRD 文档。

<br>

<p align="center">
  <img src="https://raw.githubusercontent.com/nicedoc/screenshots/main/conversation.svg" width="700" alt="PM Agent Flow">
</p>

<details open>
<summary><b>工作流程预览</b></summary>

```
用户: "我想做一个企业报销审批系统"

PM Agent: 好的，让我们来梳理一下需求。首先，这个系统主要是给
         哪些角色使用的？目前我想到的有：
         
         1. 普通员工 — 提交报销申请
         2. 部门经理 — 审批报销
         3. 财务人员 — 复核放款
         
         还有其他角色吗？另外，你们现有的财务系统是什么？

用户: "还有总经理需要看汇总报表。财务用的是用友"

PM Agent: 明白了 [更新需求画像: user_roles ✅]
         那审批流程是单人批完就过，还是需要多级会签？
         比如超过5000元的报销需要经理+财务双重审批？

用户: "对，5000以上双审批"

PM Agent: 好的 [更新: functional_modules ✅]
         
         ── 📊 当前需求完整度: 65% ──
         已覆盖: 项目名称, 用户角色, 审批规则
         待挖掘: 非功能需求, 业务流程, 系统集成...
         
         接下来确认一下性能方面：预估日均报销单量大约多少？

...

PM Agent: ── 📊 当前需求完整度: 82% ──
         信息比较充分了，要我生成 PRD 吗？

用户: "生成PRD"

PM Agent: [开始生成 8 章 PRD]
         1. 项目概述 ✅
         2. 用户角色分析 ✅
         ...
         8. 附录 ✅
         ── PRD 生成完毕 ──
```

</details>

---

## 架构

<table>
<tr>
<td width="50%">

```
  用户界面
    ↕ SSE
┌─────────────────────┐
│   PM Agent Service  │
│                     │
│  ┌── 阶段1 ────────┐│
│  │ ReAct Agent     ││
│  │  ├ 知识检索     ││
│  │  ├ 需求画像     ││
│  │  └ 充分度评估   ││
│  └────────┬────────┘│
│           ↓         │
│  ┌ RequirementProfile ┐│
│  └────────┬────────┘│
│           ↓         │
│  ┌── 阶段2 ────────┐│
│  │ PRD 流水线      ││
│  │  ├ Planner      ││
│  │  ├ Generator    ││
│  │  └ Assembler    ││
│  └─────────────────┘│
└─────────────────────┘
```

</td>
<td width="50%">

| 层 | 技术 | 用途 |
|:--|:-----|:-----|
| 对话 Agent | LangGraph ReAct | 多轮需求挖掘 |
| 会话状态 | Redis | 对话历史持久化 |
| 知识检索 | Milvus | 经验文档语义搜索 |
| 数据持久化 | MySQL | 画像+PRD 存储 |
| 生成模型 | DeepSeek V4 | 对话 & 文档生成 |
| 嵌入模型 | BGE-M3 | 1024 维向量化 |
| 部署 | Docker Compose | 一键多节点 |

</td>
</tr>
</table>

---

## 快速开始

### 前置依赖

| 服务 | 端口 | 用途 |
|:-----|:-----|:-----|
| Milvus | 19530 | 向量数据库，存储知识文档 |
| Redis | 6379 | LangGraph 会话检查点 |
| MySQL 8.0 | 3306 | 需求画像 + PRD 持久化 |

### 本地开发

```bash
git clone <repo-url> pm_agent && cd pm_agent

python -m venv .venv && source .venv/Scripts/activate   # Windows
# python -m venv .venv && source .venv/bin/activate      # macOS/Linux

pip install -e ".[dev]"

# 编辑 .env，填入 DEEPSEEK_API_KEY
```

```bash
# 一键启动基础设施
docker run -d --name pm-redis -p 6379:6379 redis:7-alpine
docker run -d --name pm-mysql -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=root_pass \
  -e MYSQL_DATABASE=pm_agent \
  -e MYSQL_USER=pm_agent \
  -e MYSQL_PASSWORD=pm_agent_pass \
  mysql:8.0
docker run -d --name pm-milvus -p 19530:19530 \
  milvusdb/milvus:v2.4.0 milvus run standalone

# 启动应用
python -m uvicorn app.main:app --host 0.0.0.0 --port 9900 --reload
```

> 打开 `http://localhost:9900` 进入聊天界面，`http://localhost:9900/docs` 查看 Swagger API 文档。

### Docker 生产部署

```bash
docker-compose up -d
```

自动拉起 **7 个容器**：

```
 nginx (80) ──→ pm-agent ×2 (9900)
                    ├── mysql (3306)
                    ├── redis (6379)
                    └── milvus (19530) ← etcd ← minio
```

---

## API

### 端点一览

| 方法 | 端点 | 阶段 | 说明 |
|:-----|:-----|:----:|:-----|
| `POST` | `/api/pm/chat` | 1 | 需求挖掘对话 · SSE |
| `POST` | `/api/pm/generate` | 2 | 触发 PRD 生成 · SSE |
| `POST` | `/api/pm/continue` | 2 | 增量模式下一章 · SSE |
| `POST` | `/api/pm/agent` | 1+2 | 便利层自动路由 · SSE |
| `POST` | `/api/pm/upload` | — | 上传经验文档至知识库 |
| `GET` | `/api/pm/profile/{id}` | — | 查看当前需求画像 |
| `GET` | `/api/health` | — | 健康检查 |

### SSE 事件流

<details open>
<summary><b>阶段1 — 需求挖掘</b></summary>

| 事件 | 触发 | 载荷 |
|:-----|:-----|:-----|
| `content` | PM 回复 | 对话 token 流 |
| `profile_update` | 画像变动 | 被更新的字段名 |
| `sufficiency` | 每轮结束 | `{score: 0.65, threshold: 0.75}` |
| `ready_to_generate` | score ≥ 阈值 | 提议生成消息 |

</details>

<details>
<summary><b>阶段2 — PRD 生成</b></summary>

| 事件 | 触发 | 载荷 |
|:-----|:-----|:-----|
| `prd_plan` | 生成开始 | 8 章节目录列表 |
| `section_start` | 每章开始 | 章节标题 + 进度 (n/8) |
| `section_content` | 持续产出 | Markdown token 流 |
| `section_complete` | 每章结束 | 完整章节内容 |
| `awaiting_approval` | 增量暂停 | 下一章标题 |
| `prd_complete` | 全篇完成 | 完整 Markdown PRD |

</details>

### curl 示例

```bash
# 开始对话
curl -X POST "localhost:9900/api/pm/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"我想做一个企业报销审批系统","session_id":"demo-1"}' \
  --no-buffer

# 一键生成 PRD
curl -X POST "localhost:9900/api/pm/generate" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","mode":"one_shot"}' \
  --no-buffer

# 增量模式
curl -X POST "localhost:9900/api/pm/generate" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","mode":"incremental"}' \
  --no-buffer
curl -X POST "localhost:9900/api/pm/continue" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1"}' --no-buffer

# 上传经验文档
curl -X POST "localhost:9900/api/pm/upload" \
  -F "file=@报销系统最佳实践.md" -F "session_id=demo-1"

# 查看需求画像
curl "localhost:9900/api/pm/profile/demo-1" | python -m json.tool
```

---

## 配置

<details open>
<summary><b>.env 完整参考</b></summary>

| 变量 | 默认值 | 说明 |
|:-----|:-----|:-----|
| `DEEPSEEK_API_KEY` | **必填** | DeepSeek 官方 API Key |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 对话模型 |
| `EMBEDDING_API_KEY` | 可选 | Embedding API Key（默认复用 DEEPSEEK_API_KEY） |
| `EMBEDDING_BASE_URL` | `api.siliconflow.cn/v1` | Embedding 服务地址 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 向量嵌入模型 (1024d) |
| `MILVUS_HOST` | `localhost` | Milvus 地址 |
| `MILVUS_PORT` | `19530` | Milvus 端口 |
| `REDIS_URL` | `redis://localhost:6379` | Redis 连接串 |
| `MYSQL_HOST` | `localhost` | MySQL 地址 |
| `MYSQL_PORT` | `3306` | MySQL 端口 |
| `MYSQL_DATABASE` | `pm_agent` | 数据库名 |
| `RAG_TOP_K` | `5` | 知识检索 Top-K |
| `SUFFICIENCY_THRESHOLD` | `0.75` | 需求充分度阈值 |
| `CHUNK_MAX_SIZE` | `800` | 文档分块字符数 |
| `CHUNK_OVERLAP` | `100` | 分块重叠字符数 |

</details>

---

## 项目结构

```
pm_agent/
│
├── app/
│   ├── main.py                              FastAPI 入口 + 生命周期
│   ├── config.py                            pydantic-settings 配置
│   │
│   ├── agent/pm/
│   │   ├── state.py                         RequirementProfile · PMState
│   │   ├── prompts.py                       PM 人设 · 8 章 PRD 模板
│   │   ├── tools.py                         @tool: 画像增删改查
│   │   ├── phase1/
│   │   │   ├── mining_agent.py              ReAct Agent · 需求对话
│   │   │   └── sufficiency.py               结构化输出 · 信息打分
│   │   └── phase2/
│   │       ├── planner.py                   章节规划器
│   │       ├── generator.py                 逐章 LLM 生成器
│   │       └── assembler.py                 Markdown 拼装 · 增量控制
│   │
│   ├── services/
│   │   ├── pm_agent_service.py              两阶段编排 · 多端点路由
│   │   ├── vector_store_manager.py           langchain_milvus 封装
│   │   ├── vector_embedding_service.py       Remote Embedding (1024d)
│   │   ├── vector_index_service.py           文件索引管线
│   │   └── document_splitter_service.py      MD 标题分割 + 合并
│   │
│   ├── db/
│   │   ├── database.py                       Async SQLAlchemy 引擎
│   │   ├── models.py                         profiles + prds 表
│   │   └── repository.py                     ProfileRepository · PRDRepository
│   │
│   ├── api/pm.py                             6 个 HTTP 端点
│   ├── models/pm.py                          Pydantic 请求/响应模型
│   ├── core/                                 LLM 工厂 · Milvus 客户端
│   ├── tools/                                知识检索 · 时间工具
│   └── utils/                                Loguru 日志配置
│
├── tests/                                    9 个测试模块 · pytest
├── static/index.html                         聊天前端 (原生 JS + SSE)
│
├── Dockerfile                                Python 3.11-slim
├── docker-compose.yml                        7 容器编排
├── nginx.conf                                负载均衡 + SSE 适配
└── .env.docker                               Docker 环境变量
```

---

## PRD 输出格式

> 8 章完整 PRD，每章由 LLM 基于需求画像独立生成

<table>
<tr>
<td>

```
1. 项目概述
   背景 · 目标 · 范围 · 一句话描述

2. 用户角色分析
   角色定义 · 痛点 · 核心需求

3. 功能需求
   功能模块 · 特性列表 · 优先级 P0/P1/P2

4. 非功能需求
   性能 · 安全 · 可扩展性 · 合规
```

</td>
<td>

```
5. 业务流程
   主流程 · 分支流程 · 异常流程

6. 系统约束与假设
   技术约束 · 业务约束 · 前置假设

7. 验收标准
   每个功能模块的可衡量验收条件

8. 附录
   术语表 · 参考文献 · 补充说明
```

</td>
</tr>
</table>

---

## 开发指南

```bash
pip install -e ".[dev]"          # 安装开发依赖
python -m pytest tests/ -v       # 运行测试
black app/ && ruff check app/    # 格式化 + lint
mypy app/                        # 类型检查
```
