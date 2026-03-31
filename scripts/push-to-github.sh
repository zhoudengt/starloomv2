#!/usr/bin/env bash
# 在 GitHub 上创建 starloomv2 仓库并推送 main（与八字项目无关，仅本目录 git）
set -euo pipefail

REPO_NAME="starloomv2"
GITHUB_USER="zhoudengt"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REMOTE_URL="git@github.com:${GITHUB_USER}/${REPO_NAME}.git"

ensure_remote() {
  git remote remove origin 2>/dev/null || true
  git remote add origin "$REMOTE_URL"
}

if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  echo ">>> 使用 GITHUB_TOKEN 检查/创建远程仓库…"
  code=$(curl -sS -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${GITHUB_USER}/${REPO_NAME}")

  if [[ "$code" == "404" ]]; then
    curl -sS -X POST \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      "https://api.github.com/user/repos" \
      -d "{\"name\":\"${REPO_NAME}\",\"private\":false,\"description\":\"StarLoom v2 — 星座性格分析 H5\"}" \
      | head -c 300
    echo ""
    echo ">>> 仓库已创建。"
  elif [[ "$code" == "200" ]]; then
    echo ">>> 远程仓库已存在，直接推送。"
  else
    echo ">>> 无法访问 GitHub API (HTTP $code)。请检查 Token 权限（需 repository 创建/写入）。"
    exit 1
  fi

  ensure_remote
  git push -u origin main
  echo ">>> 完成: https://github.com/${GITHUB_USER}/${REPO_NAME}"
  exit 0
fi

echo "未设置 GITHUB_TOKEN。任选一种方式："
echo ""
echo "【方式 A】网页创建空仓库后推送（不要勾选 README / .gitignore）："
echo "  1) 打开: https://github.com/new?name=${REPO_NAME}&visibility=public"
echo "  2) 在本目录执行:"
echo "       git push -u origin main"
echo ""
echo "【方式 B】用 Personal Access Token 一键（需 repo 权限）："
echo "  export GITHUB_TOKEN=ghp_你的令牌"
echo "  ./scripts/push-to-github.sh"
echo ""
ensure_remote
echo "当前 remote 已设为: $REMOTE_URL"
exit 1
