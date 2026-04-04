#!/usr/bin/env bash
# 从本机把代码同步到服务器（需 SSH 公钥已配置到服务器）。不会覆盖服务器上的 .env / backend/.env。
# 用法：export DEPLOY_HOST=root@你的服务器IP  && bash scripts/rsync-to-server.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${DEPLOY_HOST:?请先 export DEPLOY_HOST=用户@服务器}"

rsync -avz \
  --exclude '.git/' \
  --exclude 'frontend/node_modules/' \
  --exclude 'backend/.venv/' \
  --exclude 'backend/.env' \
  --exclude '.env' \
  --exclude 'frontend/dist/' \
  --exclude '.DS_Store' \
  "$ROOT/" "$HOST:/opt/starloomv2/"

echo ">>> 同步完成。登录服务器后在 /opt/starloomv2 配置 .env 与 backend/.env，执行:"
echo "    bash scripts/deploy-on-server.sh"
