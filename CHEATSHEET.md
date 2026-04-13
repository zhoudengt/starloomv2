# StarLoom v2 操作速查

## 1. 提交代码到 Git

```bash
cd /Users/zhoudt/Downloads/project/starloomv2
git add -A
git commit -m "描述改动"
git push origin main
```

## 2. 服务器拉取 + 发布

```bash
ssh root@39.105.50.74
cd /opt/starloomv2
git pull origin main
cd frontend && npm ci && npm run build && cd ..
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl -s https://starloom.com.cn/health
```

## 3. 手动触发每日任务

| 任务 | 自动执行时间（北京时间） | 说明 |
|------|-------------------------|------|
| 每日运势预生成 | 00:05 | 12 星座今日运势写入 DB |
| 每日指南生成 | 00:30 | 12 星座生活指南写入 DB |
| 统一日包（抖音+轮播） | 00:20 | 抖音文案图片 + H5 轮播文章 |

### 服务器（后端容器内）

**每日运势预生成**

```bash
podman exec starloom-backend python -c "
import asyncio, sys; sys.path.insert(0,'/app')
from app.database import AsyncSessionLocal
from app.services.public_daily_fortune import prefetch_all_public_daily_for_date
from app.utils.beijing_date import fortune_date_beijing
async def go():
    d = fortune_date_beijing()
    async with AsyncSessionLocal() as db:
        await prefetch_all_public_daily_for_date(db, d)
        await db.commit()
        print(f'done: {d}')
asyncio.run(go())
"
```

**每日指南生成**

```bash
podman exec starloom-backend python -c "
import asyncio, sys; sys.path.insert(0,'/app')
from app.database import AsyncSessionLocal
from app.services.guide_generator import generate_all_guides_for_date
from app.utils.beijing_date import fortune_date_beijing
async def go():
    d = fortune_date_beijing()
    async with AsyncSessionLocal() as db:
        count = await generate_all_guides_for_date(db, d)
        await db.commit()
        print(f'done: {count} guides for {d}')
asyncio.run(go())
"
```

**统一日包（抖音+轮播）**

```bash
podman exec starloom-backend python -m ops.cli daily
podman exec starloom-backend python -m ops.cli daily --no-media
```

### 本地（开发机）

```bash
cd backend && source .venv/bin/activate
python -m ops.cli daily
python -m ops.cli daily --no-media
python -m ops.cli preview
```

## 4. 重启本地开发服务

**后端**

```bash
pkill -f "uvicorn app.main:app" 2>/dev/null
cd /Users/zhoudt/Downloads/project/starloomv2/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
curl -s http://127.0.0.1:8000/health
```

**前端**

```bash
cd /Users/zhoudt/Downloads/project/starloomv2/frontend
npm run dev
```

## 5. 重启服务器容器

```bash
ssh root@39.105.50.74
podman restart starloom-backend
cd /opt/starloomv2 && docker compose -f docker-compose.prod.yml restart
podman logs -f --tail 50 starloom-backend
```

## 6. 输出目录

| 路径 | 内容 |
|------|------|
| `backend/ops/out/YYYY-MM-DD/douyin_publish.md` | 抖音文案 |
| `backend/ops/out/YYYY-MM-DD/media/images/page_*.jpg` | 配图 |
| `backend/ops/out/YYYY-MM-DD/manifest.json` | 完整 JSON |
