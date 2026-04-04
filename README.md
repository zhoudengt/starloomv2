# StarLoom v2

AI 星座性格分析与运势参考 H5（抖音引流）。**本仓库根 README 面向人与 Cursor：先读本文再改代码**，可快速定位「页面在哪、接口在哪、后端在哪」。

更细的产品与架构说明：`docs/spec.md`、`docs/architecture.md`。开发规范：`.cursorrules`。

---

## 给 Cursor / 协作者：请先建立上下文

1. **改前端**：对照下方「路由 → 页面 → API」表，打开对应 `frontend/src/pages/*.tsx` 与 `frontend/src/api/*.ts`。
2. **改接口或 AI 文案**：后端入口 `backend/app/main.py`；业务路由在 `backend/app/api/`；Prompt 在 `backend/app/prompts/`；业务逻辑在 `backend/app/services/`。
3. **不确定用户指的是哪一页**：让用户提供 **URL 路径**（如 `/report/personality`）或 **底部 Tab 名称**（首页 / 运势 / 报告 / 我的），再查下表。

---

## 前端路由一览（页面在哪里）

路由定义在 `frontend/src/App.tsx`。Shell 内页面带底部导航（`frontend/src/components/BottomNav.tsx`）：`/`, `/fortunes`, `/my-reports`, `/profile`。

| URL 路径 | 页面组件 | 一句话说明 |
|----------|----------|------------|
| `/` | `frontend/src/pages/Home.tsx` | 首页，12 星座与今日运势入口 |
| `/fortunes` | `frontend/src/pages/FortuneHub.tsx` | 运势聚合（Tab「运势」） |
| `/quicktest` | `frontend/src/pages/QuickTest.tsx` | 免费解读 / 快测 |
| `/daily/:sign` | `frontend/src/pages/DailyFortune.tsx` | 某星座每日运势（`sign` 为英文 key） |
| `/daily/personal` | `frontend/src/pages/DailyFortune.tsx` | 个人每日运势（`personalMode`） |
| `/report/personality` | `frontend/src/pages/ReportPersonality.tsx` | 个人性格报告（流式） |
| `/report/compatibility` | `frontend/src/pages/Compatibility.tsx` | 配对合盘（流式 + 分享） |
| `/report/annual` | `frontend/src/pages/AnnualReport.tsx` | 年度运势（流式） |
| `/report/astro-event` | `frontend/src/pages/ReportAstroEvent.tsx` | 天象事件类报告（流式） |
| `/payment` | `frontend/src/pages/Payment.tsx` | 支付下单 |
| `/payment/result` | `frontend/src/pages/PaymentResult.tsx` | 支付结果 / 轮询订单 |
| `/profile` | `frontend/src/pages/Profile.tsx` | 我的资料与订单等（Tab「我的」） |
| `/chat` | `frontend/src/pages/Chat.tsx` | AI 顾问（SSE 对话） |
| `/my-reports` | `frontend/src/pages/MyReports.tsx` | 报告列表（Tab「报告」） |
| `/reports/:reportId` | `frontend/src/pages/ReportView.tsx` | 单份报告详情 |
| `/season/today` | `frontend/src/pages/SeasonToday.tsx` | 季节/今日相关运势页 |
| `/share/compat/:token` | `frontend/src/pages/ShareCompatPreview.tsx` | 配对分享落地预览 |

未知路径会重定向到 `/`（同文件内 `Navigate`）。

---

## 前端 API 层（请求发到哪里）

Axios 实例：`frontend/src/api/client.ts`，`baseURL` 为 **`/api/v1`**，开发时由 Vite 代理到后端（`frontend/vite.config.ts` → `http://127.0.0.1:8000`）。

流式报告使用 `fetch` + SSE，见 `frontend/src/api/stream.ts`（路径仍为 `/api/v1/...`）。

| 前端封装文件 | 主要用途 |
|--------------|----------|
| `frontend/src/api/constellation.ts` | 星座列表、每日运势、聚合运势等 |
| `frontend/src/api/quicktest.ts` | 免费快测 `POST /quicktest` |
| `frontend/src/api/payment.ts` | 创建支付、查订单状态 |
| `frontend/src/api/user.ts` | 登录、资料、订单列表 |
| `frontend/src/api/reports.ts` | 用户报告列表、单报告详情 |
| `frontend/src/api/growth.ts` | 增长 / 分享 / 助力 / 季卡等 |
| `frontend/src/api/season.ts` | 季节今日接口 |
| `frontend/src/api/stream.ts` | 各报告与 Chat 的 SSE `POST` |

**页面 → 常用接口（便于后端联调）**

| 页面 | 典型调用 |
|------|----------|
| Home, FortuneHub | `GET /signs`, `GET /daily/all` 等（见 `constellation.ts`） |
| QuickTest | `POST /quicktest` |
| DailyFortune | `GET /daily/{sign}`, `GET /daily/personal` |
| ReportPersonality | `POST /report/personality`, `POST /report/personality-dlc`（SSE）, `getPaymentStatus`, `fetchProfile` |
| Compatibility | `POST /report/compatibility`（SSE）, `createCompatShare`, `getPaymentStatus` |
| AnnualReport | `POST /report/annual`（SSE） |
| ReportAstroEvent | `POST /report/astro-event`（SSE） |
| Chat | `POST /chat`（SSE） |
| Payment / PaymentResult | `POST /payment/create`, `GET /payment/status/{id}` |
| Profile | `GET/PATCH /user/profile`, `GET /user/orders`, `GET /user/reports` |
| MyReports, ReportView | `GET /user/reports`, `GET /reports/{report_id}` |
| ShareCompatPreview | `GET /growth/share/compatibility/{token}` |
| SeasonToday | `GET /season/today`（经 `season.ts`，对应后端 constellation 路由） |

---

## 后端结构（接口在哪里实现）

入口：`backend/app/main.py`（注册路由、CORS、限流、健康检查 `GET /health`）。

| 模块文件 | URL 前缀 | 内容概要 |
|----------|-----------|----------|
| `backend/app/api/constellation.py` | `/api/v1` | `signs`, `daily`, `quicktest`, 各类 `report/*`（含 SSE）, `season/today`, `reports/{id}` 等 |
| `backend/app/api/chat.py` | `/api/v1` | `POST /chat`（对话流式） |
| `backend/app/api/user.py` | `/api/v1/user` | `login`, `profile`, `orders`, `reports` |
| `backend/app/api/payment.py` | `/api/v1/payment` | `create`, `notify`, `status/{order_id}` |
| `backend/app/api/growth.py` | `/api/v1/growth` | 用户增长、分享、助力、拼团等 |

模型：`backend/app/models/`。LLM 与业务服务：`backend/app/services/`（如 `llm_service.py`, `payment_service.py`, `cache_service.py`）。Prompt 片段：`backend/app/prompts/`。

---

## 共享组件与样式（改 UI 时顺带看这里）

- 全局布局与路由：`frontend/src/App.tsx`
- 底部导航：`frontend/src/components/BottomNav.tsx`
- 星空背景、加载、报告展示等：`frontend/src/components/`（如 `StarryBackground`, `LoadingAnalysis`, `MarkdownReport`, `StreamText`）
- 全局样式 / 主题变量：以 `frontend/src/` 下样式入口及 Tailwind 为准（项目使用 Tailwind 4）

设计风格摘要见 `.cursorrules`（深紫 + 金、移动端优先等）。

---

## 方案：用户怎么提需求，Cursor 才不容易跑偏

### 1. 尽量带「定位信息」（任选其一或组合）

- **路由**：例如「改 `/payment` 页的按钮文案」。
- **Tab**：例如「底部导航『运势』里第一个卡片」。
- **文件名**：例如「`ReportPersonality.tsx` 里生成完成后的提示」。
- **截图 + 圈选**：说明在屏幕上的大致区域（顶栏 / 列表 / 弹窗）。

### 2. 说明改的是「界面」还是「数据/逻辑」

| 诉求类型 | 建议说法 | Cursor 应优先打开 |
|----------|----------|-------------------|
| 布局、样式、文案 | 「只改前端展示，接口不变」 | 对应 `pages/` + `components/` |
| 接口字段、报错、慢 | 「接口返回 xxx，希望改成」 | `backend/app/api/` + 对应 `services/` |
| 报告话术、Prompt | 「AI 输出风格 / 结构」 | `backend/app/prompts/` + `llm_service.py` |
| 支付、订单 | 「下单失败 / 回调」 | `payment.py` + `payment_service.py` |

### 3. 在 Cursor 里可用的操作（推荐给用户）

- **@ 引用文件或文件夹**：例如 `@frontend/src/pages/Payment.tsx`、`@backend/app/api/payment.py`，把上下文钉死。
- **@Codebase**：问「哪里调用了 `createPayment`」这类全局问题。
- **附运行现象**：浏览器控制台报错、Network 里失败的 URL、状态码，便于判断是代理、CORS 还是后端 500。

### 4. 调试前端时可用工具（若已配置 MCP）

- **浏览器类 MCP**：本地打开 `http://localhost:5173` 做快照、点按、看请求（见 Cursor 里 browser 相关 MCP 说明）。
- **本仓库不设额外强制工具**：无浏览器 MCP 时，用 Chrome DevTools + 上述路径表即可。

---

## 本地开发（简要）

**约定：本地默认不用 Docker**，按下面方式即可（与日常开发一致）。**生产环境在服务器上用 Docker** 跑 MySQL、Redis、后端、Nginx，见下文「服务器 Docker 部署」。

`backend/.venv/` 已加入 `.gitignore`，克隆后可能没有；**勿用 macOS 自带的 Command Line Tools Python 3.9** 直接跑 `uvicorn`（会缺依赖）。请用 Homebrew 的 `python3`（3.11+）创建 venv。改 `backend/.env` 后需**重启** uvicorn 进程。更细的 Agent 约定见 [`.cursor/rules/starloom-local-runtime.mdc`](.cursor/rules/starloom-local-runtime.mdc)。

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填写百炼 / Coze / 虎皮椒等；DB/Redis 指向本机或开发机
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`，`/api` 由 Vite 代理到 `http://127.0.0.1:8000`（见 `frontend/vite.config.ts`）。

### 可选：本机用 Docker 模拟生产（非必需）

若需要本地一次性验证「静态站 + Nginx + 容器后端」：

```bash
cp backend/.env.example backend/.env
cd frontend && npm run build && cd ..
docker compose up -d --build
```

- 访问：`http://localhost:8080`，API：`http://localhost:8080/api/v1/...`
- Nginx 使用 [`deploy/nginx/http.conf.template`](deploy/nginx/http.conf.template)，`DOMAIN` 默认 `_`。

---

## 服务器 Docker 部署（生产）

在服务器上安装 **Docker Engine** 与 **Compose 插件**，将代码放到例如 `/opt/starloomv2`，用 Compose 在同一台机子的 Docker 里跑 **MySQL、Redis、后端、Nginx**（见 [`docker-compose.prod.yml`](docker-compose.prod.yml)）。

### 域名访问（先决条件）

1. 在域名 DNS 为 **`starloom.com.cn`（或你的域名）添加 **A 记录**，指向服务器**公网 IP**（生效需数分钟至数小时）。
2. 云安全组 / 防火墙放行 **TCP 80、443**。
3. 用 **HTTPS + 域名** 访问前，需在 [`backend/.env`](backend/.env.example) 中设置 `FRONTEND_URL=https://你的域名`、`CORS_ORIGINS=https://你的域名`（与浏览器地址一致）。

### 一键部署脚本（在服务器上执行）

仓库提供 [`scripts/deploy-on-server.sh`](scripts/deploy-on-server.sh)：若未配置 Let’s Encrypt 路径，会生成**临时自签证书**以便先通过 `https://域名` 访问（浏览器会提示不安全）；DNS 生效后可再申请正式证书。

```bash
cd /opt/starloomv2
cp .env.example .env && cp backend/.env.example backend/.env
# 编辑 .env：DOMAIN、DB_PASSWORD；编辑 backend/.env：生产密钥、FRONTEND_URL、CORS、DB_HOST=starloom-mysql、DB_PORT=3306 等
bash scripts/deploy-on-server.sh
```

### 微信 / 浏览器显示「证书不安全」或无法访问（必做）

自签证书或无效证书会导致 **微信内置浏览器、Safari、Chrome** 拦截，用户不敢点「继续」。应使用 **Let’s Encrypt 等受信任证书**。

**若域名解析在阿里云（万网）**：优先使用 **DNS-01**（不依赖公网访问 `/.well-known`）：

1. 在阿里云 RAM 创建子用户，授权 **AliyunDNSFullAccess**（或等价 DNS 写权限），创建 **AccessKey**。
2. 在服务器（已安装 [`acme.sh`](https://github.com/acmesh-official/acme.sh) 时）执行：

```bash
cd /opt/starloomv2
export Ali_Key='你的 AccessKeyId'
export Ali_Secret='你的 AccessKeySecret'
export DOMAIN=starloom.com.cn
bash scripts/letsencrypt-aliyun-dns.sh
```

脚本会把证书写入 [`deploy/ssl/`](deploy/ssl/) 并尝试 `nginx -s reload`。根目录 `.env` **不要**再写指向自签的 `SSL_FULLCHAIN_HOST`（留空则用默认 `deploy/ssl/*.pem`）。

**若公网能直接打到本机 Nginx（无 CDN/WAF 挡 `/.well-known`）**：可改用 HTTP-01：安装 `certbot` 后执行 [`scripts/issue-letsencrypt-webroot.sh`](scripts/issue-letsencrypt-webroot.sh)，并把 `.env` 中证书路径改为 `/etc/letsencrypt/live/域名/...`。

**说明**：若公网访问 `http://域名/.well-known/acme-challenge/` 返回 **403** 且响应头不是 `Server: nginx`，多为阿里云 **边缘/WAF（如响应头带 Beaver）** 拦截，HTTP-01 会失败，**必须用 DNS-01**（上文的 `letsencrypt-aliyun-dns.sh`）。

Nginx 已在 [`deploy/nginx/https.conf.template`](deploy/nginx/https.conf.template) 为 **`/.well-known/acme-challenge/`** 预留路径，与 [`deploy/letsencrypt-webroot`](deploy/letsencrypt-webroot) 配合供 HTTP-01 使用。

### 从本机同步代码到服务器（可选）

需已配置 **SSH 公钥**（无法用密码自动化）。在开发机执行：

```bash
export DEPLOY_HOST=root@你的服务器IP
bash scripts/rsync-to-server.sh
```

登录服务器后在 `/opt/starloomv2` 创建并编辑 `.env`、`backend/.env`，再执行 `bash scripts/deploy-on-server.sh`。

### 1. 手动步骤（与脚本等价）

1. 安装 Docker / Compose（脚本 [`scripts/deploy-on-server.sh`](scripts/deploy-on-server.sh) 在无 Docker 时会尝试调用官方 `get.docker.com` 安装脚本；亦可自行按发行版安装）。
2. `cp backend/.env.example backend/.env`，生产项：`APP_ENV=production`、`DEMO_MODE=false`、`FRONTEND_URL`、`CORS_ORIGINS`、`XUNHUPAY_NOTIFY_URL`、密钥等；**Docker 内** `DB_HOST=starloom-mysql`、`DB_PORT=3306`、`REDIS_HOST=starloom-redis`、`REDIS_PORT=6379`（与 [`backend/.env.example`](backend/.env.example) 一致）。
3. `cp .env.example .env`：设置 `DB_PASSWORD`（与 `backend/.env` 里 `DB_PASSWORD` 一致）、`DOMAIN`；证书可先使用脚本生成的 [`deploy/ssl/`](deploy/ssl/)，或配置 `SSL_FULLCHAIN_HOST` / `SSL_PRIVKEY_HOST` 指向 Let’s Encrypt 路径。
4. `cd frontend && npm ci && npm run build`，再 `docker compose -f docker-compose.prod.yml up -d --build`（与一键脚本相同）。
5. 生产 compose 中 MySQL/Redis 仅 `127.0.0.1`，后端不暴露宿主机端口，经 Nginx 对外。

### 2. 表结构与数据迁移到生产 MySQL

- 后端首次连接空库时会用 SQLAlchemy **`create_all` 建表**（见 `backend/app/database.py`）。若你从**空库**上线，可先启动一次 `starloom-backend` 再检查表是否齐全。
- **从现有库迁到服务器 Docker 里的 MySQL**（库名默认 `starloom`）典型做法：
  1. 在源环境导出：  
     `mysqldump -u root -p --databases starloom --single-transaction > starloom_backup.sql`
  2. 将 `starloom_backup.sql` 传到服务器，确保生产 compose 已启动且 MySQL 健康。
  3. 导入到容器内 MySQL（示例：映射端口为 `127.0.0.1:3307`，密码与 `.env` 中 `DB_PASSWORD` 一致）：  
     `mysql -h 127.0.0.1 -P 3307 -u root -p starloom < starloom_backup.sql`  
     或使用：`docker exec -i starloom-mysql mysql -uroot -p"$DB_PASSWORD" starloom < starloom_backup.sql`
- **注意**：若目标库已有数据，导入前请确认是否覆盖/合并；`mysqldump` 与导入时字符集建议统一为 `utf8mb4`。
- **Redis**：多为缓存与会话，一般**无需**从开发机迁数据；上线后冷启动即可，或按需单独做 RDB/AOF 迁移（非默认流程）。

---

## 百炼 / 演示模式

- `LLM_PLATFORM=bailian` 时使用百炼应用；系统提示词多在控制台配置，后端 `app/prompts/` 拼接用户参数。
- 开发联调：`DEMO_MODE=true` 可跳过部分支付校验；**上线前务必 `DEMO_MODE=false`**。

---

## 定时任务示例

```bash
cd backend && source .venv/bin/activate
PYTHONPATH=. python ../scripts/generate_daily.py
```

---

## 合规

面向用户文案使用「性格分析」「运势参考」，避免「算命」「占卜」等表述。
