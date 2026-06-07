# ===== ReQCollect — 多阶段 Docker 构建 =====
# Builder 1: Node.js 前端构建
# Builder 2: Python 依赖安装
# Runtime: python:3.11-slim + 前端 dist + 后端代码

# ── Stage 1: Frontend Builder ──
FROM node:22-alpine AS frontend-builder

WORKDIR /build
COPY reqcollect-web/package.json reqcollect-web/package-lock.json* ./
RUN npm ci
COPY reqcollect-web/ .
RUN npm run build

# ── Stage 2: Python Builder ──
FROM python:3.11-slim AS python-builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir gunicorn cryptography

# ── Stage 3: Runtime ──
FROM python:3.11-slim

WORKDIR /app

# Python site-packages
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# 前端构建产物 (Vue SPA)
COPY --from=frontend-builder /build/dist/ ./reqcollect-web/dist/

# 应用代码
COPY app/ ./app/
COPY static/ ./static/

# 创建运行时目录
RUN mkdir -p pm_data logs

EXPOSE 9900

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9900/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9900"]
