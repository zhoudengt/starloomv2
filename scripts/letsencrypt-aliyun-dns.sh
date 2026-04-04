#!/usr/bin/env bash
# 使用阿里云 DNS（万网）API 做 DNS-01，申请 Let’s Encrypt，解决微信/浏览器「证书不受信任」。
# 公网若经阿里云 Beaver/WAF，HTTP-01 的 /.well-known 可能返回 403，必须用本脚本或手动 TXT。
#
# 前置：在阿里云 RAM 创建子用户，授权 AliyunDNSFullAccess（或仅 DNS 写权限），创建 AccessKey。
# 在服务器执行：
#   export Ali_Key='LTAI...'
#   export Ali_Secret='...'
#   export DOMAIN=starloom.com.cn   # 可选
#   bash scripts/letsencrypt-aliyun-dns.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${DOMAIN:-starloom.com.cn}"

export Ali_Key="${Ali_Key:?请先 export Ali_Key= 与 Ali_Secret=（阿里云 RAM AccessKey）}"
export Ali_Secret="${Ali_Secret:?}"

mkdir -p "$ROOT/deploy/ssl"

echo ">>> 使用 acme.sh + dns_ali 申请证书: $DOMAIN"

~/.acme.sh/acme.sh --issue --dns dns_ali -d "$DOMAIN" --keylength ec-256

~/.acme.sh/acme.sh --install-cert -d "$DOMAIN" --ecc \
  --key-file "$ROOT/deploy/ssl/privkey.pem" \
  --fullchain-file "$ROOT/deploy/ssl/fullchain.pem" \
  --reloadcmd "podman exec starloom-nginx nginx -s reload 2>/dev/null || true"

echo ">>> 已写入 $ROOT/deploy/ssl/fullchain.pem 与 privkey.pem，并已尝试 reload Nginx。"
echo ">>> 请确认根目录 .env 未把 SSL_FULLCHAIN_HOST 指到旧路径；默认使用 deploy/ssl/ 即可。"
