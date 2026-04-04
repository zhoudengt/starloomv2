# StarLoom v2 — 架构设计文档

## 1. 整体架构概览

基于经典 Web 服务架构，分 MVP 和扩展两个阶段实施。

### 架构层级

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│              Web 浏览器（H5）    手机浏览器                    │
└────────────┬────────────────────────┬───────────────────────┘
             │                        │
      www.starloom.cn          api.starloom.cn
      (前端静态资源)            (后端 API)
             │                        │
┌────────────▼────────────────────────▼───────────────────────┐
│                     网络接入层                                │
│    CDN（静态资源加速）      Load Balancer（负载均衡）           │
└────────────┬────────────────────────┬───────────────────────┘
             │                        │
┌────────────▼────────────────────────▼───────────────────────┐
│                      应用服务层                               │
│                                                              │
│  ┌──────────────────────────────────────────────┐            │
│  │  Web Servers (FastAPI + Uvicorn)              │            │
│  │  - /api/v1/daily/*     每日运势               │            │
│  │  - /api/v1/report/*    付费报告（SSE 流式）    │            │
│  │  - /api/v1/payment/*   支付处理               │            │
│  │  - /api/v1/user/*      用户管理               │            │
│  └──────┬──────────┬──────────┬─────────────────┘            │
│         │          │          │                               │
│    ┌────▼───┐ ┌────▼───┐ ┌───▼─────┐                        │
│    │ MySQL  │ │ Redis  │ │ Workers │  (异步任务)              │
│    │ (持久) │ │ (缓存) │ │ (定时)  │                          │
│    └────────┘ └────────┘ └─────────┘                         │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                     外部服务层                                 │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ Coze API │  │ 百炼 API  │  │ 虎皮椒   │                    │
│  │ (LLM主)  │  │ (LLM备)  │  │  (支付)  │                    │
│  └──────────┘  └──────────┘  └──────────┘                    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. MVP 阶段架构

最简方案，单机部署，快速上线。

### 2.1 部署拓扑（Docker Compose 独立编排）

> **核心原则：每个项目独立一套数据库、缓存、容器网络，禁止与 HiFate 或其他项目共用。**

```
一台云服务器（2C4G，阿里云/腾讯云轻量应用 ~60-80元/月）
    │
    └── Docker Compose（starloom-network 独立网络）
            │
            ├── starloom-nginx（反向代理 + 静态文件 + HTTPS）
            │       ├── / → 前端 H5 静态文件（dist/）
            │       └── /api/ → starloom-backend:8000
            │
            ├── starloom-backend（FastAPI + Uvicorn）
            │       ├── 处理 HTTP 请求
            │       ├── SSE 流式输出（报告生成）
            │       └── 虎皮椒支付回调接收
            │
            ├── starloom-mysql（MySQL 8，端口 3307:3306）
            │       └── starloom 库（独立数据卷）
            │
            ├── starloom-redis（Redis 7，端口 6380:6379）
            │       ├── 每日运势缓存
            │       ├── 用户 Session
            │       └── 接口限流
            │
            └── Cron Job（宿主机或容器内定时任务）
                    └── 每天 00:30 批量生成 12 星座运势

端口映射（避免与 HiFate / 本地服务冲突）：
  - MySQL: 3307 (StarLoom) vs 3306 (HiFate/本地)
  - Redis:  6380 (StarLoom) vs 6379 (HiFate/本地)
  - API:    8000 (StarLoom) vs 8001 (HiFate)
  - HTTP:   80/443 (按域名区分)
```

### 2.2 Nginx 配置要点

```nginx
server {
    listen 443 ssl http2;
    server_name starloom.cn;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 前端静态文件
    location / {
        root /var/www/starloom/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE 流式支持（关键配置）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # 虎皮椒支付回调
    location /api/v1/payment/notify {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2.3 关键技术决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 部署方式 | Docker Compose 独立编排 | 与 HiFate 完全隔离，互不影响 |
| Web 服务器 | Uvicorn + Gunicorn | FastAPI 标准方案，支持异步 |
| 进程数 | 2-4 workers | 2C CPU 对应 2-4 个 worker |
| 数据库 | 独立 MySQL 容器（端口 3307） | 与 HiFate 隔离，独立数据卷 |
| 缓存 | 独立 Redis 容器（端口 6380） | 与 HiFate 隔离，独立数据卷 |
| HTTPS | Let's Encrypt 免费证书 | 微信支付必须 HTTPS |
| CDN | 可选（七牛/又拍云免费额度） | 前端静态资源加速 |

---

## 3. 扩展阶段架构

当用户量增长时，按需扩展。

### 3.1 第一阶段扩展（日活 5,000+）

```
变化：
- 前端静态文件迁移到 CDN
- MySQL 迁移到云 RDS（自动备份）
- Redis 迁移到云 Redis
- 增加 Nginx 缓存层
```

### 3.2 第二阶段扩展（日活 20,000+）

```
变化：
- 增加 Load Balancer（阿里云 SLB / Nginx）
- 后端扩展到 2-3 台 Web Server
- MySQL 读写分离（1 主 1 从）
- Redis Sentinel（高可用）
```

### 3.3 第三阶段扩展（日活 50,000+）

对应架构参考图中的完整架构：

```
用户 → CDN + Load Balancer
        │
        ├── Web Server x N（无状态，水平扩展）
        │
        ├── Message Queue（RabbitMQ / Redis Stream）
        │       └── Workers（消费异步任务）
        │           ├── 批量生成每日运势
        │           ├── 生成报告（后台异步）
        │           └── 发送通知
        │
        ├── MySQL Cluster（主从 + 读写分离）
        ├── Redis Cluster（分片）
        └── MongoDB（可选：用户行为分析、内容存储）

工具层：
  - Logging（日志收集：ELK / 阿里云 SLS）
  - Metrics（监控指标：Prometheus + Grafana）
  - Monitoring（告警：阿里云云监控）
  - Automation（自动化部署：GitHub Actions / Jenkins）
```

### 3.4 扩展决策指标

| 指标 | 当前承载 | 触发扩展的阈值 | 扩展动作 |
|------|---------|---------------|---------|
| API QPS | ~100 | > 200 | 加 Web Server |
| 数据库连接 | ~50 | > 100 | 迁移到云 RDS |
| Redis 内存 | ~100MB | > 500MB | 迁移到云 Redis |
| 磁盘 | 40GB | > 30GB 使用 | 扩容或迁移 |
| LLM 调用延迟 | ~3s | > 5s 常态 | 增加 LLM 平台（百炼备份） |

---

## 4. 数据流详解

### 4.1 免费运势请求流

```
用户访问 /daily/aries
    │
    ▼
前端 GET /api/v1/daily/aries
    │
    ▼
后端 → 查 Redis 缓存 daily:aries:2026-03-31
    │
    ├── 命中 → 直接返回 JSON（<10ms）
    │
    └── 未命中 → 调用 LLM 生成（~3s）
                    │
                    ├── 写入 Redis（TTL 24h）
                    ├── 写入 MySQL daily_fortunes 表（备份）
                    └── 返回 JSON
```

### 4.2 付费报告请求流

```
用户点击"购买报告"
    │
    ▼
前端 POST /api/v1/payment/create
    │
    ▼
后端创建订单（MySQL orders 表，status=pending）
    │
    ▼
调用虎皮椒 API 获取支付链接
    │
    ▼
返回 url（及可选 url_qrcode）→ 前端跳转或展示扫码图
    │
    ▼
用户完成支付
    │
    ├── 虎皮椒异步回调 → 后端验签 → 更新订单 status=paid
    │
    └── 前端轮询订单状态（每 2 秒）
            │
            ▼
        status=paid → 前端 POST /api/v1/report/personality
            │
            ▼
        后端调用 LLM 流式生成 → SSE 逐字返回前端
            │
            ▼
        前端逐字渲染报告内容
            │
            ▼
        生成完毕 → 保存到 MySQL reports 表
```

### 4.3 每日批量生成流

```
Cron Job: 每天 00:30 触发
    │
    ▼
scripts/generate_daily.py
    │
    ▼
循环 12 星座：
    ├── 调用 LLM 生成当日运势（JSON）
    ├── 写入 Redis: daily:{sign}:{date}（TTL 24h）
    └── 写入 MySQL daily_fortunes 表（备份）
    │
    ▼
日志记录：12 个星座生成完成，耗时 ~2 分钟
```

---

## 5. LLM 对接架构

### 5.1 工厂模式（参考 HiFate）

```python
# 服务抽象层
class BaseLLMService(ABC):
    @abstractmethod
    async def generate(self, prompt: str, params: dict) -> str:
        """非流式生成"""
        pass

    @abstractmethod
    async def stream_generate(self, prompt: str, params: dict) -> AsyncGenerator[str, None]:
        """流式生成"""
        pass

class CozeService(BaseLLMService):
    """Coze Bot 对接"""
    pass

class BailianService(BaseLLMService):
    """阿里云百炼对接"""
    pass

class LLMServiceFactory:
    @staticmethod
    def create(platform: str = None) -> BaseLLMService:
        platform = platform or os.getenv("LLM_PLATFORM", "coze")
        if platform == "coze":
            return CozeService()
        elif platform == "bailian":
            return BailianService()
        raise ValueError(f"Unknown platform: {platform}")
```

### 5.2 Coze 对接要点

```
API 基地址: https://api.coze.cn（国内版）
认证方式: Bearer Token（Personal Access Token）
请求格式: OpenAI 兼容的 Chat Completion

创建 3 个 Bot：
  1. 每日运势 Bot（输出 JSON 格式）
  2. 个人报告 Bot（输出 Markdown 长文）
  3. 配对分析 Bot（输出 Markdown 长文）

每个 Bot 在 Coze 控制台配置好 System Prompt，
代码中只需传 user message（用户的出生信息等）。

流式调用：
  POST /open_api/v2/chat/completions
  Body: { "bot_id": "xxx", "user": "user_id", "query": "...", "stream": true }
  Response: SSE 格式，逐 token 输出
```

### 5.3 百炼对接要点（备用）

```
API 基地址: 阿里云百炼 API
认证方式: API Key
用途: 当 Coze 不可用时的降级方案
对接方式: 同样支持流式输出
```

### 5.4 降级策略

```
正常: Coze API → 返回结果
    │
    └── Coze 超时/报错
            │
            ▼
        自动切换百炼 API → 返回结果
            │
            └── 百炼也失败
                    │
                    ▼
                返回 fallback 内容（预生成的通用运势模板）
                + 记录告警日志
```

---

## 6. 安全与性能

### 6.1 接口限流

```
免费接口: 60 次/分钟/IP
付费接口: 20 次/分钟/用户
支付创建: 5 次/分钟/用户
LLM 调用: 全局 100 次/分钟（防止费用爆炸）
```

使用 Redis + 滑动窗口实现。

### 6.2 安全措施

- HTTPS 全站加密
- 虎皮椒回调验签（hash / MD5）
- JWT Token 认证（付费接口）
- SQL 注入防护（SQLAlchemy ORM）
- XSS 防护（前端输出转义）
- CORS 配置（只允许自己的域名）
- 环境变量管理敏感信息（不硬编码）

### 6.3 性能目标

| 指标 | 目标 |
|------|------|
| 免费运势接口 | < 50ms（缓存命中） |
| 付费报告首字节 | < 2s（LLM 流式） |
| 支付创建 | < 1s |
| H5 首屏加载 | < 2s（移动端 4G） |

---

## 7. 监控与日志

### MVP 阶段（简单方案）

```
- 应用日志: Python logging → 文件（logrotate 轮转）
- 访问日志: Nginx access.log
- 错误告警: 邮件/微信通知（关键错误）
- 简单看板: 每日查看订单数、收入、活跃用户数（手动 SQL）
```

### 扩展阶段

```
- 日志收集: ELK Stack 或 阿里云 SLS
- 指标监控: Prometheus + Grafana
- 告警: 阿里云云监控 / PagerDuty
- APM: 链路追踪（可选）
```

---

## 8. 成本估算（MVP）

| 项目 | 月费用 | 说明 |
|------|--------|------|
| 云服务器 2C4G | 60-80 元 | 阿里云轻量应用 |
| 域名 | 5-10 元/月 | .cn 域名约 50-100/年 |
| SSL 证书 | 0 | Let's Encrypt 免费 |
| Coze API | 0-50 元 | 个人版有免费额度 |
| 虎皮椒 | 开户费+按交易 | 以官网为准 |
| CDN | 0-20 元 | 七牛/又拍云有免费额度 |
| **合计** | **~100 元/月** | 极低启动成本 |

盈亏平衡点：每月 4-5 单付费（约 50-100 元收入）即可覆盖服务器成本。
