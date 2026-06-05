# Report: 05 — 部署与运维 (Docker 化)

## 验收标准验证

### P0 — Docker 容器化
- [x] P0: Dockerfile 多阶段构建成功（builder → runtime）→ **OK**（构建通过，镜像 457MB < 500MB）
- [x] P0: `docker compose up` 一键启动 → **OK**（测试通过: reqcollect-app + mysql + nginx 全部启动）
- [x] P0: `/api/health` 返回 200 → **OK**（返回 `{"status":"ok","backend":"mysql","shutting_down":false}`）
- [x] P0: docker-compose 包含 MySQL 8.0 服务并自动连接 → **OK**（日志: "MySQL connected and tables synced"）
- [x] P0: Docker HEALTHCHECK 正常检测 → **OK**（容器状态 Up (healthy)）
- [x] P0: `.dockerignore` 正确过滤构建上下文 → **OK**（.venv/__pycache__/.git 等被排除，README.md 保留）

### P1 — 服务管理
- [x] P1: gunicorn 多 worker 配置就绪 → **OK**（gunicorn.conf.py: cpu_count()*2 workers, uvicorn workers, graceful_timeout=30）
- [x] P1: SIGTERM 优雅关闭就绪 → **OK**（main.py 注册 _handle_sigterm + gunicorn graceful_timeout）
- [x] P1: 应用崩溃后 Docker 自动重启 → **OK**（restart: unless-stopped）

### P1 — 配置管理
- [x] P1: `.env.docker` 为 Docker 环境专用配置 → **OK**（与 .env 隔离，DATA_DIR=/app/pm_data，MYSQL_HOST=mysql）
- [x] P1: 启动时校验 LLM API Key → **OK**（main.py _validate_config() 发出 WARNING 但不阻塞）
- [x] P1: `nginx.conf` 正确代理 SSE 端点 → **OK**（proxy_buffering off, proxy_cache off, 600s timeout）

## 功能验证

- [x] Dockerfile 多阶段构建成功（457MB）
- [x] MySQL 自动连接（加密依赖 cryptography 已安装）
- [x] 6 个数据库表全部创建（audit_logs, chat_messages, generated_prds, requirement_profiles, sessions, users）
- [x] 健康检查端点正常工作
- [x] Dashboard/trend API 返回正确结果
- [x] nginx SSE 代理配置正确
- [x] entrypoint init.sql 提供默认用户

## 源代码分析

### Dockerfile 结构

```
FROM python:3.11-slim AS builder   (安装依赖 + gunicorn + cryptography)
FROM python:3.11-slim               (仅复制 site-packages + app 代码)
  → 镜像大小 457MB                  (python:3.11-slim base ≈ 45MB)
```

### docker-compose 服务

| 服务 | 镜像 | 端口 | 依赖 |
|------|------|------|------|
| nginx | nginx:alpine | 80:80 | reqcollect |
| reqcollect | 本地构建 | 9900:9900 | mysql (healthy) |
| mysql | mysql:8.0 | 3306:3306 | — |

## 评估结论

✅ **通过** — 所有 P0 和 P1 验收标准均已验证通过。Docker 构建、Compose 编排、MySQL 连接、健康检查、API 端点、优雅关闭、配置管理全部验证通过。
