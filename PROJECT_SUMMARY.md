# StarLoom v2 项目摘要

> 本文件是所有 AI 模型了解项目的**唯一入口**。任何代码改动后必须同步更新本文件。
> 最后更新: 2026-04-13

**多角色协作母版**（gstack 方法论适配）：`~/Desktop/StarLoom-Team-Collaboration-System.md`；Cursor 内见 `.cursor/rules/multi-role-review.mdc`、`opus-delegation.mdc`、`design-review.mdc`。变更日志需包含 **盈利影响** 列。

## 项目概述

基于 AI 的星座性格分析与运势 H5 产品，FastAPI 后端 + React 移动端前端，对接百炼/Coze LLM 与虎皮椒聚合支付，面向抖音引流场景。

## 技术栈

- **后端**: Python 3.11+、FastAPI、SQLAlchemy 2（async + aiomysql）、Redis、APScheduler、JWT
- **前端**: React 19、TypeScript、Vite、Tailwind CSS 4、React Router 7、Zustand（persist）、TanStack Query、Axios、Framer Motion
- **运维/内容**: `backend/ops/` 流水线（RSS/社媒数据源、文案合规、万相媒体、导出等，可选环境变量驱动）

## 目录结构

```
starloomv2/
├── docs/                    # 产品与技术设计、Prompt 文档（spec、architecture、prompts/*.md）
├── PROJECT_SUMMARY.md       # 本摘要（AI/人类项目入口）
├── README.md                # 仓库说明
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口：路由挂载、CORS、限流、生命周期内调度器
│   │   ├── config.py        # pydantic-settings 环境配置
│   │   ├── database.py      # 异步引擎与会话
│   │   ├── deps.py          # 依赖注入（当前用户等）
│   │   ├── scheduler.py     # 定时任务注册与执行
│   │   ├── api/             # HTTP 路由模块
│   │   ├── models/          # ORM 模型
│   │   ├── services/        # 业务与外部服务封装
│   │   ├── prompts/         # LLM 用户侧输入拼装模板
│   │   ├── middleware/      # 如全局限流
│   │   ├── auth/            # JWT 签发校验
│   │   └── utils/           # 流式 SSE、星座计算、时区等
│   ├── ops/                 # 运营 CLI/流水线（与主 API 进程独立）
│   ├── requirements.txt
│   └── .env.example         # 环境变量模板
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # 路由与 Shell（懒加载页面、底栏、自动 device 登录）
│   │   ├── api/             # Axios 与 SSE 封装
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 共用 UI
│   │   ├── stores/          # Zustand
│   │   ├── hooks/           # 如价格、hydration
│   │   └── utils/           # 分析、UTM、资源路径等
│   ├── public/              # 静态资源（星座图、插画）
│   └── vite.config.ts       # 开发代理 /api → 后端
└── scripts/                 # 种子数据、迁移辅助、文案工具等
```

## 后端架构

### API 路由 (backend/app/api/)

| 文件 | 接口（前缀均为文档路径，实际挂载见下） | 说明 |
|------|----------------------------------------|------|
| `constellation.py` | `GET .../reports/{report_id}` 含 **content_ir**；signs、quicktest 等 | 星座元数据、免费快测、报告详情 |
| `daily.py` | `GET /api/v1/daily/all`、`GET /api/v1/daily/personal`、`GET /api/v1/daily/{sign}` | 每日运势（含个人/全量） |
| `reports.py` | `POST /api/v1/report/personality|compatibility|annual|personality-dlc|astro-event` | 付费报告 SSE 流式生成并落库 |
| `season.py` | `GET /api/v1/season/today` | 当季/今日相关运势聚合接口 |
| `content.py` | `GET /api/v1/articles`（`carousel=1` 仅 `tags=carousel`；优先今日 → 昨日 → 更早窗口；无今日时 BackgroundTasks 触发当日轮播生成）；轮播 brief 含 `subtitle`/`reading_minutes`；`GET /api/v1/articles/{slug}` 含 **body_ir**（**published + archived** 可读）、`GET /api/v1/tips/today`、分享链接… | H5 文章与每日 tips |
| `guide.py` | `GET .../guide/{category}`：无今日行则用**昨日**行（`content_row_date`）；皆无则占位 **200**；缺今日时 BackgroundTasks 触发当日深析生成。`/preview` 按类回退昨日；`source_guide_date`；`/access` 同前 | 每日星运深析 |
| `growth.py` | `/api/v1/growth/me`、`/cards`、`/group-buy`、`/assist/*`、`/share/compatibility` | 增长：积分、季卡、拼团、助力、配对分享 |
| `payment.py` | `POST /api/v1/payment/create`、`POST .../notify`、`GET .../prices|pending`、`POST .../sync/{order_id}`、`GET .../status/{order_id}` | 虎皮椒下单、回调、询价与状态 |
| `user.py` | `POST /api/v1/user/login`、`GET|PATCH /api/v1/user/profile`、`GET .../orders`、`GET .../reports` | 设备登录、资料、订单与报告列表 |
| `chat.py` | `GET /api/v1/chat/status`、`POST /api/v1/chat` | AI 顾问（SSE） |
| `_report_helpers.py` | （被 reports/constellation 引用，无独立路由） | 报告保存、订单校验、星盘合并、画像异步更新 |
| `schemas.py` | （Pydantic 模型） | 请求体验证 |

### 数据模型 (backend/app/models/)

| 模型 | 关键字段 | 表名 |
|------|----------|------|
| `User` | device_id、出生/地点/时区、sun_sign、gender、ai_profile | `users` |
| `Order` | order_id、product_type、amount、status、pay_method、extra_data | `orders` |
| `Report` | report_id、report_type、sign、input_data、content、content_ir(JSON 可选) | `reports` |
| `DailyFortune` | sign、fortune_date、content(JSON) | `daily_fortunes` |
| `DailyGuide` | sign、category、guide_date、title、preview、content、**content_ir**（JSON 可选） | `daily_guides` |
| `Article` / `DailyTip` | slug、body、**body_ir**（JSON 可选）、cover、category、status；tip 按 category/sign/date | `articles` / `daily_tips` |
| `UserGrowthProfile` | referral_code、credit_yuan、season_pass_until | `user_growth_profiles` |
| `UserZodiacCard` | user_id、sign、source | `user_zodiac_cards` |
| `GroupBuy` / `GroupBuyMember` | public_id、leader、product_type、状态与成员 | `group_buys` / `group_buy_members` |
| `AssistTask` / `AssistRecord` | task_id、助力进度与记录 | `assist_tasks` / `assist_records` |
| `CompatibilityShareToken` | token、payload、expires_at | `compatibility_share_tokens` |

### 服务层 (backend/app/services/)

| 服务 | 职责 | 主要依赖 |
|------|------|----------|
| `llm_service.py` | Coze/百炼工厂、按场景选应用、流式与降级 | `config`、HTTP/SDK |
| `report_planner.py` | 两阶段报告（规划 + 写作）编排 | `llm_service` |
| `profile_extractor.py` | 从报告内容抽取并合并用户 `ai_profile` | LLM（profile_extractor 应用） |
| `payment_service.py` | 虎皮椒创建订单、验签、查询 | `config`、HTTP |
| `cache_service.py` | Redis 访问封装 | Redis |
| `astro_service.py` / `astro_models.py` | 本命盘、合盘、年运摘要等计算 | 天文/时间库 |
| `daily_fortune_core.py` / `public_daily_fortune.py` | 每日运势生成与批量预取 | LLM、DB、Redis |
| `guide_generator.py` | 按日生成各星座 `DailyGuide` | LLM、DB |
| `article_scraper.py` | 按北京日生成首页轮播：NewsNow 风格 API + RSS 回退 → 抓取 `og:image`/摘要 → 百炼改写入库（`articles.tags=carousel`） | httpx、百炼 `chat/completions`、DB |
| `chat_context_service.py` | 聊天上下文装配 | DB/缓存 |
| `growth_helpers.py` | 支付后奖励、季卡、卡片等副作用 | 各 growth 模型 |

### Prompts (backend/app/prompts/)

| 文件 | 用途 |
|------|------|
| `daily_fortune.py` | 每日运势用户输入 |
| `personality.py` / `personality_dlc.py` | 性格报告与 DLC（career/love/growth） |
| `compatibility.py` / `annual.py` | 配对、年度运势 |
| `astro_event.py` | 天象事件主题报告 |
| `chart_formatter.py` | 星盘文本格式化给规划器 |
| `report_plan_prompt.py` | 报告规划阶段输入 |
| `guide_career.py` 等四个 `guide_*.py` | 每日深析四类文案模板 |

### 定时任务 (backend/app/scheduler.py)

- **`daily_prefetch_beijing`**（可关 `DAILY_PREFETCH_ENABLED`）：北京时间 cron 触发，预生成当日 12 星座公开运势写入 DB/缓存。
- **`carousel_articles_beijing`**（可关 `CAROUSEL_GENERATION_ENABLED`）：默认 0:20 北京时间，写入当日 `tags=carousel` 轮播短文（与深析四分类独立）。
- **`guide_generation_beijing`**（可关 `guide_generation_enabled`）：北京时间 cron 触发，生成当日 `DailyGuide`。
- **`h5_article_generation_beijing`**：与 guide 同日起算，晚 5 分钟触发，调用 `ops.pipeline.run_h5_content` 生成/发布 H5 文章类内容。

## 前端架构

### 页面 (frontend/src/pages/)

| 文件 | 路由 | 用途 | 付费/免费 |
|------|------|------|-----------|
| `Home.tsx` | `/` | 首页入口 | 免费为主 |
| `FortuneHub.tsx` | `/fortunes` | 运势聚合/导航 | 免费 |
| `QuickTest.tsx` | `/quicktest` | 免费快测 | 免费 |
| `DailyFortune.tsx` | `/daily/:sign`、`/daily/personal` | 每日运势 | 免费 |
| `ReportPersonality.tsx` | `/report/personality` | 性格报告流式 | 付费 |
| `Compatibility.tsx` | `/report/compatibility` | 配对报告流式 | 付费 |
| `AnnualReport.tsx` | `/report/annual` | 年运流式 | 付费 |
| `ReportAstroEvent.tsx` | `/report/astro-event` | 天象事件报告 | 付费 |
| `Payment.tsx` | `/payment` | 下单支付 | — |
| `PaymentResult.tsx` | `/payment/result` | 支付结果 | — |
| `Profile.tsx` | `/profile` | 用户资料 | — |
| `Chat.tsx` | `/chat` | AI 顾问 | 付费能力 |
| `MyReports.tsx` | `/my-reports` | 报告列表 | — |
| `ReportView.tsx` | `/reports/:reportId` | 报告详情 | — |
| `SeasonToday.tsx` | `/season/today` | 季运/今日 | 视产品配置 |
| `ShareCompatPreview.tsx` | `/share/compat/:token` | 配对分享预览 | 增长 |
| `Article.tsx` | `/articles/:slug` | 文章阅读 | 内容 |
| `Guide.tsx` | `/guide/:category` | 每日深析 | 预览免费全文付费 |

### 组件 (frontend/src/components/)

| 文件 | 用途 |
|------|------|
| `BottomNav.tsx` | 底部导航 |
| `LoadingAnalysis.tsx` | 全页加载占位 |
| `StarryBackground.tsx` | 星空背景 |
| `ZodiacCard.tsx` | 星座卡片 |
| `MarkdownReport.tsx` | 报告 Markdown 渲染 |
| `StreamText.tsx` / `ReportStreamingLoader.tsx` / `ReportGeneratingShell.tsx` | 流式与生成中 UI |
| `ReportExportActions.tsx` / `ReportCertificateHeader.tsx` / `ReportCrossSell.tsx` | 导出、证书头、交叉销售 |
| `PayButton.tsx` | 支付触发 |
| `Toast.tsx` | 全局轻提示 |
| `Skeleton.tsx` | 骨架屏 |
| `ScoreRing.tsx` / `RadarChart.tsx` / `BirthChartWheel.tsx` | 分数环、雷达、星盘轮 |
| `FortuneArticleCarousel.tsx` / `PracticalGuideSection.tsx` | 首页文章轮播（`carousel=1` + 来源角标；封面实底 + `onError` 回退）、实用指南区块 |
| `BlurLock.tsx` | 模糊锁内容 |
| `GameDecor.tsx` / `AnimatedUserCount.tsx` | 装饰与动效 |
| `icons/Icon.tsx` | 图标集合 |

### API 层 (frontend/src/api/)

| 文件 | 主要请求 |
|------|----------|
| `client.ts` | Axios 实例与基路径 |
| `constellation.ts` | signs、daily、quicktest、React Query hooks |
| `payment.ts` | create、pending、prices、status |
| `user.ts` | login、profile、patch、orders |
| `reports.ts` | user/reports 列表、report 详情 |
| `stream.ts` | `postSseStream` 消费 SSE |
| `growth.ts` | me/cards、拼团、助力、分享 |
| `content.ts` | articles、tips 与 hooks |
| `guide.ts` | guide preview/full/access |
| `season.ts` | season today |
| `quicktest.ts` | quicktest POST |

### 状态管理

- **`userStore`**（persist）：`token`、`deviceId`、`setToken`、`ensureDevice`。
- **`birthProfileStore`**（persist）：出生日期时间、地点经纬与时区、性别；`applyFromProfile` / `applyFromExtras` 与服务端/订单扩展字段合并。

## 业务流程摘要

### 用户核心路径

抖音/外链进入 H5 → Shell 用 `device_id` 调 `POST /user/login` 换 JWT → 首页或运势 hub → 免费 `GET /daily/*` 或快测 → 选择付费报告 → `GET /payment/prices` + `POST /payment/create` 跳转虎皮椒 → 支付成功回 `FRONTEND_URL` 结果页并轮询 `GET /payment/status/{order_id}` → 携带 `order_id` 打开报告页，`postSseStream` 调对应 `POST /report/*` → 完成后 `GET /user/reports` / `GET /reports/{id}` 回看。

### 支付流程

前端提交商品类型与金额（须与后端 `PRODUCT_PRICES` 一致，拼团带 `extra_data`）→ `payment/create` 写 `orders` 并请求虎皮椒 → 返回支付链接/H5 → 用户支付 → 虎皮椒 `POST /api/v1/payment/notify` → 验签、幂等更新订单 `paid`、触发增长奖励 → 前端轮询 `status` 或 `pending` 对齐状态。

### SSE 流式报告生成流程

前端 `fetch` POST + `Authorization`，`Content-Type: application/json`，响应 `text/event-stream` → 后端校验已支付订单、拼 prompt，经 `LLMService`/`two_stage_report` 或 `stream_with_fallback` 产出 chunk → `sse_line` 封装事件（含 `content`、`done` 与 `report_id`）→ 前端 `ReadableStream` 解析追加正文 → 可选落库后跳转报告详情。

## 数据库表结构摘要

| 表 | 用途摘要 |
|----|----------|
| `users` | 设备用户与出生档案、AI 画像 JSON |
| `orders` | 订单与支付状态、扩展字段（如 guide_date、拼团 id） |
| `reports` | 生成报告全文与输入快照 |
| `daily_fortunes` | 按日按星座缓存的公开运势 JSON |
| `daily_guides` | 按日按星座按类别的深析正文 |
| `articles` | 运营文章；首页轮播日更由 `article_scraper` 写入 `tags=carousel` |
| `daily_tips` | 每日短 tip |
| `user_growth_profiles` | 邀请码、余额、季卡截止时间 |
| `user_zodiac_cards` | 用户收集的星座卡 |
| `group_buys` / `group_buy_members` | 拼团 |
| `assist_tasks` / `assist_records` | 助力任务 |
| `compatibility_share_tokens` | 配对分享令牌 |

## 配置与环境变量

- **数据库**: `DB_HOST`、`DB_PORT`、`DB_NAME`、`DB_USER`、`DB_PASSWORD` → `Settings.database_url`（aiomysql）。
- **Redis**: `REDIS_HOST`、`REDIS_PORT`、`REDIS_DB`。
- **每日预取**: `DAILY_PREFETCH_ENABLED`、`DAILY_PREFETCH_HOUR_BEIJING`、`DAILY_PREFETCH_MINUTE_BEIJING`。
- **LLM**: `LLM_PLATFORM`；Coze：`COZE_*`；百炼：`BAILIAN_API_KEY`、分场景 `BAILIAN_APP_ID_*`（daily/personality/compatibility/annual/chat/planner/profile_extractor）。
- **支付**: `XUNHUPAY_APPID_*`、`XUNHUPAY_APPSECRET_*`、`XUNHUPAY_NOTIFY_URL`、`XUNHUPAY_API_BASE`。
- **应用**: `APP_ENV`、`APP_SECRET_KEY`、`FRONTEND_URL`、`JWT_EXPIRE_DAYS`、`CORS_ORIGINS`。
- **首页文章轮播**: `ARTICLE_CAROUSEL_FALLBACK_DAYS`（默认 7）：`GET /articles?carousel=1` 在无北京当日发文时回退最近 N 个自然日。
- **轮播日更短文（主进程）**: `CAROUSEL_GENERATION_ENABLED`、`CAROUSEL_MAX_ARTICLES`、`CAROUSEL_GENERATION_HOUR_BEIJING`、`CAROUSEL_GENERATION_MINUTE_BEIJING`；可选 `NEWSNOW_API_BASE`、`CAROUSEL_NEWSNOW_SOURCE_IDS`（逗号）、`CAROUSEL_RSS_FALLBACK_URLS`（逗号，默认含 36氪/爱范儿）、`CAROUSEL_PAGE_FETCH_MAX_BYTES` — 定时拉热点 → 抓页面 meta → 百炼改写写入 `articles`（`tags=carousel`）；NewsNow 若被 CDN 拦截可依赖 RSS；一次性执行：`scripts/run_carousel_articles.py`（`--force` 覆盖当日）。
- **深析与 ops**: `guide_generation_*`、`guide_llm_model`；`backend/.env.example` 中 `OPS_*` 为运营流水线可选项；`OPS_H5_MAX_ARTICLES_PER_DAY`（默认 5）与首页轮播容量对齐；H5 文章在 `OPS_WAN_IMAGE_ENABLED` 且具备 DashScope 密钥时为每篇生成封面并写入 `frontend/public/generated/articles/{date}/`（失败则降级静态分类图并打日志）。

## 当前开发状态

### 已完成功能

- 12 星座元数据、每日运势（含定时预取）、多类付费报告 SSE、聊天 SSE、虎皮椒支付闭环、用户资料与报告列表、增长玩法（拼团/助力/分享）、内容/指南 API 与对应前端路由。

### 进行中功能

- 工作区存在大量未提交变更（`git status`）：ops 流水线扩展、content/guide/reports/chat/支付前后端迭代、文档与静态资源等，需合并与回归测试后更新本摘要。

### 已知问题

- 未配置 `XUNHUPAY_NOTIFY_URL` 或渠道密钥时，启动日志会警告且创建支付可能返回 503（见 `main.py`）。
- 本地 `uvicorn --reload` 可能与 APScheduler 重复执行，开发可按 `.env.example` 关闭预取/深析定时任务。

### 首页文章轮播「日更」QA 证据清单（发版 / 每日 ops 后）

1. **HTTP**：`GET /api/v1/articles?carousel=1&limit=8` — 记录 `carousel_source`（`today` / `fallback` / `empty`）、各条 `slug`、`publish_date`、`cover_image`；非 `empty` 时断言 `publish_date` 符合当日或回退窗口策略。
2. **静态资源**：对每条 `cover_image` 做 `HEAD` 或浏览器网络面板，期望 200 且为图片类型；大量 404 视为失败。
3. **DB（可选）**：`articles` 表中当日 `publish_date`、状态 `published` 与接口一致；种子 slug 应为 `draft`/`archived`，不参与轮播。
4. **浏览器**：本地 `http://localhost:5173` 首页截图首张轮播标题 + 封面；与昨日留存或昨日 slug 对比，至少一项不同，或界面明确为「近期精选」/「暂无今日更新」。
5. **控制台**：无未处理异常；关键接口无 5xx。

## 变更日志（最近 10 条）

| 日期 | 改动 | 涉及文件（节选） | 盈利影响 |
|------|------|------------------|----------|
| 2026-04-13 | **图片全量转 WebP**：`scripts/optimize-images.sh` 批量转换（113MB→10MB, -91%）；前端所有静态图路径从 `.png` 改为 `.webp` | `frontend/src/utils/reportSectionImages.ts`、`frontend/src/constants/reportStreamVisual.ts`、`frontend/src/data/zodiacArticles.ts`、`frontend/src/pages/*`（ReportAstroEvent、SeasonToday、FortuneHub、ShareCompatPreview、Compatibility、Chat、Profile、DailyFortune、QuickTest、ReportPersonality、AnnualReport、Payment）、`frontend/src/components/*`（BlurLock、ReportGeneratingShell、PayButton、FortuneArticleCarousel、PracticalGuideSection、ReportStreamingLoader）、`scripts/optimize-images.sh`、`PROJECT_SUMMARY.md` | 首屏图片加载从 30+ 秒降到 2-3 秒，抖音引流落地页体验大幅改善，减少首屏流失 |
| 2026-04-13 | **生产定价**：性格 / 配对 / 年运 `_PRODUCTION_PRICES` 改为 ¥0.10 / ¥0.20 / ¥0.30，与本地测试档一致 | `backend/app/api/payment.py`、`PROJECT_SUMMARY.md` | 正式环境客单价大幅下降；适合内测/验证支付链路，上线前需再评估 |
| 2026-04-12 | **轮播与深析无今日数据**：轮播 API 仅 `tags=carousel`，顺序 今日→昨日→窗口；无今日时后台触发 `generate_carousel_articles`（冷却）。深析 preview/full 无今日用昨日行，并触发 `generate_all_guides_for_date`（冷却）；响应含 `source_guide_date`/`content_row_date`；首页轮播角标 `yesterday`；Guide 页昨日提示 | `backend/app/api/content.py`、`guide.py`、`services/daily_generation_kick.py`、`frontend/.../FortuneArticleCarousel.tsx`、`Guide.tsx`、`api/content.ts`、`api/guide.ts`、`PROJECT_SUMMARY.md` | 无今日仍可看昨日，减少空窗；后台补拉今日提升转化与留存 |
| 2026-04-12 | **每日星运深析支付拉不起**：根因是 `GET /guide/{category}` 在库中无当日记录时返回 **404**，前端 `Guide` 页无 `fullData` 只报错，不渲染「立即解锁」。现改为无记录时返回 **200** + 占位文案，与 `/preview` 一致 | `backend/app/api/guide.py`、`PROJECT_SUMMARY.md` | 无深析数据时仍可进入付费墙，减少流失 |
| 2026-04-12 | **发布流程规则**：代码必须本地改并提交仓库；生产仅从仓库拉取后再构建发布；禁止服务器直接改业务代码；新增 `.cursor/rules/deployment-workflow.mdc`，`.cursorrules` 与 `DEPLOY.md` 对齐；`.gitignore` 改为仅跟踪 `.cursor/rules/*.mdc` 以便规则入库 | `.cursor/rules/deployment-workflow.mdc`、`.cursorrules`、`DEPLOY.md`、`.gitignore`、`PROJECT_SUMMARY.md` | 无直接营收；可追溯、可回滚，降低线上漂移与误覆盖风险 |
| 2026-04-11 | **Content IR v1**：Markdown→结构化 JSON（`markdown_to_ir`）；`articles.body_ir`、`daily_guides.content_ir`、`reports.content_ir`（需执行 `scripts/migrations/add_content_ir_columns.sql`）；轮播 brief 带 `reading_minutes`/`subtitle`；API 返回 IR；前端 `IRRenderer` + 文章/深析/报告视图优先 IR；`scripts/backfill_content_ir.py` 回填旧数据 | `backend/app/services/ir_converter.py`、`backend/app/content_ir_types.py`、`backend/app/models/*`、`backend/app/api/content.py`、`guide.py`、`constellation.py`、`article_scraper.py`、`guide_generator.py`、`_report_helpers.py`、`frontend/src/types/contentIr.ts`、`frontend/src/components/IRRenderer.tsx`、`MarkdownReport.tsx`、`Article.tsx`、`Guide.tsx`、`ReportView.tsx`、`FortuneArticleCarousel.tsx`、`scripts/migrations/add_content_ir_columns.sql`、`scripts/backfill_content_ir.py`、`PROJECT_SUMMARY.md` | 长文可读性与组件化展示提升转化与停留；老数据需迁移+回填 |
| 2026-04-11 | 支付 500：订单 `flush` 捕获 `SQLAlchemyError` 返回 503+中文说明；`ProductType` 非法 400；商品名 `name_map.get` 兜底；Axios 对 5xx/无 detail 统一中文提示 | `backend/app/api/payment.py`、`frontend/src/api/client.ts`、`PROJECT_SUMMARY.md` | 降低支付页「status code 500」客诉与困惑 |
| 2026-04-11 | 429 限流：后端各路径限流改为 `config` 可配（默认支付创建 12/60s，原 5）；响应 `Retry-After`；前端 Axios 将 429 译为中文提示 | `backend/app/config.py`、`backend/app/middleware/rate_limit.py`、`backend/.env.example`、`frontend/src/api/client.ts`、`PROJECT_SUMMARY.md` | 减少测试/重试误伤；提示可理解 |
| 2026-04-11 | 首页精选轮播：封面仅从**源页**提取（og/twitter/正文区 `<img>` 等），同批轮播内 URL 撞车时换用同页候选图，**不再用本地插图顶替**；摘录加长供 LLM；改写 prompt 要求 **1200–2200 字**、多小节，`MIN_BODY_CHARS` 提升；支付：`daily_guide` 询价与金额量化比较见上行 | `backend/app/services/article_scraper.py`、`backend/app/api/payment.py`、`frontend/src/components/FortuneArticleCarousel.tsx`、`frontend/src/pages/Payment.tsx`、`frontend/src/hooks/usePrices.ts`、`PROJECT_SUMMARY.md` | 读感与配图可信度提升；支付失败率下降 |
| 2026-04-11 | 首页轮播：`article_scraper` 聚合 NewsNow API + RSS 回退 → 抓取摘要/`og:image` → 百炼改写（`tags=carousel`）；删除纯天象 `carousel_generator`；`GET /guide/{category}` 改可选登录避免未登录 401 | `backend/app/services/article_scraper.py`、`backend/app/config.py`、`backend/app/scheduler.py`、`backend/app/api/guide.py`、`scripts/run_carousel_articles.py`、`PROJECT_SUMMARY.md` | 热点锚点+独立封面提升点击与信任；深析详情未登录可预览降低跳出 |
| 2026-04-11 | 文章详情/分享：`GET /articles/{slug}` 与 `.../share` 允许 **archived**（仍不出现在列表与 `carousel=1`），避免种子归档后兜底轮播点进详情 404；归档脚本结束时 `dispose` 引擎消除 asyncio 告警 | `backend/app/api/content.py`、`scripts/archive_seed_carousel_articles.py`、`PROJECT_SUMMARY.md` | 空窗期静态预览可继续转化详情阅读，减少死链挫败 |
| 2026-04-11 | 首页轮播与日更链路：API `carousel=1`+`carousel_source`；ops 默认北京日、`OPS_H5_MAX_ARTICLES_PER_DAY`、万相按篇封面落盘；种子改 draft、归档脚本；轮播封面实底与 onError；QA 清单写入摘要 | `backend/app/api/content.py`、`backend/app/config.py`、`backend/ops/pipeline.py`、`backend/ops/config.py`、`backend/ops/h5_content/article_generator.py`、`backend/ops/media/wan_media.py`、`scripts/seed_articles.py`、`scripts/archive_seed_carousel_articles.py`、`frontend/src/api/content.ts`、`frontend/src/components/FortuneArticleCarousel.tsx`、`frontend/.gitignore`、`frontend/public/generated/articles/.gitkeep`、`backend/.env.example`、`PROJECT_SUMMARY.md` | 日更轮播与当日感知增强，利于回访与停留；万相成本随篇数上升，可用 `OPS_WAN_IMAGE_ENABLED` 与条数配置控制 |
| 2026-04-11 | 建立多角色团队协作规则：桌面母版、multi-role 精简规则、Opus 角色映射与监控含盈利列、设计 0-10 评分章 | `~/Desktop/StarLoom-Team-Collaboration-System.md`、`.cursor/rules/multi-role-review.mdc`、`.cursor/rules/opus-delegation.mdc`、`.cursor/rules/design-review.mdc`、`PROJECT_SUMMARY.md` | 无直接营收；降低协作与返工成本，强化转化/测试门禁 |
| 2026-04-06 | 支付 H5 兜底、pending 查询、Docker pip 超时 | `backend/Dockerfile`、`payment.py`、`Payment.tsx`、`api/payment.ts` | — |
| 2026-04-05 | 年运/配对 prompt 与报告 UI、支付与流式体验 | `.cursorrules`、`README`、`backend` API/service、`docs/prompts/*`、`frontend` | — |
| 2026-04-04 | daily、growth、支付与聊天流程、部署相关 | `backend/app`、`frontend`、Docker、配置 | — |
| 2026-03-31 | 可选 GitHub 推送脚本 | `scripts/push-to-github.sh` | — |
| 2026-03-31 | 项目初始化：H5 + FastAPI | 后端骨架、auth、API、配置、README | — |

（Git 目前仅上表 5 条；其余迭代在工作区未提交，见 `git status`，commit 后应追加至本表至满 10 条。）
