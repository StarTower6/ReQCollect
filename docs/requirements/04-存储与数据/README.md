# 04 — 存储与数据

## 概述

当前使用 JSON 文件持久化，存在数据丢失风险和并发问题。企业级需要可靠的关系型数据库和数据治理能力。

## 当前状态 ✅ 已实现

- [x] 内存存储（运行时）：_profile_store, _message_history, _prd_store
- [x] JSON 文件备份：pm_data/profile_{sid}.json, pm_data/prd_{sid}.json
- [x] Agent 状态：MemorySaver（内存检查点）

## 待实现 🔲

### 数据库升级（P0）
- [ ] **PostgreSQL 替换 JSON 文件**
  - requirement_profiles 表（需求画像持久化）
  - chat_messages 表（对话历史）
  - generated_prds 表（PRD 文档）
  - users 表（用户信息）
  - audit_logs 表（审计日志）
- [ ] **SQLAlchemy ORM** + asyncpg 驱动（复用原 PMAgent 的 db 层代码）
- [ ] **迁移工具** — JSON 文件 → PostgreSQL 一键迁移脚本

### 数据模型
- [ ] **用户关联** — 所有数据表增加 user_id 外键
- [ ] **会话状态** — 记录对话阶段（mining/generating/complete）
- [ ] **PRD 版本** — 支持同一会话多次生成，保留版本历史
- [ ] **标签系统** — 会话/PRD 可打标签（部门、项目类型、优先级）

### 数据安全
- [ ] **自动备份** — PostgreSQL 每日自动备份
- [ ] **数据加密** — 敏感字段（如 API Key）加密存储
- [ ] **数据保留策略** — 可配置数据保留期限，自动清理过期会话

### 数据服务（P1）
- [ ] **需求看板** — 汇总所有需求项目的仪表盘（数量、状态、负责人）
- [ ] **数据统计** — 按部门/时间统计需求数量、完整度分布、平均生成时间
- [ ] **数据导出** — 会话/PRD 批量导出为 Excel/CSV

### 索引与搜索（P1）
- [ ] **全文搜索** — 搜索所有历史会话和 PRD 内容
- [ ] **FTS5（SQLite FTS）/ PostgreSQL tsvector**
