# 03 — 用户与权限

## 概述

企业级系统必须支持用户隔离、权限分级和审计追踪。当前已具备基础用户认证与角色权限框架。

## 当前状态 ✅ 已实现

### 已实现的基础功能

- [x] **用户注册与登录** — `POST /api/auth/register` + `POST /api/auth/login`，用户名密码登录
- [x] **JWT Token 认证** — 登录返回 JWT access_token，API 请求携带 Bearer Token 认证
- [x] **Token 刷新** — `POST /api/auth/refresh` 延长 Token 有效期
- [x] **当前用户查询** — `GET /api/auth/me` 获取当前登录用户信息
- [x] **用户表（MySQL）** — `users` 表含 username、display_name、email、department、role、password_hash 等字段
- [x] **角色模型** — 四角色枚举：`admin` / `analyst` / `reviewer` / `business`
- [x] **管理员用户** — admin/admin123 已种子到数据库
- [x] **密码安全** — bcrypt 密码哈希存储（passlib + bcrypt）
- [x] **用户管理** — `GET /api/auth/users` 列出用户，`PATCH /api/auth/users/{id}` 修改用户信息，`PATCH /api/auth/users/{id}/status` 启用/禁用用户

### 数据模型（users 表）

```sql
CREATE TABLE users (
    id              VARCHAR(64) PRIMARY KEY,
    username        VARCHAR(100) NOT NULL UNIQUE,
    display_name    VARCHAR(200),
    email           VARCHAR(200),
    department      VARCHAR(100),
    role            ENUM('admin','analyst','reviewer','business') NOT NULL DEFAULT 'business',
    password_hash   VARCHAR(256),
    avatar_url      VARCHAR(500),
    source          ENUM('ldap','wecom','local') DEFAULT 'local',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_department (department),
    INDEX idx_role (role)
);
```

## 待实现 🔲

### 认证增强（P1）

- [ ] **LDAP/OIDC 集成** — 对接公司 AD/LDAP 或 OIDC 统一认证
- [ ] **企业微信扫码登录** — 使用现有 WeCom 身份体系扫码登录
- [ ] **企业微信/企业微信账号绑定** — 用户名/密码登录后绑定企微 ID，下次企微扫码直接登录

### 权限细化（P1）

- [ ] **权限矩阵** — 每个 API 端点校验角色权限（如仅 admin 可访问用户管理）
- [ ] **功能级权限** — 前端按钮/菜单根据角色显隐控制
- [ ] **用户组** — 支持用户分组，权限按组分配

### 审计日志（P1）

- [ ] **操作日志** — 记录谁在什么时间做了什么（对话、生成、修改、删除）
- [ ] **需求溯源** — 每条需求字段可以追溯到是在哪轮对话中产生的（已有 `audit_logs` 表结构但日志记录未完善）
- [ ] **审计导出** — 按时间范围导出审计日志

### 协作（P2）

- [ ] **会话共享** — 分析师可将会话分享给其他分析师协作
- [ ] **评论/@提及** — 在 PRD 上@某人进行评审
- [ ] **通知** — PRD 生成完成/有新评论时通知相关人（企微消息）
