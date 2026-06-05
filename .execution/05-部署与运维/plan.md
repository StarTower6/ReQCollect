# Plan: 05 — 部署与运维 (Docker 化)

## 1. 任务理解

- **需求来源**: `docs/requirements/05-部署与运维/README.md`
- **核心目标**: 将当前 uvicorn 裸跑的应用升级为完整的 Docker 化部署方案
- **用户选择**:
  - 范围: P0 容器化 + P1 服务管理 + P1 配置管理（不包含反向代理/监控/CI/CD）
  - docker-compose 含 MySQL 8.0 服务，开箱即用

## 2. 改动清单

### 新增文件

| 文件 | 优先级 | 说明 |
|------|--------|------|
| `Dockerfile` | P0 | 多阶段构建 (重写现有文件) |
| `.dockerignore` | P0 | 构建上下文过滤 |
| `docker-compose.yml` | P0 | 编排 reqcollect + MySQL + nginx (重写) |
| `nginx.conf` | P1 | 反向代理 + SSE 优化 (重写) |
| `.env.docker` | P1 | Docker 环境专用配置 |
| `.env.example` | P1 | 更新：新增 MySQL 示例 |
| `gunicorn.conf.py` | P1 | gunicorn + uvicorn workers 配置 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `app/main.py` | 添加 SIGTERM 优雅关闭处理、启动时配置校验 |

## 3. 架构图

```
                         ┌─────────────────┐
                         │    Nginx:80     │  ← 反向代理 / SSE 优化
                         │  (nginx.conf)   │
                         └────────┬────────┘
                                  │ proxy_pass
                         ┌────────▼────────┐
                         │  gunicorn:9900   │  ← 多 worker + 优雅关闭
                         │  uvicorn workers │
                         │  (gunicorn.conf) │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼────────┐ ┌───────▼────────┐ ┌───────▼────────┐
     │  ReQCollect App │ │  MySQL 8.0    │ │  pm_data/      │
     │  (Dockerfile)   │ │  :3306        │ │  (volume)      │
     └─────────────────┘ └────────────────┘ └────────────────┘
```

## 4. 验收标准

### P0 — Docker 容器化

- [ ] P0: `Dockerfile` 多阶段构建成功（builder → runtime），最终镜像 < 500MB
- [ ] P0: `docker-compose up` 一键启动，应用在 http://localhost:9900 可用
- [ ] P0: `/api/health` 返回 200
- [ ] P0: docker-compose 包含 MySQL 8.0 服务，应用自动连接 MySQL 而非 JSON 文件
- [ ] P0: Docker HEALTHCHECK 正常检测（30s 间隔）
- [ ] P0: `.dockerignore` 正确过滤 python缓存/虚拟环境/git

### P1 — 服务管理

- [ ] P1: gunicorn 多 worker 启动（4 workers），一启动即监听 9900
- [ ] P1: 收到 SIGTERM 时优雅关闭（完成当前请求再退出）
- [ ] P1: 应用崩溃后 Docker 自动重启（restart: unless-stopped）

### P1 — 配置管理

- [ ] P1: `.env.docker` 为 Docker 环境专用配置，与 `.env` 隔离
- [ ] P1: 启动时校验 LLM API Key 是否配置，缺失则 WARNING 但不阻塞
- [ ] P1: `nginx.conf` 正确代理 `/api/pm/` SSE 端点（proxy_buffering off）

### 不做（明确排除）

- ❌ P1 反向代理 HTTPS/SSL（Let's Encrypt，后续迭代）
- ❌ P2 Prometheus 监控
- ❌ P2 GitHub Actions CI/CD
- ❌ P2 结构化 JSON 日志
- ❌ P1 API Rate Limit

## 5. 风险与依赖

### 依赖

- Docker Engine 24+ / Docker Compose v2
- 镜像: `python:3.11-slim` (builder + runtime)
- 镜像: `mysql:8.0`
- 镜像: `nginx:alpine`

### 注意事项

1. **现有 docker-compose.yml 含 milvus/redis/etcd/minio** — 这些是原 PMAgent 的依赖，ReQCollect 不需要，直接替换
2. **已有一个 Dockerfile**（单阶段）— 重写为多阶段，不发 dev 依赖到运行时
3. **`.env` 已经有了 LLM_API_KEY 等配置** — 创建 `.env.docker` 作为 Docker 专用，不覆盖 `.env`
4. **pm_data 目录在 .gitignore 中** — Docker volume 挂载即可，不需提交
5. **MySQL 自动连接** — 应用已有 MySQL 回退逻辑，docker-compose 中 MySQL 就绪后会自然切换到 MySQL

## 6. 实施步骤

### Step 1: Dockerfile（多阶段构建）
- builder 阶段: 安装项目依赖
- runtime 阶段: python:3.11-slim，从 builder 复制 site-packages + app 代码
- HEALTHCHECK + 暴露 9900 端口

### Step 2: .dockerignore
- 过滤 .venv, __pycache__, .git, .env, pm_data, logs, .vscode 等

### Step 3: docker-compose.yml
- reqcollect 服务: build + env_file + volumes + depends_on mysql + restart
- mysql 服务: mysql:8.0 + healthcheck + volume + .env.docker 变量

### Step 4: Nginx 反向代理
- 重写 nginx.conf: 代理 `/api/pm/` + SSE 优化 + 静态缓存

### Step 5: gunicorn + 优雅关闭
- gunicorn.conf.py: 4 uvicorn workers
- main.py: SIGTERM 信号处理

### Step 6: 配置管理
- .env.docker: Docker 环境配置（含 MySQL 默认值）
- .env.example: 更新示例（新增 MySQL 配置项）
- main.py: 启动时配置校验

### Step 7: Evaluate
- 逐条验证验收标准
- 写 report.md
