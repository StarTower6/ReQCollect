# ===== ReQCollect — 多阶段 Docker 构建 =====
# Builder: 安装项目依赖
# Runtime: python:3.11-slim + 最小运行时

# ── Stage 1: Builder ──
FROM python:3.11-slim AS builder

WORKDIR /build

# 系统依赖（编译某些 Python 包需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖声明以利用缓存
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir gunicorn cryptography

# ── Stage 2: Runtime ──
FROM python:3.11-slim

WORKDIR /app

# 从 builder 复制 site-packages（含所有依赖）
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY app/ ./app/
COPY static/ ./static/

# 创建运行时目录
RUN mkdir -p pm_data logs

# 暴露端口
EXPOSE 9900

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9900/api/health')" || exit 1

# 默认启动（可用 gunicorn 覆盖）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9900"]
