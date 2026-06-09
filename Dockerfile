# ===== ReQCollect — 多阶段 Docker 构建 =====
# Builder: Python 依赖安装
# Runtime: python:3.11-slim + 前端预构建 dist + 后端代码
#
# 注意：前端在宿主机构建（npm run build），Docker 不负责前端构建
# 这样可以避免 Docker layer cache 导致前端未更新的问题

# ── Stage 1: Python Builder ──
FROM python:3.11-slim AS python-builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e ".[dev]" && \
    pip install gunicorn cryptography

# ── Stage 2: Runtime ──
FROM python:3.11-slim

WORKDIR /app

# Python site-packages
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# 前端构建产物（宿主机构建，非 Docker 内构建）：确保构建后再部署
COPY reqcollect-web/dist/ ./reqcollect-web/dist/

# 应用代码
COPY app/ ./app/

# 创建运行时目录
RUN mkdir -p pm_data logs

EXPOSE 9900

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9900/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9900"]
