# Plan: 03 — 用户认证与隔离

## 1. 任务理解
- 需求来源: `docs/requirements/03-用户与权限/README.md`
- 核心目标: 实现用户认证（登录/注册/JWT）和用户隔离（个人会话空间 + 用户管理），将当前无用户共用系统升级为企业级多用户系统

## 2. 改动清单
- 新增文件:
  - `app/core/auth.py` — JWT 工具 + 密码哈希 + FastAPI 依赖注入
  - `app/api/auth.py` — 认证路由（login/register/me/users）
  - `tests/test_auth.py` — 认证模块测试
  - `reqcollect-web/src/views/LoginView.vue` — 登录页面
  - `reqcollect-web/src/stores/auth.ts` — 前端认证状态管理
  - `reqcollect-web/src/views/admin/UsersView.vue` — 管理员用户管理页面
- 修改文件:
  - `app/config.py` — 添加 JWT 配置字段
  - `app/api/pm.py` — 所有端点添加 `Depends(get_current_user)` + 会话归属检查
  - `app/db/__init__.py` — DataStore 抽象类增加 User CRUD
  - `app/db/compat.py` — FileDataStore 实现 User CRUD
  - `app/db/repository.py` — MySQLDataStore 实现 User CRUD
  - `app/main.py` — 注册 auth router + 启动时初始化 admin 用户
  - `pyproject.toml` — 新增依赖 python-jose, passlib[bcrypt]
  - `reqcollect-web/src/api/client.ts` — 添加 Authorization 拦截器 + 401 处理
  - `reqcollect-web/src/router/index.ts` — 添加 /login 和 /admin/users 路由 + 导航守卫
  - `reqcollect-web/src/components/layout/AppLayout.vue` — 添加用户信息 + 登出
  - `reqcollect-web/src/stores/session.ts` — 初始化时检查登录状态

## 3. 数据模型
- User 表已存在于 MySQL ORM 模型（`app/db/models.py`），无需改表结构
- FileDataStore 新增 `pm_data/users/users.json` 存储用户
- 出场管理员: admin / admin123

## 4. 验收标准
- [ ] P0: POST /api/auth/login 返回 JWT Token（24h 有效期）
- [ ] P0: 无效 Token 请求 /api/pm/* 返回 401
- [ ] P0: 普通用户只能看到自己的会话
- [ ] P0: 前端 /login 页面可正常登录
- [ ] P0: 登录后自动跳转到 /chat
- [ ] P0: Token 过期或无效时自动跳转登录页
- [ ] P0: 出场管理员 admin 可正常登录
- [ ] P1: 注册新用户 POST /api/auth/register
- [ ] P1: GET /api/auth/me 返回当前用户信息
- [ ] P1: 管理员可查看所有用户
- [ ] P1: 管理员可启用/禁用用户
- [ ] P1: 管理员用户管理界面
- [ ] P1: 现有 API 回退兼容（不影响未登录的 /api/health）

## 5. 风险与依赖
- 新增依赖: `python-jose`, `passlib[bcrypt]` — 需更新 pyproject.toml
- API 兼容: 所有 /api/pm/* 新增 `Depends(get_current_user)`，未登录请求返回 401（之前返回数据）
- 前端 sessionStore 初始化需等待 AuthStore 加载完 token

## 6. 实施步骤 (按顺序)
1. 新增依赖 + 配置字段
2. 实现 core/auth.py（JWT + 密码 + 依赖注入）
3. 扩展 DataStore（User CRUD 抽象 + FileDataStore + MySQLDataStore）
4. 实现 api/auth.py（认证路由）
5. 修改 api/pm.py（所有端点添加 Depends + 归属检查）
6. 修改 main.py（注册路由 + 出场管理员初始化）
7. 实现前端 AuthStore + api/client.ts 拦截器
8. 实现 LoginView.vue + 路由守卫
9. 实现管理员用户管理页面
10. 修改 AppLayout.vue
11. 编写测试 + 验证
