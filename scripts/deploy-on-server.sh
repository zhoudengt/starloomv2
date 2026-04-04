#!/usr/bin/env bash
# 在服务器上执行：安装 Docker（若缺失）、生成临时自签证书（若未配置 LE）、构建前端并启动生产 Compose。
# 用法：cd /opt/starloomv2 && bash scripts/deploy-on-server.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/.env" ]] || [[ ! -f "$ROOT/backend/.env" ]]; then
  echo "请先复制并编辑: cp .env.example .env && cp backend/.env.example backend/.env"
  exit 1
fi

# 加载根 .env（若值中含空格/特殊字符，请在 .env 内用引号包裹）
set -a
# shellcheck disable=SC1091
source "$ROOT/.env"
set +a

if ! command -v docker &>/dev/null; then
  echo ">>> 安装 Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker 2>/dev/null || true
fi

if ! docker compose version &>/dev/null; then
  echo "未检测到 docker compose 插件，请安装 Docker Compose V2。"
  exit 1
fi

mkdir -p "$ROOT/deploy/ssl" "$ROOT/deploy/letsencrypt-webroot"

have_cert=0
if [[ -n "${SSL_FULLCHAIN_HOST:-}" ]] && [[ -f "${SSL_FULLCHAIN_HOST}" ]]; then
  have_cert=1
elif [[ -f "$ROOT/deploy/ssl/fullchain.pem" ]]; then
  have_cert=1
fi

if [[ "$have_cert" -eq 0 ]]; then
  echo ">>> 未找到正式证书，生成临时自签证书（浏览器会提示不安全）。拿到 Let’s Encrypt 后请改 .env 并重启 nginx："
  echo "    bash scripts/issue-letsencrypt-webroot.sh"
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$ROOT/deploy/ssl/privkey.pem" \
    -out "$ROOT/deploy/ssl/fullchain.pem" \
    -subj "/CN=${DOMAIN:-starloom.com.cn}"
fi

echo ">>> 构建前端..."
cd "$ROOT/frontend"
npm ci
npm run build
cd "$ROOT"

echo ">>> 启动容器..."
docker compose -f docker-compose.prod.yml up -d --build

echo ">>> 完成。请确认域名 DNS A 记录指向本机公网 IP，访问: https://${DOMAIN:-你的域名}"
docker compose -f docker-compose.prod.yml ps
