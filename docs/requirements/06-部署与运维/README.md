# 06 — 部署与运维

## 概述

当前 uvicorn 裸跑。企业级需要容器化、服务守护、监控告警和 CI/CD。

## 当前状态 ✅ 已实现

- [x] uvicorn 单进程启动
- [x] Python 3.11+ FastAPI 应用
- [x] 零外部中间件依赖（启动即可用）

## 待实现 🔲

### 容器化（P0）
- [ ] **Dockerfile** — 基于 python:3.11-slim 的多阶段构建
  ```dockerfile
  FROM python:3.11-slim AS builder
  COPY . /app
  RUN pip install --no-cache-dir .

  FROM python:3.11-slim
  COPY --from=builder /app /app
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9900"]
  ```
- [ ] **Docker Compose 编排**
  ```yaml
  services:
    reqcollect:
      build: .
      ports: ["9900:9900"]
      env_file: .env
      volumes: ["./pm_data:/app/pm_data"]
    postgres:   # 企业级可选
      image: postgres:16
      volumes: ["pgdata:/var/lib/postgresql/data"]
  ```
- [ ] **健康检查** — Docker HEALTHCHECK + FastAPI /api/health

### 服务管理（P1）
- [ ] **多 worker** — 使用 gunicorn + uvicorn workers 提升并发
- [ ] **进程守护** — systemd unit 文件，自动重启
- [ ] **优雅关闭** — 收到 SIGTERM 时完成当前请求再退出

### 反向代理（P1）
- [ ] **Nginx 反向代理** — SSL 终止、静态文件缓存、SSE 连接优化
  ```
  location /api/pm/ {
      proxy_pass http://127.0.0.1:9900;
      proxy_set_header Connection '';
      proxy_http_version 1.1;
      chunked_transfer_encoding off;
      proxy_buffering off;
      proxy_cache off;
  }
  ```
- [ ] **HTTPS** — Let's Encrypt 自动续签

### 监控告警（P2）
- [ ] **Prometheus Metrics** — FastAPI metrics 端点（请求数、延迟、错误率）
- [ ] **结构化日志** — JSON 格式日志，方便 ELK/Loki 采集
- [ ] **告警规则** — 服务宕机、API 错误率 > 5%、LLM 调用超时

### CI/CD（P2）
- [ ] **GitHub Actions** — PR 自动 lint + test + build
- [ ] **自动部署** — master 分支推送 → 自动构建 Docker 镜像 → 部署到测试环境
- [ ] **版本管理** — 语义化版本 + Change Log

### 配置管理（P1）
- [ ] **环境隔离** — dev/staging/production 三套独立 .env
- [ ] **配置校验** — 启动时校验关键配置（API Key 可达性、数据库连接）
- [ ] **API Rate Limit** — 限制单用户每分钟调用次数
