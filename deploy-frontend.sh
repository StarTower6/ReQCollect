#!/bin/bash
# deploy-frontend.sh — 构建前端并部署到 Docker
# 用法: ./deploy-frontend.sh
# 每次前端改动后执行此脚本

set -e
cd "$(dirname "$0")"

echo "=== 1. 构建前端 ==="
rm -rf reqcollect-web/dist
cd reqcollect-web && npm run build && cd ..
echo "=== 2. 重新构建 Docker 镜像 (无缓存) ==="
docker compose build --no-cache reqcollect
echo "=== 3. 重启容器 ==="
docker compose up -d reqcollect
echo "=== 4. 检查健康状态 ==="
sleep 3
curl -s http://localhost:9900/api/health
echo ""
echo "=== 部署完成 ==="