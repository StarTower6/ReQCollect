# 04 — 存储与数据

## 概述

当前使用 JSON 文件持久化，存在数据丢失风险和并发问题。企业级需要可靠的关系型数据库和数据治理能力。

**数据库选型：MySQL 8.0**（与格力现有技术栈一致，原 PMAgent 即使用 MySQL）

## 当前状态 ✅ 已实现

- [x] 内存存储（运行时）：_profile_store, _message_history, _prd_store
- [x] JSON 文件备份：pm_data/profile_{sid}.json, pm_data/prd_{sid}.json
- [x] Agent 状态：MemorySaver（内存检查点）

## 待实现 🔲

### MySQL 接入（P0）

#### 配置
```yaml
# .env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=reqcollect
MYSQL_PASSWORD=***
MYSQL_DATABASE=reqcollect
```

#### 数据模型（SQLAlchemy + aiomysql 异步驱动）

```sql
-- 用户表
CREATE TABLE users (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    email VARCHAR(200),
    department VARCHAR(100),         -- 部门
    role ENUM('admin','analyst','reviewer','business') NOT NULL DEFAULT 'business',
    source ENUM('ldap','wecom','local') DEFAULT 'local',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_department (department),
    INDEX idx_role (role)
);

-- 会话表
CREATE TABLE sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    project_name VARCHAR(200) DEFAULT '',
    status ENUM('mining','generating','complete') DEFAULT 'mining',
    sufficiency_score FLOAT DEFAULT 0.0,
    is_pinned BOOLEAN DEFAULT FALSE,
    tags JSON,                       -- 标签：["报销","财务"]
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_updated (updated_at)
);

-- 需求画像表
CREATE TABLE requirement_profiles (
    id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    project_name VARCHAR(200) DEFAULT '',
    business_background TEXT,
    current_process TEXT,
    user_roles JSON,                 -- [{"role":"审批人","count":50,"dept":"财务部"}]
    business_flow TEXT,
    functional_requirements JSON,    -- [{"module":"报销录入","features":[],"priority":"P0"}]
    existing_systems JSON,           -- ["用友ERP","OA系统"]
    non_functional JSON,             -- {"performance":"...","security":"..."}
    data_scale VARCHAR(500),
    constraints JSON,
    success_criteria JSON,
    covered_topics JSON,
    pending_questions JSON,
    sufficiency_score FLOAT DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- 对话消息表
CREATE TABLE chat_messages (
    id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    role ENUM('user','assistant','event') NOT NULL,
    content TEXT NOT NULL,
    event_type VARCHAR(50) DEFAULT 'message',
    meta JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_session (session_id),
    INDEX idx_created (created_at)
);

-- PRD 文档表
CREATE TABLE generated_prds (
    id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    version INT DEFAULT 1,
    title VARCHAR(500) DEFAULT '',
    mode VARCHAR(20) DEFAULT 'one_shot',
    sections JSON,
    markdown LONGTEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_session (session_id),
    INDEX idx_version (session_id, version)
);

-- 审计日志表
CREATE TABLE audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64),
    session_id VARCHAR(64),
    action VARCHAR(100) NOT NULL,      -- 'chat','generate','view','delete','login'
    detail JSON,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
);
```

#### 代码改动
- [ ] **app/db/** — 恢复 database.py / models.py / repository.py（参考原 PMAgent 的 MySQL 层代码）
  - `database.py` — Async SQLAlchemy 引擎 + session 管理
  - `models.py` — ORM 模型（users, sessions, profiles, messages, prds, audit_logs）
  - `repository.py` — 数据访问层（CRUD 操作）
- [ ] **app/main.py** — 启动时 init_db()
- [ ] **app/services/pm_agent_service.py** — 存储逻辑从 in-memory + JSON 迁移到 MySQL
- [ ] **app/api/pm.py** — 恢复 /api/pm/sessions、/api/pm/history 等端点

### 数据迁移（P0）
- [ ] **JSON → MySQL 迁移脚本** — 一键将 pm_data/*.json 导入 MySQL
  ```bash
  python scripts/migrate_json_to_mysql.py
  ```
- [ ] **兼容层** — 无 MySQL 时回退到 JSON 文件模式（开发环境可用）

### 数据安全（P1）
- [ ] **MySQL 自动备份** — mysqldump 每日定时备份
- [ ] **连接池** — SQLAlchemy pool_size=20, max_overflow=10
- [ ] **重试机制** — 数据库连接失败时自动重试

### 数据服务（P1）
- [ ] **需求看板** — 按部门/状态汇总需求数量、完整度分布
- [ ] **数据统计** — 按时间维度统计需求采集量、PRD 生成量
- [ ] **数据导出** — 会话/PRD 批量导出为 Excel/CSV

### 索引与搜索（P2）
- [ ] **全文搜索** — MySQL FULLTEXT INDEX 搜索会话标题和消息内容
- [ ] **标签筛选** — 按 tags JSON 字段过滤会话
