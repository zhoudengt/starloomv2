# StarLoom 运营内容流水线（`backend/ops`）

独立 Python 包：**不挂载**主 FastAPI，**不改变**现网路由。每日生成 `out/YYYY-MM-DD/` 下文案、JSON/Markdown，并可选用 **阿里云 DashScope 万相** 生成**文生图**（默认）与可选**文生视频**（较贵，默认关闭）。

## 运行方式

在 **`backend` 目录**下执行（需已配置主项目 `.env` 中的 Redis 等，以便读取 12 星座日运缓存）：

```bash
cd backend
../.venv/bin/python -m ops.cli preview
../.venv/bin/python -m ops.cli daily
../.venv/bin/python -m ops.cli daily --date 2026-04-06
# 仅文案与 JSON，不调用万相（不产生费用）
../.venv/bin/python -m ops.cli daily --no-media
# 本次额外强制生成文生视频（覆盖 OPS_WAN_VIDEO_ENABLED=false）
../.venv/bin/python -m ops.cli daily --with-video
```

若本日 Redis 尚无日运，仍会生成占位选题（并标注 `_placeholder` 数据源）。

## 万相媒体（非智能体调用）

使用与项目一致的 **`BAILIAN_API_KEY`**（DashScope），通过 `ImageSynthesis` / `VideoSynthesis` 调用模型，**不是** `Application.call` 智能体 AppId。

| 能力 | 默认 | 环境变量 |
|------|------|----------|
| 文生图（carousel 每页 `image_prompt`） | 开 | `OPS_WAN_IMAGE_ENABLED`（默认 true） |
| 文生视频（单条 clip） | **关**（省成本） | `OPS_WAN_VIDEO_ENABLED`（默认 false） |

生成文件目录：`out/<date>/media/images/page_XX.png`，视频 `media/videos/clip.mp4`。结果摘要写在 `manifest.json` 的 `wan_media` 字段。

推荐模型：`OPS_WAN_IMAGE_MODEL=wan2.6-t2i`（走 **`multimodal-generation/generation`** HTTP，与旧版 `ImageSynthesis` 路径不同），`OPS_WAN_VIDEO_MODEL=wan2.6-t2v`。多张图之间默认间隔 `OPS_WAN_IMAGE_SLEEP_SEC=4` 以降低 429。

## 抖音一体化发布包（引流 + 合规）

同一次 `daily` 会在 `out/<date>/` 额外生成（**不挂载主 API**）：

| 文件 | 说明 |
|------|------|
| `douyin_publish.md` | 标题备选、四段正文（含 spec 定价桥接）、配图/轮播表、置顶块 |
| `pinned_comment.txt` | **生产 H5 + UTM** 完整链接（与二维码同源） |
| `hotspot_report.json` | 今日热点 `none` / `weak` / `matched` 与摘要 |
| `douyin_compliance.txt` | 平台规则与内容定位提示（非法律意见） |
| `media/traffic_qr.png` | 可选：二维码编码上述完整 URL（需 `qrcode[pil]`） |

`manifest.json` 会合并 `hotspot_report` 与 `douyin_kit` 字段。**发布抖音前**请将 **`FRONTEND_URL` / `OPS_FRONTEND_BASE_URL`** 设为真实线上 H5 域名（勿长期用 localhost）；二维码与置顶链接会一致。

## 环境变量（前缀 `OPS_`）

| 变量 | 说明 |
|------|------|
| `OPS_LLM_ENABLED` | `true` 时调用百炼润色口播（需 `OPS_BAILIAN_APP_ID` + 主配置 `BAILIAN_API_KEY`） |
| `OPS_BAILIAN_APP_ID` | 运营专用百炼应用 ID（勿与付费报告混用） |
| `OPS_WEIBO_ACCESS_TOKEN` | 微博开放平台 `access_token`，拉取 hourly trends |
| `OPS_RSS_FEED_URLS` | 逗号分隔 RSS URL（权威媒体标题作叙事锚点） |
| `OPS_FRONTEND_BASE_URL` | 与 `FRONTEND_URL` 一致时用于文案中的链接展示 |
| `OPS_TOP_K_ANGLES` | 输出 Top-K 选题（默认 3） |
| `OPS_CALENDAR_YAML` | 覆盖默认节日/禁忌词配置文件路径 |
| `OPS_WAN_IMAGE_ENABLED` | 是否文生图（默认 true） |
| `OPS_WAN_VIDEO_ENABLED` | 是否文生视频（默认 false） |
| `OPS_DASHSCOPE_API_KEY` | 可选，覆盖 `BAILIAN_API_KEY` 仅用于万相 |
| `OPS_DASHSCOPE_WORKSPACE` | 可选业务空间 ID |
| `OPS_WAN_CAROUSEL_MODE` | `asset_first`（首帧项目 `/zodiac/{slug}.webp` + 万相）或 `ai_only`（三帧均万相） |
| `OPS_TRAFFIC_QR_ENABLED` | 是否生成 `media/traffic_qr.png`（默认 true） |

完整列表见 [`../.env.example`](../.env.example)。

节日与禁忌词默认见 [`ops/config/calendar.yaml`](config/calendar.yaml)。

## 每日 SOP（≤30 分钟）

1. 运行 `python -m ops.cli daily`（可由 cron 触发）。
2. 打开 `out/<date>/manifest.json`：检查 `compliance`、`wan_media`、`hotspot_report`、`douyin_kit`、数据源、`angles`。
3. 优先使用 `douyin_publish.md` + `pinned_comment.txt`（及 `traffic_qr.png`）发抖音；图片/视频已在 `media/` 下则可直接用；否则仍可用 `media_prompts.json` 手动生成。
4. 使用文案中的 UTM 链接做复盘。

## 数据源说明

- **天象**：`app.services.astro_service`（Swiss Ephemeris / kerykeion）。
- **日运**：Redis `daily:{sign}:{date}`，与线上一致。
- **微博 / RSS**：可选；失败自动降级，不中断生成。

## CTA 与定价

与 [`docs/spec.md`](../../docs/spec.md) 对齐：`free_daily`、`personality`（9.9）、`compatibility`（19.9）、`annual`（29.9）、`chat`（9.9）。
