# 用户认证与隔离设计文档

## 概述

在 ReQCollect 平台中实现用户认证（登录/注册/JWT）和用户隔离（个人会话空间、用户管理），将当前的无用户共用系统升级为企业级多用户系统。

## 总体架构

```
┌──────────────────────────────────────────────────────┐
│                    前端 Vue SPA                        │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │LoginView │  │AuthStore │  │api/client.ts 拦截器 │  │
│  │登录页面  │  │用户状态  │  │自动附 Authorization│  │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
└───────┼──────────────┼─────────────────┼─────────────┘
        │              │                 │
        ▼              ▼                 ▼
┌──────────────────────────────────────────────────────┐
│                   FastAPI Backend                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ /api/auth/*  │  │ /api/pm/*   │  │Middleware │  │
│  │ login/me     │  │← all with   │  │CORS/JSON │  │
│  │ refresh      │  │ Depends(    │  │          │  │
│  │ users(admin) │  │ get_current │  │          │  │
│  └──────┬───────┘  │ _user)     │  └───────────┘  │
│         │          └──────┬──────┘                 │
│         ▼                 ▼                        │
│  ┌─────────────────────────────────────┐           │
│  │         core/auth.py                │           │
│  │  • JWT 创建/验证                    │           │
│  │  • 密码哈希/校验 (passlib+bcrypt)   │           │
│  │  • get_current_user 依赖注入         │           │
│  └──────────────┬─────────────────────┘           │
│                 ▼                                  │
│  ┌─────────────────────────────────────┐          │
│  │        DataStore                    │          │
│  │  • User CRUD 扩展                   │          │
│  │  • 会话归属 user_id 过滤            │          │
│  └─────────────────────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

## 1. 核心工具层 — `app/core/auth.py`

### 功能
- JWT Token 创建与验证
- 密码安全哈希与校验
- FastAPI 依赖注入（获取当前用户）

### JWT 配置（扩展 `app/config.py`）

```python
# 新增配置字段
auth_jwt_secret: str = ""           # 自动生成 fallback
auth_jwt_algorithm: str = "HS256"
auth_access_token_expire_minutes: int = 1440  # 24小时
```

### 核心函数

| 函数 | 签名 | 说明 |
|------|------|------|
| `create_access_token` | `(data: dict, expires_delta: timedelta \| None = None) → str` | 创建 JWT Token |
| `verify_token` | `(token: str) → dict \| None` | 验证 Token，返回 payload 或 None |
| `hash_password` | `(password: str) → str` | passlib bcrypt 哈希 |
| `verify_password` | `(plain: str, hashed: str) → bool` | 校验密码 |
| `get_current_user` | FastAPI Depends | 从 Authorization header 提取并验证用户 |

### get_current_user 行为
- **401**: 无 Token / Token 无效 / Token 过期
- **403**: 用户被禁用（is_active=False）

### 依赖
- `python-jose[cryptography]` — JWT 编解码
- `passlib[bcrypt]` — 密码哈希

## 2. 认证 API — `app/api/auth.py`

### 路由表

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/login` | 用户名密码登录 → `{access_token, token_type}` | 公开 |
| POST | `/api/auth/refresh` | 刷新 Token | Bearer Token |
| GET | `/api/auth/me` | 获取当前用户信息 | Bearer Token |
| POST | `/api/auth/register` | 注册新用户（首次部署用） | 公开 |
| GET | `/api/auth/users` | 列出所有用户 | 管理员 |
| PATCH | `/api/auth/users/{user_id}/status` | 启用/禁用用户 | 管理员 |

### 认证中间件设计

不引入全局中间件，采用 **FastAPI 依赖注入**方式。所有 `/api/pm/*` 端点添加 `Depends(get_current_user)` 参数：

```python
@router.get("/pm/sessions")
async def pm_list_sessions(
    current_user: dict = Depends(get_current_user),
    ...
):
    user_id = current_user["id"]
    ...
```

这样做的好处：
- 精确控制每个端点的权限
- 不影响 `/api/health` 等公开端点
- 不影响依赖注入的测试

### 错误响应格式

```json
{
  "detail": "Not authenticated",
  "code": "auth_required"
}
```

```json
{
  "detail": "User is disabled",
  "code": "user_disabled"
}
```

## 3. 用户隔离 — 会话管理改造

### DataStore 扩展

#### 用户管理（新增）

```
create_user(username, display_name, password_hash, role, source, ...) → dict
get_user_by_username(username) → dict | None
get_user_by_id(user_id) → dict | None
list_users() → list[dict]
update_user(user_id, **kwargs) → dict | None
```

#### FileDataStore 用户存储

文件路径：`pm_data/users/users.json`

```json
[
  {
    "id": "abc123...",
    "username": "admin",
    "display_name": "管理员",
    "email": "",
    "department": "",
    "role": "admin",
    "source": "local",
    "password_hash": "$2b$12$...",
    "is_active": true,
    "created_at": "2026-06-07T...",
    "updated_at": "2026-06-07T..."
  }
]
```

#### 会话查询改造

现有 `list_sessions(user_id)` 已支持按 user_id 过滤，前端传参即可。**唯一补充**：管理员可通过 `?all=true` 查看所有用户会话。

```python
@router.get("/pm/sessions")
async def pm_list_sessions(
    current_user: dict = Depends(get_current_user),
    all: bool = Query(default=False),  # 管理员专用
    ...
):
    if all and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可查看所有会话")
    user_id = None if all else current_user["id"]
    sessions = await _svc().list_sessions(user_id=user_id, ...)
```

#### 会话归属检查（新增辅助函数）

```python
async def _check_session_ownership(current_user: dict, session_id: str):
    """检查当前用户是否有权限访问指定会话。管理员可访问任何会话。"""
    session = await _svc().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user["role"] != "admin" and session.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    return session
```

### 现有 PM API 端点改动清单

| 端点 | 改动 |
|------|------|
| `POST /api/pm/chat` | 添加 `Depends(get_current_user)`；替换硬编码 "default" user_id |
| `POST /api/pm/generate` | 添加 `Depends(get_current_user)` |
| `POST /api/pm/continue` | 添加 `Depends(get_current_user)` |
| `POST /api/pm/agent` | 添加 `Depends(get_current_user)` |
| `GET /api/pm/sessions` | 添加 `Depends(get_current_user)`；默认按当前用户过滤；支持 `?all=` |
| `DELETE /api/pm/sessions/{id}` | 添加 `Depends(get_current_user)`；归属检查 |
| `GET /api/pm/profile/{id}` | 添加 `Depends(get_current_user)`；归属检查 |
| `GET /api/pm/prd/{id}` | 添加 `Depends(get_current_user)`；归属检查 |
| `GET /api/pm/history/{id}` | 添加 `Depends(get_current_user)`；归属检查 |
| `GET /api/pm/dashboard/*` | 管理员专属或基于当前用户 |
| `GET /api/pm/export/*` | 添加 `Depends(get_current_user)`；过滤归属 |

## 4. 前端改动

### 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/views/LoginView.vue` | **新建** | 登录表单页面 |
| `src/stores/auth.ts` | **新建** | AuthStore：token 管理、用户信息、登录/登出 |
| `src/api/client.ts` | **修改** | 添加请求拦截器（注入 Authorization）、响应拦截器（401 跳登录） |
| `src/router/index.ts` | **修改** | 添加 `/login` 路由；导航守卫 |
| `src/views/admin/UsersView.vue` | **新建** | 管理员用户管理页面 |
| `src/components/layout/AppLayout.vue` | **修改** | 顶部栏添加用户信息、登出按钮 |
| `src/stores/session.ts` | **修改** | 初始化时先检查登录状态 |

### 路由表

```
/login          → LoginView.vue        (公开)
/chat           → ChatView.vue          (需登录)
/chat/:id       → ChatView.vue          (需登录)
/prd/:id        → PrdView.vue           (需登录)
/dashboard      → DashboardView.vue     (需登录)
/admin/users    → UsersView.vue         (管理员)
```

### 导航守卫逻辑

```typescript
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.path !== '/login' && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/chat')
  } else {
    next()
  }
})
```

### AuthStore 接口

```typescript
// stores/auth.ts
interface AuthState {
  token: string | null
  user: UserInfo | null
}

// 方法
login(username: string, password: string): Promise<void>
logout(): void
refreshToken(): Promise<void>
loadUser(): Promise<void>  // GET /api/auth/me

// getters
isAuthenticated: boolean
isAdmin: boolean
```

### 登录页面设计

简洁的居中登录卡片（与现有 Element Plus 设计一致）：
- Logo + 系统名
- 用户名输入框
- 密码输入框
- 登录按钮（loading 状态）
- 错误提示

### AppLayout 改造

顶部标题栏右侧添加：
- 用户头像/名称
- 角色标签
- 登出按钮
- 管理员可见"用户管理"入口

## 5. 数据流

```
[首次访问]
浏览器 → /chat
       → 路由守卫检查 token
       → 无 token → 跳转 /login

[登录]
用户输入用户名/密码 → LoginView
       → AuthStore.login()
       → POST /api/auth/login → {access_token, ...}
       → AuthStore 存 token 到 localStorage
       → AuthStore 存用户信息
       → 路由跳转 /chat

[聊天]  
用户发送消息 → ChatView
       → api/client.ts 拦截器添加 Authorization: Bearer <token>
       → POST /api/pm/chat
       → FastAPI get_current_user 解析 token
       → 服务端获取 user_id → 消息归属该用户

[会话列表]
ChatView onMounted
       → GET /api/pm/sessions
       → 服务端从 token 获取 user_id → 只返回该用户会话

[管理员]
管理员 → GET /api/pm/sessions?all=true
       → 服务端检查 role == "admin" → 返回所有会话

[Token 过期]
API 返回 401 → api/client.ts 响应拦截器
       → AuthStore.logout()
       → 跳转 /login
```

## 6. 出场管理员账号

启动时自动创建出场管理员（只在用户表为空时创建）：
- 用户名：`admin`
- 密码：`admin123`（首次部署后建议修改）
- 角色：`admin`

## 7. 不做的事项

- LDAP/OIDC 集成
- 企业微信扫码登录
- 角色权限校验（P1 — 本次不做端点级角色校验，仅做用户隔离）
- 审计日志增强（P1）
- 协作功能（P2）

## 8. 验收标准

### P0 — 必须通过
- [ ] POST /api/auth/login 正确返回 JWT Token（有效期 24h）
- [ ] 无效 Token 请求 /api/pm/* 返回 401
- [ ] 普通用户只能看到自己的会话
- [ ] 会话归属正常：消息/画像/PRD 关联到创建用户
- [ ] 前端 /login 页面可正常登录
- [ ] 登录后自动跳转到 /chat
- [ ] Token 过期或无效时自动跳转登录页
- [ ] 出场管理员可正常登录

### P1 — 迭代补充
- [ ] POST /api/auth/register 注册新用户
- [ ] GET /api/auth/me 返回当前用户信息
- [ ] 管理员 GET /api/auth/users 列出所有用户
- [ ] 管理员可启用/禁用用户
- [ ] 管理员可通过 ?all=true 查看所有用户的会话
- [ ] 管理员用户管理界面

## 9. 风险与依赖

- **依赖新增**：`python-jose`、`passlib[bcrypt]` — 需更新 pyproject.toml
- **数据库兼容**：FileDataStore 新增 users.json 文件；MySQLDataStore 已存在 User 表
- **API 兼容性**：所有端点新增 `Depends(get_current_user)`，API 接口语义不变，但未登录请求会返回 401

## 10. 实施步骤

1. 新增依赖 + 配置
2. 实现 `app/core/auth.py`（JWT + 密码哈希 + 依赖注入）
3. 实现 `app/api/auth.py`（认证路由）
4. 扩展 DataStore（User CRUD）
5. 修改 `app/api/pm.py`（添加 Depends + 用户隔离）
6. 实现前端 `LoginView.vue` + `AuthStore`
7. 实现 `api/client.ts` 拦截器 + 路由守卫
8. 实现管理员用户管理页面
9. 修改 `AppLayout.vue`（用户信息 + 登出）
10. 自测 + 验证
