#!/usr/bin/env bash
# 站点已能访问（含自签 HTTPS）且 DNS 已指向本机后，用 HTTP-01 申请/续期 Let’s Encrypt。
# 用法：DOMAIN=starloom.com.cn bash scripts/issue-letsencrypt-webroot.sh
# 需已安装 certbot（如: yum install certbot / apt install certbot）。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

set -a
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"
set +a

D="${DOMAIN:-}"
if [[ -z "$D" ]]; then
  echo "请在 .env 中设置 DOMAIN= 或环境变量 DOMAIN="
  exit 1
fi

WEBROOT="$ROOT/deploy/letsencrypt-webroot"
mkdir -p "$WEBROOT"

echo ">>> certbot webroot: $WEBROOT  domain: $D"
if [[ -n "${CERTBOT_EMAIL:-}" ]]; then
  certbot certonly --webroot -w "$WEBROOT" -d "$D" --agree-tos --non-interactive --email "$CERTBOT_EMAIL"
else
  certbot certonly --webroot -w "$WEBROOT" -d "$D" --agree-tos --non-interactive --register-unsafely-without-email
fi

echo ">>> 将根目录 .env 中证书路径设为（示例）："
echo "SSL_FULLCHAIN_HOST=/etc/letsencrypt/live/$D/fullchain.pem"
echo "SSL_PRIVKEY_HOST=/etc/letsencrypt/live/$D/privkey.pem"
echo ">>> 然后执行: cd $ROOT && docker compose -f docker-compose.prod.yml up -d --force-recreate nginx"
