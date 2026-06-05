# Plan: 04 — 存储与数据

## 1. 任务理解

- **需求来源**: `docs/requirements/04-存储与数据/README.md`
- **核心目标**: 将当前纯内存 + JSON 文件的持久化方案升级为 MySQL 8.0（asyncmy 异步驱动），同时保留 JSON 文件作为无 MySQL 时的自动回退模式
- **用户选择**:
  - 范围: P0 MySQL 接入 + P0 数据迁移 + P1 数据服务
  - 驱动: asyncmy
  - 兼容层: 自动回退（无 MySQL 时降级为 JSON 文件模式）

## 2. 架构设计

### 分层结构

```
┌─────────────────────────────────────────┐
│           Service 层                      │  pm_agent_service.py
│   (注入 DataStore，不关心底层实现)        │
├─────────────────────────────────────────┤
│           DataStore 抽象接口              │  app/db/__init__.py (protocol)
├──────────────────┬──────────────────────┤
│  MySQLDataStore  │   FileDataStore       │  repository.py / compat.py
│  (asyncmy+SQLA)  │   (JSON 文件回退)     │
├──────────────────┴──────────────────────┤
│           ORM 模型                        │  models.py
│   users / sessions / requirement_profiles │
│   chat_messages / generated_prds         │
│   audit_logs                             │
├─────────────────────────────────────────┤
│           database.py                     │
│   async engine + session 管理 + init_db  │
└─────────────────────────────────────────┘
```

### 核心设计决策

1. **策略模式**: Service 层不直接操作 MySQL 或 JSON 文件，而是通过 `DataStore` protocol 接口调用。启动时根据 MySQL 可达性自动选择实现。
2. **兼容层**: `FileDataStore` 实现与 `MySQLDataStore` 相同的接口，用 JSON 文件模拟 CRUD。开发环境无 MySQL 也可正常运行。
3. **models.py 只做 ORM 定义**，不做业务逻辑。repository 负责数据访问和结果组装。
4. **迁移不影响现有数据**：已有 `pm_data/*.json` 文件格式与 `FileDataStore` 兼容；`migrate_json_to_mysql.py` 一次性导入到 MySQL。

## 3. 改动清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `app/db/database.py` | 异步 SQLAlchemy 引擎、session 工厂、init_db() |
| `app/db/models.py` | 6 个 ORM 模型（users, sessions, requirement_profiles, chat_messages, generated_prds, audit_logs） |
| `app/db/repository.py` | MySQLDataStore — MySQL CRUD 实现 |
| `app/db/compat.py` | FileDataStore — JSON 文件回退实现 |
| `app/db/exceptions.py` | 自定义异常类 |
| `scripts/migrate_json_to_mysql.py` | JSON → MySQL 一键迁移脚本 |
| `scripts/export_sessions.py` | 会话/PRD 批量导出为 Excel/CSV |

### 修改文件

| 文件 | 改动 |
|------|------|
| `app/db/__init__.py` | 导出 DataStore 协议和工厂函数 `create_datastore()` |
| `app/config.py` | 追加 MySQL 配置项、兼容层配置 |
| `app/main.py` | lifespan 中初始化 datastore 并注入 service |
| `app/services/pm_agent_service.py` | 从内存 dict + JSON 迁移到 DataStore 接口；新增统计/导出方法 |
| `app/agent/pm/tools.py` | `_profile_store` 从内存迁移到 DataStore |
| `app/api/pm.py` | 恢复完整版会话列表、历史消息分页、新增统计看板/导出端点 |
| `app/models/pm.py` | 新增 DashboardRequest, ExportRequest 等模型 |
| `pyproject.toml` | 新增依赖: sqlalchemy[asyncio], asyncmy, openpyxl |

## 4. 数据模型

完全遵循需求文档中的 6 个表结构（Schema 见 `docs/requirements/04-存储与数据/README.md`）：

- `users` — 用户表（暂作为基础数据表，本次不实现完整的用户管理，仅做会话归属）
- `sessions` — 会话表（含 status, sufficiency_score, tags, 项目名称）
- `requirement_profiles` — 需求画像表（JSON 字段存储结构化画像数据）
- `chat_messages` — 对话消息表（role 区分 user/assistant/event，event_type 细分消息类型）
- `generated_prds` — PRD 文档表（支持多版本，sections JSON 字段 + markdown LONGTEXT）
- `audit_logs` — 审计日志表（BIGINT 自增主键，记录关键操作）

本次不做: 用户注册/登录（用户数据由企业微信 LDAP 或其他外部系统导入）

## 5. 验收标准

### P0 — MySQL 接入

- [ ] P0: `app/db/database.py` 能正常初始化异步 SQLAlchemy 引擎并创建所有表
- [ ] P0: MySQL 可用时，数据写入会话表/消息表/画像表/PRD 表后能正确读出
- [ ] P0: `pm_agent_service.chat()` 的对话消息持久化到 MySQL（不再丢失）
- [ ] P0: `pm_agent_service.generate_prd()` 生成的 PRD 持久化到 MySQL
- [ ] P0: 需求画像（profile）数据持久化到 MySQL
- [ ] P0: `GET /api/pm/sessions` 返回持久化的会话列表（含项目名称、状态、完整度分数）
- [ ] P0: `GET /api/pm/history/{session_id}` 返回完整的对话历史
- [ ] P0: `DELETE /api/pm/sessions/{session_id}` 级联删除关联数据

### P0 — 数据迁移

- [ ] P0: `scripts/migrate_json_to_mysql.py` 能读取 pm_data/*.json 并写入 MySQL
- [ ] P0: MySQL 不可用时（配置未设置或连接失败），服务自动回退到 JSON 文件模式
- [ ] P0: JSON 回退模式下，所有 API 端点正常工作

### P0 — 兼容性

- [ ] P0: 原有的 `GET /api/pm/profile/{session_id}` 和 `GET /api/pm/prd/{session_id}` 端点保持兼容
- [ ] P0: 原有的 SSE 流式端点不受影响
- [ ] P0: `/api/health` 返回 200

### P1 — 数据服务

- [ ] P1: `GET /api/pm/dashboard/overview` 返回按状态汇总的需求数量、平均完整度
- [ ] P1: `GET /api/pm/dashboard/trend` 返回按时间维度（日/周/月）的需求采集量、PRD 生成量
- [ ] P1: `GET /api/pm/export/sessions?format=csv` 导出会话列表为 CSV
- [ ] P1: `GET /api/pm/export/sessions?format=xlsx` 导出会话列表为 Excel
- [ ] P1: `GET /api/pm/export/prds?format=xlsx` 导出 PRD（标题+时间+内容摘要）为 Excel

### 不做（明确排除）

- ❌ 用户注册/登录、权限管理（仅建立 users 表基础结构）
- ❌ 全文搜索（P2，后续迭代）
- ❌ 标签筛选（P2，后续迭代）
- ❌ MySQL 自动备份脚本（P1 数据安全，后续迭代）
- ❌ 前端看板页面（仅提供 API 端点）
- ❌ 消息事件溯源、数据版本控制

## 6. 风险与依赖

### 依赖

- `sqlalchemy[asyncio]>=2.0` — SQLAlchemy 异步支持
- `asyncmy>=0.2.9` — MySQL 异步驱动
- `openpyxl>=3.1` — Excel 导出
- MySQL 8.0 服务（开发环境可选）

### 注意事项

1. **Profile Store 迁移风险**: `tools.py` 中的 `_profile_store` 是 LangGraph agent 的核心状态，迁移到 DataStore 后必须保持接口兼容。agent 通过 `get_profile()` / `get_profile_summary()` / `update_requirement_profile()` 工具操作 profile，这些函数的语义不能变。

2. **并发安全**: 当前内存 dict 在并发请求下存在竞态。MySQL 事务 + connection pool 能解决；JSON 文件回退模式下仍无并发保护，需在文档中注明。

3. **Session ID 兼容性**: 现有 pm_data/*.json 文件名使用 `session-xxx` 和 `test-xxx` 作为 session_id。迁移脚本和 FileDataStore 需要保持文件名解析规则一致。

4. **初始化顺序**: lifespan 中必须先初始化 datastore，再创建 service 实例。在 `__init__` 中依赖检测可能导致导入时抛异常。

## 7. 实施步骤（按顺序）

### Step 1: 环境准备
- 安装 asyncmy + sqlalchemy + openpyxl 依赖
- 更新 pyproject.toml

### Step 2: 基础 DB 层
- 实现 `app/db/models.py` — 6 个 ORM 模型
- 实现 `app/db/database.py` — 异步引擎、session 管理、init_db()
- 实现 `app/db/exceptions.py` — 自定义异常

### Step 3: DataStore 抽象接口
- 更新 `app/db/__init__.py` — 定义 DataStore Protocol 和 factory 函数

### Step 4: MySQLDataStore 实现
- 实现 `app/db/repository.py` — MySQL 版 CRUD 全量实现

### Step 5: FileDataStore 回退实现
- 实现 `app/db/compat.py` — JSON 文件版全量实现（取代现有的分散文件存储逻辑）

### Step 6: 配置更新
- 更新 `app/config.py` — MySQL 配置项

### Step 7: 服务层迁移
- 重写 `app/services/pm_agent_service.py` — 注入 DataStore，移除内存 dict
- 更新 `app/agent/pm/tools.py` — _profile_store 迁移

### Step 8: API 端点完善
- 更新 `app/api/pm.py` — sessions/history 使用 DataStore
- 新增 dashboard/trend/export 端点

### Step 9: 应用入口
- 更新 `app/main.py` — lifespan 中 init datastore

### Step 10: 数据迁移脚本
- 实现 `scripts/migrate_json_to_mysql.py`

### Step 11: Evaluate
- 逐条验证验收标准
- 写 report.md
