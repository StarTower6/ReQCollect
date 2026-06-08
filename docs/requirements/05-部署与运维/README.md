# 05 — 部署与运维

## 概述

系统已通过 Docker Compose 实现容器化部署（三容器：应用 + MySQL 8.0 + Nginx）。企业级需要进一步增强监控、CI/CD 和生产环境加固。

## 当前状态 ✅ 已实现

### 已实现的基础功能

- [x] **Docker 多阶段构建** — `Dockerfile` 三段式（Node.js 前端构建 → Python 依赖安装 → Python 3.11-slim 运行镜像）
- [x] **Docker Compose 编排** — `docker-compose.yml` 含三服务（app / mysql / nginx），共享网络 `reqcollect-net`
- [x] **服务健康检查** — 应用 `HEALTHCHECK`（每 30s 检测 `/api/health`）+ MySQL 健康检查（mysqladmin ping）
- [x] **Nginx 反向代理** — 端口 8082 → 反向代理到应用 9900，配置 SSE 优化（proxy_buffering off）
- [x] **MySQL 持久化** — 命名卷 `reqcollect-mysql-data`，初始化脚本 `scripts/init.sql` 自动导入
- [x] **数据持久化** — `pm_data/` 和 `logs/` 目录卷挂载
- [x] **自动重启策略** — `restart: unless-stopped` 确保服务崩溃后自动拉起
- [x] **服务依赖** — app 依赖 mysql（wait for healthy），nginx 在 app 启动后接上
- [x] **优雅关闭** — uvicorn 内置 SIGTERM 处理
- [x] **启动配置校验** — `app/main.py` 启动时校验关键配置项可达性
- [x] **环境隔离** — `.env.docker` 和 `.env` 两套配置，开发/容器环境分离

### 部署架构

```
用户 → Nginx:8082 (反向代理) → uvicorn:9900 (FastAPI)
                                    │
                              MySQL:3306 (SQLAlchemy + aiomysql)
```

## 待实现 🔲

### 服务管理（P1）

- [ ] **多 worker** — 使用 gunicorn + uvicorn workers (`gunicorn -w 4 -k uvicorn.workers.UvicornWorker`) 提升并发处理能力
- [ ] **进程守护** — 不使用 Docker 时，systemd unit 文件确保自启动与自动重启

### HTTPS 与域名（P1）

- [ ] **HTTPS** — Let's Encrypt 自动续签，Nginx 配置 SSL 终止
- [ ] **域名绑定** — 配置正式域名（如 reqcollect.gree.com），Nginx server_name 绑定

### 监控告警（P2）

- [ ] **Prometheus Metrics** — 暴露 `/api/metrics` 端点（请求数、延迟、错误率）
- [ ] **结构化日志** — JSON 格式日志，方便 ELK/Loki 采集
- [ ] **告警规则** — 服务宕机、API 错误率 > 5%、LLM 调用超时

### CI/CD（P2）

- [ ] **GitHub Actions** — PR 自动 lint + test + build
- [ ] **自动部署** — master 分支推送 → 自动构建 Docker 镜像 → 部署到测试环境
- [ ] **语义化版本** — 版本号管理 + Change Log + Git Tag

### 限流与安全（P1）

- [ ] **API Rate Limit** — 限制单用户每分钟调用次数（如 60 req/min），防止异常流量
- [ ] **请求大小限制** — Nginx `client_max_body_size` 限制上传文件大小
