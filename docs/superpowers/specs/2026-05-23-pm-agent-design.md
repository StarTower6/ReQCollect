# PM Agent 设计文档

> 自动识别项目需求、规划需求说明书的智能 Agent，做产品经理的活

## 1. 概述

### 1.1 目标

基于现有 SuperBizAgent 技术栈（FastAPI + LangChain + LangGraph + Milvus + MCP），构建一个 PM Agent，能够像真人产品经理一样与用户对话，挖掘软件项目需求，最终产出专业 PRD 文档。

### 1.2 核心能力

- 对话式需求挖掘：像资深 PM 一样主动追问、引导用户表达需求
- 领域知识检索：上传的经验文档索引到 Milvus，Agent 自动检索参考
- 多轮对话 + 文件上传双输入
- 输出专业 Markdown PRD，支持一键生成和增量确认两种模式
- 工具调用由 LLM 自主决策，不限死工具列表

## 2. 技术栈

| 组件 | 选型 |
|------|------|
| Web 框架 | FastAPI |
| Agent 框架 | LangGraph |
| LLM | DeepSeek V4（1M 上下文） |
| 向量存储 | Milvus |
| 文件上传管线 | 复用现有 document_splitter + vector_index |
| 工具协议 | LangChain @tool + MCP |
| 流式输出 | SSE（sse-starlette） |

## 3. 架构：双阶段混合模式

```
┌─────────────────────────────────────────────────────────┐
│                     PM Agent Service                     │
│                                                         │
│  ┌──────────────────────┐    ┌──────────────────────┐   │
│  │   阶段1: 需求挖掘     │    │  阶段2: PRD 生成      │   │
│  │   (ReAct Agent)      │    │  (Structured Pipeline)│   │
│  │                      │    │                      │   │
│  │  用户 ←→ PM人设LLM   │    │  Profile → PRD输出   │   │
│  │         ↓            │───→│                      │   │
│  │   更新需求画像        │    │  支持: 一键 / 增量   │   │
│  │   信息充分度评估      │    │                      │   │
│  └──────────────────────┘    └──────────────────────┘   │
│                         ↕                               │
│               RequirementProfile (共享状态)              │
└─────────────────────────────────────────────────────────┘
```

- **阶段1**：基于 ReAct（`create_react_agent`），自然对话 + 后台维护结构化需求画像
- **阶段2**：基于 Plan-Execute 流水线，按章节目录逐节生成 PRD

## 4. 项目结构

```
pm_agent/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   │
│   ├── agent/
│   │   └── pm/
│   │       ├── __init__.py
│   │       ├── state.py                  # RequirementProfile 状态定义
│   │       ├── prompts.py                # PM 人设提示词 + PRD 模板
│   │       ├── tools.py                  # PM 专用 @tool 工具
│   │       │
│   │       ├── phase1/
│   │       │   ├── __init__.py
│   │       │   ├── mining_agent.py       # ReAct PM 对话 Agent
│   │       │   └── sufficiency.py        # 信息充分度评估器
│   │       │
│   │       └── phase2/
│   │           ├── __init__.py
│   │           ├── planner.py            # PRD 章节规划
│   │           ├── generator.py          # 逐章节内容生成
│   │           └── assembler.py          # 文档拼装 + 增量控制
│   │
│   ├── services/
│   │   └── pm_agent_service.py           # 两阶段编排 + SSE 流式输出
│   │
│   ├── api/
│   │   └── pm.py                         # PM Agent HTTP 端点
│   │
│   ├── models/
│   │   └── pm.py                         # 请求/响应 Pydantic 模型
│   │
│   ├── core/
│   │   ├── llm_factory.py                # LLM 工厂（DeepSeek V4）
│   │   └── milvus_client.py              # Milvus 客户端
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── knowledge_tool.py             # 向量检索工具
│   │   └── time_tool.py                  # 时间工具
│   │
│   └── utils/
│       └── logger.py                     # Loguru 日志
│
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-23-pm-agent-design.md
```

## 5. 核心状态：RequirementProfile

两个阶段之间的桥梁：

```python
class RequirementProfile(TypedDict):
    project_name: str
    project_type: str           # Web/SaaS/小程序/AI应用...
    industry: str               # 金融/医疗/外卖/通用...
    elevator_pitch: str         # 一句话描述

    user_roles: List[dict]      # [{"role": "...", "desc": "...", "concerns": [...]}]
    functional_modules: List[dict]  # [{"module": "...", "features": [...], "priority": "P0/P1/P2"}]
    non_functional: dict        # {"performance": "...", "security": "...", ...}

    constraints: List[str]      # 技术/业务约束
    assumptions: List[str]      # 前置假设

    covered_topics: List[str]   # 已覆盖的话题
    pending_questions: List[str]  # 待追问
    sufficiency_score: float    # 信息充分度 0.0-1.0
```

## 6. API 设计

### 6.1 核心端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/pm/chat` | 阶段1：需求挖掘对话（SSE） |
| POST | `/api/pm/generate` | 阶段2：触发 PRD 生成（SSE） |
| POST | `/api/pm/continue` | 阶段2：增量模式继续下一章节（SSE） |
| POST | `/api/pm/agent` | 便利层：自动路由到 chat/generate/continue |
| POST | `/api/pm/upload` | 上传需求经验文档 → Milvus |
| GET | `/api/pm/profile/{session_id}` | 查看当前需求画像 |

`/api/pm/agent` 是前端便利层——自动检测意图：普通消息 → chat，含"生成PRD" → generate，"继续" → continue。后端内部仍使用独立方法，各端点可独立调用和测试。

### 6.2 阶段1 SSE 事件（/api/pm/chat）

| 事件类型 | 时机 | 内容 |
|---------|------|------|
| `content` | PM Agent 回复 | token 流 |
| `profile_update` | 需求画像更新 | 哪个字段被填充 |
| `sufficiency` | 信息充分度变化 | 当前评分 0.0-1.0 |
| `ready_to_generate` | 信息够了 | 提议用户生成 PRD |

### 6.3 阶段2 SSE 事件（/api/pm/generate + /api/pm/continue）

| 事件类型 | 时机 | 内容 |
|---------|------|------|
| `prd_plan` | 章节规划完成 | PRD 章节目录 |
| `section_start` | 开始写某章节 | 章节标题 |
| `section_content` | 章节内容流 | token 流 |
| `section_complete` | 某章节完成 | 完整章节 Markdown |
| `prd_complete` | 全篇完成 | 最终 PRD |
| `awaiting_approval` | 增量模式暂停 | 等待用户通过 /api/pm/continue 继续 |

## 7. 阶段1：PM 对话 Agent

### 7.1 系统提示词（人设）

```
你是一位资深产品经理，拥有 10 年以上的软件需求分析经验。

工作方式：
1. 先理解业务背景 — 行业、目标用户、要解决什么问题
2. 逐步挖掘 — 用户角色 → 核心流程 → 功能模块 → 边界条件
3. 主动追问 — 用户说得模糊的地方，用具体问题引导他说清楚
4. 借鉴经验 — 检索知识库，找到类似项目的经验参考
5. 同步记录 — 分析得到的结论实时写入需求画像

对话原则：
- 一次只问 1-2 个问题，不要连珠炮
- 用具体选项引导，而不是开放式提问
- 用户跑题时温和拉回来
```

### 7.2 PM 专用工具

| 工具名 | 功能 |
|-------|------|
| `search_domain_knowledge` | 检索 Milvus 中的需求经验文档 |
| `update_requirement_profile` | 更新需求画像字段 |
| `get_profile_summary` | 获取当前画像摘要（自检覆盖了什么、还缺什么） |
| `evaluate_sufficiency` | 评估画像信息充分度，返回分数 + 待补充项 |

工具调用由 LLM 自主决策，同时开放 MCP 动态工具接入，Agent 可根据需要自由调用任何可用工具。

### 7.3 信息充分度评估

- 运行时机：每轮对话后自动评估
- 返回：评分（0.0-1.0）+ 缺失字段列表 + 建议追问方向
- 阈值：≥ 0.75 时 Agent 主动提议生成 PRD
- 用户可忽略建议，随时手动触发生成

## 8. 阶段2：PRD 生成流水线

### 8.1 流程

```
PRD Planner（确定章节结构）
  → Generator（逐章调用 LLM 生成）
    → Assembler（拼装 Markdown）
      → SSE 流式输出
```

### 8.2 默认 PRD 模板

```
1. 项目概述
2. 用户角色分析
3. 功能需求
4. 非功能需求
5. 业务流程
6. 系统约束与假设
7. 验收标准
8. 附录（术语表、参考文档）
```

## 9. 文件上传策略

- 全部文件走 Milvus 索引管线（分块 → 嵌入 → 存入 Milvus）
- 复用现有的 `document_splitter_service` + `vector_index_service` 管线
- Agent 通过 `search_domain_knowledge` 工具检索

## 10. 错误处理

| 场景 | 处理方式 |
|------|---------|
| LLM 调用失败 | 重试 2 次，失败后 SSE 返回 `error` 事件 |
| 知识库检索无结果 | 告知用户，用 LLM 内置知识继续 |
| 文件上传/解析失败 | 返回具体错误，不阻塞对话流程 |
| 信息不足时强制生成 | 允许，提醒当前完整度百分比 |
| 增量模式中途切换 | 支持用户随时发"直接生成全部"切换为一键模式 |

## 11. 关键约定

- 遵循现有项目的单例模式（module-level 全局实例）
- 使用 Loguru 日志（`from loguru import logger`）
- 配置通过 pydantic-settings 从 `.env` 读取
- 使用 LangGraph `MemorySaver` 管理会话状态
- SSE 流式输出使用 `sse-starlette`
