# 04 — 存储与数据

## 概述

系统已使用 MySQL 8.0 作为主存储引擎，JSON 文件作为 fallback 兼容层。企业级需要进一步强化数据安全、数据服务和搜索能力。

**数据库选型：MySQL 8.0**（与格力现有技术栈一致）

## 当前状态 ✅ 已实现

### 已实现的基础功能

- [x] **MySQL 8.0 数据库** — Docker Compose 编排的 `reqcollect-mysql` 容器（健康检查 + 持久化卷 + 开机自启）
- [x] **SQLAlchemy 异步驱动** — `aiomysql` + `asyncmy` 异步 MySQL 驱动
- [x] **6 张核心表全量创建**（通过 `scripts/init.sql` + `app/db/models.py` 自动迁移）

| 表名 | 用途 |
|------|------|
| `users` | 用户账户与角色 |
| `sessions` | 对话会话（项目名、状态、完整度分数、标签） |
| `requirement_profiles` | 需求画像（11 个字段 + 完整度评分） |
| `chat_messages` | 对话消息（角色、内容、事件类型、元数据） |
| `generated_prds` | PRD 文档（版本、章节 JSON、Markdown） |
| `audit_logs` | 审计日志（操作记录） |

- [x] **`app/db/database.py`** — Async SQLAlchemy 引擎 + session 管理 + 连接池
- [x] **`app/db/models.py`** — 6 表 ORM 模型，UUID 主键，UTC 时间戳
- [x] **`app/db/repository.py`** — 完整 CRUD 数据访问层
- [x] **`app/db/compat.py`** — JSON 文件兼容层，确保无 MySQL 时降级运行
- [x] **`app/main.py`** — 启动时 `init_db()` 创建表，先尝试 MySQL 失败则回退 JSON
- [x] **JSON 文件 fallback** — `pm_data/` 目录保留，无 MySQL 环境仍可用

### 连接池配置

```yaml
pool_size: 20
max_overflow: 10
pool_recycle: 3600
pool_pre_ping: true
echo: false
```

## 待实现 🔲

### 数据安全（P1）

- [ ] **MySQL 自动备份** — mysqldump 每日定时备份到 `pm_data/backups/`
- [ ] **备份保留策略** — 保留最近 7 天备份，自动清理过期备份
- [ ] **连接池监控** — SQLAlchemy 连接池状态暴露给 Prometheus

### 数据服务（P1）

- [ ] **需求看板** — 按部门/状态汇总需求数量、完整度分布
- [ ] **数据统计** — 按时间维度统计需求采集量、PRD 生成量
- [ ] **数据导出** — 会话/PRD 批量导出为 Excel/CSV

### 索引与搜索（P2）

- [ ] **全文搜索** — MySQL FULLTEXT INDEX 搜索会话标题和消息内容
- [ ] **标签筛选** — 按 tags JSON 字段过滤会话
- [ ] **高级查询** — 按部门、时间段、完整度区间组合筛选
