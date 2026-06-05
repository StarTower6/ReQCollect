-- ReQCollect 初始化 SQL
-- 在 MySQL 容器首次启动时自动执行
-- 创建应用所需数据库表结构（SQLAlchemy 也会自动创建）

CREATE DATABASE IF NOT EXISTS reqcollect
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 创建用户表
CREATE TABLE IF NOT EXISTS reqcollect.users (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    email VARCHAR(200),
    department VARCHAR(100),
    role ENUM('admin','analyst','reviewer','business') NOT NULL DEFAULT 'business',
    source ENUM('ldap','wecom','local') DEFAULT 'local',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_department (department),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建会话表
CREATE TABLE IF NOT EXISTS reqcollect.sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    project_name VARCHAR(200) DEFAULT '',
    status ENUM('mining','generating','complete') DEFAULT 'mining',
    sufficiency_score FLOAT DEFAULT 0.0,
    is_pinned BOOLEAN DEFAULT FALSE,
    tags JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES reqcollect.users(id),
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建需求画像表
CREATE TABLE IF NOT EXISTS reqcollect.requirement_profiles (
    id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    project_name VARCHAR(200) DEFAULT '',
    business_background TEXT,
    current_process TEXT,
    user_roles JSON,
    business_flow TEXT,
    functional_requirements JSON,
    existing_systems JSON,
    non_functional JSON,
    data_scale VARCHAR(500),
    constraints JSON,
    success_criteria JSON,
    covered_topics JSON,
    pending_questions JSON,
    sufficiency_score FLOAT DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES reqcollect.sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建对话消息表
CREATE TABLE IF NOT EXISTS reqcollect.chat_messages (
    id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    role ENUM('user','assistant','event') NOT NULL,
    content TEXT NOT NULL,
    event_type VARCHAR(50) DEFAULT 'message',
    meta JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES reqcollect.sessions(id) ON DELETE CASCADE,
    INDEX idx_session (session_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建 PRD 文档表
CREATE TABLE IF NOT EXISTS reqcollect.generated_prds (
    id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    version INT DEFAULT 1,
    title VARCHAR(500) DEFAULT '',
    mode VARCHAR(20) DEFAULT 'one_shot',
    sections JSON,
    markdown LONGTEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES reqcollect.sessions(id) ON DELETE CASCADE,
    INDEX idx_session (session_id),
    INDEX idx_version (session_id, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建审计日志表
CREATE TABLE IF NOT EXISTS reqcollect.audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64),
    session_id VARCHAR(64),
    action VARCHAR(100) NOT NULL,
    detail JSON,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认用户
INSERT IGNORE INTO reqcollect.users (id, username, display_name, role, source)
VALUES ('default', 'default', 'Default User', 'business', 'local');
