# StarLoom 生产部署指南

> 本文件供任何开发者或 AI 模型自主完成从代码更新到上线的全流程。
> 按顺序执行即可，无需额外背景知识。

**流程约束（与 `.cursorrules`、`.cursor/rules/deployment-workflow.mdc` 一致）**

- 业务代码**必须在本机改完并提交到 Git 仓库**后再部署；**禁止**在生产服务器上直接改源码替代这一流程。
- 服务器上只做：**拉取仓库** → **构建/发布**（本文后续步骤）。

---

## 1. 环境概览

| 项目 | 值 |
|------|------|
| 服务器 IP | `39.105.50.74` |
| SSH 用户 | `root`（已配置免密登录） |
| 项目路径 | `/opt/starloomv2` |
| 域名 | `starloom.com.cn` |
| 容器引擎 | **podman 4.9 + podman-compose 1.0.6**（`docker` / `docker compose` 命令均为 podman alias，用法一致） |
| Node.js | v20.x（宿主机已装） |
| Git remote | `https://github.com/zhoudengt/starloomv2.git`（HTTPS，无需 token 即可 pull 公开仓库） |

### 容器与端口

| 容器名 | 镜像 | 宿主机端口 |
|--------|------|-----------|
| starloom-mysql | mysql:8.0 | 127.0.0.1:3307 → 3306 |
| starloom-redis | redis:7-alpine | 127.0.0.1:6380 → 6379 |
| starloom-backend | 本地构建 | 不暴露（nginx 反代） |
| starloom-nginx | nginx:alpine | 0.0.0.0:80, 0.0.0.0:443 |

### 关键配置文件（均不入 Git）

- **`/opt/starloomv2/.env`** — compose 编排用（`DB_PASSWORD`、`DOMAIN`、SSL 路径）
- **`/opt/starloomv2/backend/.env`** — 后端应用用（API Key、支付密钥、`FRONTEND_URL` 等）

> `backend/.env` 中 `DB_HOST=localhost` 和 `REDIS_HOST=localhost` 在容器内会被
> `docker-compose.prod.yml` 的 `environment:` 覆盖为 `starloom-mysql` / `starloom-redis`，
> 无需手动改。

---

## 2. 部署步骤

以下命令均在服务器上以 root 执行。可通过 `ssh root@39.105.50.74` 登录。

### 2.1 拉取最新代码

```bash
cd /opt/starloomv2
git pull origin main
```

若提示认证失败（私有仓库），需配置 GitHub token：
```bash
git remote set-url origin https://<TOKEN>@github.com/zhoudengt/starloomv2.git
```

### 2.2 检查 backend/.env 是否缺少新变量

对照 `backend/.env.example` 检查，当前版本新增了：

```
BAILIAN_APP_ID_PLANNER=<从百炼控制台获取>
BAILIAN_APP_ID_PROFILE_EXTRACTOR=<从百炼控制台获取>
```

若暂时没有，可留空（相关功能降级但不影响核心启动）：
```bash
grep -q 'BAILIAN_APP_ID_PLANNER' backend/.env || echo -e '\nBAILIAN_APP_ID_PLANNER=\nBAILIAN_APP_ID_PROFILE_EXTRACTOR=' >> backend/.env
```

### 2.3 构建前端

```bash
cd /opt/starloomv2/frontend
npm ci
npm run build
cd /opt/starloomv2
```

产物输出到 `frontend/dist/`，nginx 容器以 `:ro` 挂载此目录。

### 2.4 构建并重启容器

```bash
cd /opt/starloomv2
docker compose -f docker-compose.prod.yml up -d --build
```

> 该命令会：重建 backend 镜像（含新代码）、重启 backend 和 nginx，mysql/redis 数据卷不受影响。

等待所有容器就绪：
```bash
docker compose -f docker-compose.prod.yml ps
```

确认 mysql 为 `healthy`，其余为 `Up`。

### 2.5 数据库迁移

后端启动时 SQLAlchemy `create_all` 会自动建新表（`articles`、`daily_guides`、`daily_tips` 等）。
但 IR 列需要额外 ALTER：

```bash
podman exec -i starloom-mysql mysql -uroot -p123456 starloom < scripts/migrations/add_content_ir_columns.sql
```

> 若列已存在会报 `Duplicate column name`，可安全忽略。

### 2.6 验证

```bash
# 健康检查
curl -s https://starloom.com.cn/health | head -c 200

# 轮播 API
curl -s 'https://starloom.com.cn/api/v1/articles?carousel=1&limit=2' | head -c 300

# 首页 HTML
curl -s -o /dev/null -w '%{http_code}' https://starloom.com.cn/
```

期望：health 返回 JSON、articles 返回 200（items 可能为空但不应 500）、首页 200。

### 2.7 可选：回填 IR 数据

若数据库中已有旧文章/指南/报告且想补充 IR 字段：

```bash
podman exec starloom-backend python -c "
import asyncio, sys; sys.path.insert(0,'/app')
from app.database import AsyncSessionLocal, engine
from app.models.article import Article
from app.models.daily_guide import DailyGuide
from app.models.report import Report
from app.services.ir_converter import markdown_to_ir
from sqlalchemy import select, update

async def main():
    async with AsyncSessionLocal() as db:
        for a in (await db.execute(select(Article).where(Article.body_ir.is_(None)))).scalars().all():
            ir = markdown_to_ir(a.body, {'title': a.title, 'cover_image': a.cover_image})
            await db.execute(update(Article).where(Article.id == a.id).values(body_ir=ir))
        for g in (await db.execute(select(DailyGuide).where(DailyGuide.content_ir.is_(None)))).scalars().all():
            ir = markdown_to_ir(g.content, {'title': g.title})
            await db.execute(update(DailyGuide).where(DailyGuide.id == g.id).values(content_ir=ir))
        for r in (await db.execute(select(Report).where(Report.content_ir.is_(None)))).scalars().all():
            ir = markdown_to_ir(r.content, {})
            await db.execute(update(Report).where(Report.id == r.id).values(content_ir=ir))
        await db.commit(); print('backfill ok')
    await engine.dispose()
asyncio.run(main())
"
```

---

## 3. 回滚方案

### 快速回滚（代码级）

```bash
cd /opt/starloomv2

# 记录当前 commit
git rev-parse HEAD > /tmp/starloom-rollback-hash

# 回退到上一个版本
git checkout <旧commit-hash>

# 重新构建并重启
cd frontend && npm ci && npm run build && cd ..
docker compose -f docker-compose.prod.yml up -d --build
```

### 目录级备份（已有先例）

部署前可手动备份：
```bash
cp -r /opt/starloomv2 /opt/starloomv2.bak.$(date +%Y%m%d%H%M%S)
```

回滚时直接：
```bash
rm -rf /opt/starloomv2
mv /opt/starloomv2.bak.XXXXXXXX /opt/starloomv2
cd /opt/starloomv2 && docker compose -f docker-compose.prod.yml up -d --build
```

---

## 4. 常用运维命令

```bash
# === 日志 ===
podman logs -f --tail 100 starloom-backend    # 后端实时日志
podman logs -f --tail 50  starloom-nginx      # Nginx 访问/错误日志

# === 重启单个容器 ===
podman restart starloom-backend
podman restart starloom-nginx

# === 进入 MySQL ===
podman exec -it starloom-mysql mysql -uroot -p123456 starloom

# === 进入后端容器 ===
podman exec -it starloom-backend bash

# === 查看容器状态 ===
docker compose -f docker-compose.prod.yml ps

# === 完全停止 ===
docker compose -f docker-compose.prod.yml down
# 注意：down 不会删除 volume（数据安全）

# === 证书续期（Let's Encrypt） ===
cd /opt/starloomv2 && bash scripts/issue-letsencrypt-webroot.sh
# 续期后重启 nginx：
podman restart starloom-nginx
```

---

## 5. 注意事项

1. **podman ≠ Docker**：服务器用 podman 4.9 + podman-compose 1.0.6 模拟 Docker CLI。
   `docker` 和 `docker compose` 命令可用，但底层是 podman。
   `depends_on.condition: service_healthy` 在 podman-compose 中可能不完全生效，
   若 backend 启动时 mysql 未 ready，backend 会自动重试连接。

2. **前端每次必须在服务器构建**：`frontend/dist/` 不入 Git，nginx 直接挂载宿主机的 `dist/` 目录。

3. **`.env` 绝不提交**：根目录 `.env` 和 `backend/.env` 均在 `.gitignore` 中。
   `git pull` 不会覆盖它们。

4. **backend/.env 中的 DB_HOST / REDIS_HOST**：写的是 `localhost`（方便本地开发），
   但 `docker-compose.prod.yml` 通过 `environment:` 在容器内覆盖为 `starloom-mysql` / `starloom-redis`。

5. **新增 env var**：每次部署前对照 `backend/.env.example` 检查是否有新变量。
   缺少非关键变量不会阻止启动，但相关功能会降级。

6. **数据库迁移**：新表由 ORM `create_all` 自动建；ALTER 类迁移（如加列）
   需手动执行 `scripts/migrations/` 下的 SQL。

7. **SSL 证书**：当前使用自签证书（`deploy/ssl/`）。
   正式证书申请：`bash scripts/issue-letsencrypt-webroot.sh`，
   申请后在 `.env` 中设置 `SSL_FULLCHAIN_HOST` / `SSL_PRIVKEY_HOST` 路径并重启 nginx。

---

## 6. 一键部署脚本

若以上步骤都已理解，也可直接在服务器执行已有脚本：

```bash
cd /opt/starloomv2
git pull origin main
bash scripts/deploy-on-server.sh
```

该脚本会自动：检查 `.env`、安装 Docker（若缺）、生成自签证书（若无）、`npm ci && npm run build`、`docker compose up -d --build`。

**脚本执行后仍需手动**：
- 补全 `backend/.env` 中的新变量
- 执行 `scripts/migrations/add_content_ir_columns.sql`（若有新迁移）
