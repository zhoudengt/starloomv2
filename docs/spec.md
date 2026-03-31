# StarLoom v2 — 产品与技术详细设计

## 1. 产品定义

### 1.1 核心定位
基于 AI 的星座性格分析与运势服务。面向国内 18-35 岁用户，通过抖音短视频引流到 H5 页面变现。

### 1.2 产品形态
- **免费层**：每日 12 星座运势（引流 + 留存）
- **付费层**：个性化深度报告（AI 实时生成，非模板）

### 1.3 定价

| 产品 | 价格 | 定位 | 付费触发场景 |
|------|------|------|-------------|
| 每日运势 | 免费 | 引流入口 | — |
| 星座性格报告 | 9.9 元 | 低门槛尝鲜 | 看完运势想深入了解 |
| 双人配对报告 | 19.9 元 | 主力收入产品 | 情侣/暗恋/朋友关系 |
| 年度运势报告 | 29.9 元 | 高客单价 | 新年/生日节点 |
| AI 星座顾问对话 | 9.9 元/次 | 复购型 | 遇到具体问题想问 |

### 1.4 收入预期（诚实版）

- **第 1-2 周**：产品上线 + 开始发内容，收入 0
- **第 1 个月**：积累粉丝，月入 0-500 元
- **第 2-3 个月**：内容起量，月入 1,000-5,000 元
- **第 4-6 个月**：执行力强、内容持续，月入 1-3 万
- **第 6 个月后**：有可能突破 6 万/月

达到 6 万/月的数学：29.9 元/单 x 5% 转化 → 需日均 1,300+ 访客 → 约需 10 万+ 抖音粉丝。

---

## 2. 架构设计

### 2.1 MVP 阶段架构（第一版）

```
用户手机浏览器
    │
    ├─ 静态资源 ──→ CDN（前端 H5 打包文件）
    │
    └─ API 请求 ──→ FastAPI 后端服务（单机）
                        │
                        ├── Redis（缓存：每日运势、会话、限流）
                        ├── MySQL（持久化：用户、订单、报告记录）
                        ├── Coze API（AI 分析，流式 SSE）
                        ├── 百炼 API（AI 备用通道）
                        └── xorpay API（支付回调）
```

MVP 只需要：
- 1 台云服务器（2C4G 即可，推荐阿里云/腾讯云轻量应用）
- **独立的 MySQL 数据库**：库名 `starloom`，禁止与 HiFate 共用数据库实例或库
- **独立的 Redis 实例**：使用独立 Redis 实例或独立 db 编号（如 db1），禁止与 HiFate 共用
- 域名 + SSL 证书（必须 HTTPS，微信支付要求）
- CDN（可选，前端静态文件托管）
- **部署方式**：Docker Compose 独立编排（MySQL + Redis + 后端 + Nginx），一个项目一套容器，互不干扰

### 2.2 扩展阶段架构（用户量增长后）

参考架构图（`docs/architecture.md`），未来扩展方向：

```
用户（Web + Mobile）
    │
    ├── CDN（静态资源）
    │
    └── Load Balancer（负载均衡）
            │
            ├── Web Server 1 ─┐
            ├── Web Server 2 ─┤──→ MySQL（主从）
            └── Web Server N ─┘──→ Redis Cluster
                    │
                    ├── Message Queue（异步任务：批量生成运势、发送通知）
                    │       └── Workers（消费任务）
                    │
                    └── NoSQL（MongoDB：用户行为分析、内容存储）
```

扩展时机判断：
- 日活 > 5,000 → 考虑加 CDN + 负载均衡
- 日活 > 20,000 → 考虑 MySQL 读写分离 + Redis Cluster
- 日活 > 50,000 → 考虑消息队列 + Worker 异步处理

### 2.3 与 HiFate 的关系

StarLoom 是**完全独立**的项目，不依赖 HiFate 的代码或服务器。但可以参考 HiFate 的以下架构模式：

| 模式 | HiFate 实现 | StarLoom 参考点 |
|------|------------|----------------|
| LLM 工厂 | `server/services/llm_service_factory.py` | 同样用工厂模式切换 Coze/百炼 |
| 流式输出 | SSE + gRPC-Web | 简化为纯 SSE（不需要 gRPC） |
| 数据编排 | `BaziDataOrchestrator` | 星座计算简单，不需要编排器 |
| 支付 | 统一支付工厂 + Stripe/Payermax | 简化为 xorpay 单一通道 |
| 缓存 | `CacheKeyGenerator` | 参考 key 命名规范，简化实现 |
| Prompt | `server/utils/prompts/` 集中管理 | 同样集中到 `prompts/` 目录 |

---

## 3. 后端 API 详细设计

### 3.1 API 总览

基础路径：`/api/v1`

| 方法 | 路径 | 说明 | 认证 | 付费 |
|------|------|------|------|------|
| GET | `/signs` | 获取 12 星座基本信息 | 否 | 免费 |
| GET | `/signs/{sign}` | 单个星座详情 | 否 | 免费 |
| GET | `/daily/{sign}` | 今日运势 | 否 | 免费 |
| GET | `/daily/all` | 所有星座今日运势摘要 | 否 | 免费 |
| POST | `/report/personality` | 个人性格分析报告 | 是 | 9.9 |
| POST | `/report/compatibility` | 配对分析报告 | 是 | 19.9 |
| POST | `/report/annual` | 年度运势报告 | 是 | 29.9 |
| POST | `/chat` | AI 星座顾问对话 | 是 | 9.9/次 |
| POST | `/payment/create` | 创建支付订单 | 是 | — |
| GET | `/payment/status/{order_id}` | 查询订单状态 | 是 | — |
| POST | `/payment/notify` | xorpay 异步回调 | 否 | — |
| POST | `/user/login` | 用户登录/注册 | 否 | — |
| GET | `/user/profile` | 获取用户信息 | 是 | — |
| GET | `/user/orders` | 用户订单列表 | 是 | — |

### 3.2 核心接口详细设计

#### GET `/api/v1/daily/{sign}` — 每日运势

```
请求：
  GET /api/v1/daily/aries

响应（200）：
{
  "sign": "aries",
  "sign_cn": "白羊座",
  "date": "2026-03-31",
  "overall_score": 85,
  "love_score": 70,
  "career_score": 90,
  "wealth_score": 80,
  "health_score": 85,
  "lucky_color": "红色",
  "lucky_number": 7,
  "summary": "今天精力充沛，适合主动出击...",
  "love": "感情方面可能会有意外的惊喜...",
  "career": "工作中容易获得上级认可...",
  "wealth": "理财方面保持稳健...",
  "health": "注意劳逸结合...",
  "advice": "抓住上午的好时机..."
}
```

缓存策略：
- Redis key: `daily:{sign}:{YYYY-MM-DD}`
- TTL: 24 小时
- 每日凌晨 00:30 由定时任务批量生成 12 个星座的运势并写入缓存
- 如果缓存未命中（首次或过期），实时调用 LLM 生成

#### POST `/api/v1/report/personality` — 个人性格报告（流式）

```
请求：
  POST /api/v1/report/personality
  Headers: Authorization: Bearer {token}
  Body: {
    "birth_date": "1995-06-15",
    "birth_time": "14:30",  // 可选，用于更精确分析
    "gender": "female"       // 可选
  }

响应（200，SSE 流式）：
  Content-Type: text/event-stream

  data: {"type": "section", "title": "太阳星座分析"}
  data: {"type": "content", "text": "你的太阳星座是双子座"}
  data: {"type": "content", "text": "，天生具有灵活多变的思维方式"}
  data: {"type": "content", "text": "和出色的沟通能力..."}
  data: {"type": "section", "title": "性格特质"}
  data: {"type": "content", "text": "你的性格中最突出的是..."}
  ...
  data: {"type": "done", "report_id": "rpt_xxx"}
```

前端接收方式：
```javascript
const response = await fetch('/api/v1/report/personality', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
const reader = response.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // 解析 SSE data 行，逐字渲染到页面
}
```

#### POST `/api/v1/report/compatibility` — 配对分析（流式）

```
请求：
  POST /api/v1/report/compatibility
  Headers: Authorization: Bearer {token}
  Body: {
    "person1": { "birth_date": "1995-06-15", "gender": "female", "name": "小明" },
    "person2": { "birth_date": "1993-11-22", "gender": "male", "name": "小红" }
  }

响应：SSE 流式（同上格式）
```

#### POST `/api/v1/payment/create` — 创建支付订单

```
请求：
  POST /api/v1/payment/create
  Headers: Authorization: Bearer {token}
  Body: {
    "product_type": "personality",   // personality / compatibility / annual / chat
    "amount": 9.9,
    "pay_method": "wechat"           // wechat / alipay
  }

响应（200）：
{
  "order_id": "ord_20260331_xxx",
  "pay_url": "https://xorpay.com/pay/xxx",  // 跳转到支付页面的 URL
  "qr_code": "https://...",                   // 或二维码图片地址
  "expire_at": "2026-03-31T12:30:00"
}
```

#### POST `/api/v1/payment/notify` — xorpay 异步回调

```
请求（由 xorpay 服务器发送）：
  POST /api/v1/payment/notify
  Body: {
    "aoid": "xorpay_order_id",
    "order_id": "ord_20260331_xxx",
    "pay_price": "9.90",
    "pay_time": "2026-03-31 12:05:33",
    "sign": "md5_signature"
  }

处理逻辑：
  1. 验证 sign（MD5(order_id + pay_price + app_secret)）
  2. 查询订单，确认金额一致
  3. 更新订单状态为 paid
  4. 返回 "success" 字符串

响应：
  200 OK
  Body: "success"
```

### 3.3 用户认证

MVP 阶段使用简单的手机号 + 验证码登录，或微信 H5 静默授权：

- 登录后颁发 JWT Token（有效期 7 天）
- 免费接口不需要 Token
- 付费接口必须携带 Token
- 后续可扩展微信授权登录

简化方案（MVP 最快上线）：
- 不做登录，用设备指纹（UUID）标识用户
- 付费时直接跳转 xorpay 支付页面
- 支付成功后回调关联设备 UUID
- 后续迭代再加正式登录

---

## 4. 前端页面设计

### 4.1 页面列表

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | `/` | 12 星座卡片 + 今日运势预览 |
| 每日运势 | `/daily/:sign` | 单星座详细运势（免费） |
| 个人报告 | `/report/personality` | 付费个人分析（流式输出） |
| 配对分析 | `/report/compatibility` | 付费配对分析（流式输出） |
| 支付结果 | `/payment/result` | 支付成功/失败/等待 |
| 我的 | `/profile` | 用户信息 + 历史报告 |

### 4.2 首页设计

```
┌──────────────────────────────┐
│  StarLoom ✨ 星座分析         │  ← 顶部 Logo + 品牌名
│                              │
│  今日运势 · 2026年3月31日     │  ← 日期
│                              │
│  ┌─────┐ ┌─────┐ ┌─────┐   │
│  │ ♈   │ │ ♉   │ │ ♊   │   │  ← 12 星座网格（3x4）
│  │白羊座│ │金牛座│ │双子座│   │    点击进入每日运势
│  │ 85分 │ │ 72分 │ │ 90分 │   │
│  └─────┘ └─────┘ └─────┘   │
│  ┌─────┐ ┌─────┐ ┌─────┐   │
│  │ ♋   │ │ ♌   │ │ ♍   │   │
│  │巨蟹座│ │狮子座│ │处女座│   │
│  │ 78分 │ │ 88分 │ │ 65分 │   │
│  └─────┘ └─────┘ └─────┘   │
│  ... (后 6 个)               │
│                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                              │
│  🔮 深度分析                  │  ← 付费入口区
│  ┌────────────────────────┐  │
│  │ 个人星座性格报告  ¥9.9  │  │
│  │ AI 深度解读你的星座密码  │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │ 星座配对分析    ¥19.9   │  │
│  │ 看看你们的缘分指数      │  │
│  └────────────────────────┘  │
│                              │
└──────────────────────────────┘
```

### 4.3 每日运势页

```
┌──────────────────────────────┐
│  ← 返回        白羊座 ♈      │
│                              │
│  ┌────────────────────────┐  │
│  │     综合运势 85/100     │  │  ← 圆形进度环
│  │        ████████░░       │  │
│  └────────────────────────┘  │
│                              │
│  💕 爱情 ★★★★☆  70          │  ← 分项评分
│  💼 事业 ★★★★★  90          │
│  💰 财运 ★★★★☆  80          │
│  🏥 健康 ★★★★☆  85          │
│                              │
│  📝 今日概述                  │
│  今天精力充沛，适合主动出击... │
│                              │
│  💕 感情详解                  │
│  感情方面可能会有意外的惊喜... │
│                              │
│  💼 事业详解                  │
│  工作中容易获得上级认可...     │
│                              │
│  🍀 幸运提示                  │
│  幸运色：红色 | 幸运数字：7   │
│                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ┌────────────────────────┐  │
│  │  想了解更多？            │  │  ← 付费转化入口
│  │  解锁完整性格分析 ¥9.9  │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

### 4.4 设计风格

- **主色调**：深紫 (#2D1B69) + 金色 (#F0C75E) + 星空渐变
- **背景**：深色系（模拟星空/宇宙感）
- **字体**：标题用思源宋体，正文用思源黑体
- **动效**：星座符号微动画、流式文字逐字出现效果、评分环形进度条动画
- **整体感觉**：神秘 + 高级 + 现代，不要廉价感

---

## 5. AI Prompt 设计

### 5.1 每日运势 Prompt

```
你是一位专业的星座分析师，请为{sign_cn}生成今日({date})的运势分析。

要求：
1. 综合运势评分（0-100）
2. 分项评分：爱情、事业、财运、健康（各 0-100）
3. 幸运色和幸运数字
4. 今日概述（50-80字）
5. 爱情详解（60-100字）
6. 事业详解（60-100字）
7. 财运简述（30-50字）
8. 健康提示（30-50字）
9. 今日建议（一句话）

请以 JSON 格式输出，字段如下：
{
  "overall_score": 85,
  "love_score": 70,
  "career_score": 90,
  "wealth_score": 80,
  "health_score": 85,
  "lucky_color": "红色",
  "lucky_number": 7,
  "summary": "...",
  "love": "...",
  "career": "...",
  "wealth": "...",
  "health": "...",
  "advice": "..."
}

语气要求：积极向上但不空泛，具体实用，像朋友间的贴心建议。
避免：绝对化表述（一定会、必须、肯定），负面恐吓。
```

### 5.2 个人性格报告 Prompt

```
你是一位资深的星座性格分析师。用户出生日期为{birth_date}，太阳星座为{sun_sign}。
{如果有出生时间：出生时间为{birth_time}，可参考月亮星座和上升星座。}

请生成一份深度个性化的星座性格分析报告，包含以下章节：

## 1. 太阳星座解读
解读核心性格特质、行为模式、价值观。

## 2. 性格优势
3-5 个突出优点，结合具体场景说明。

## 3. 性格挑战
2-3 个需要注意的方面，给出建设性建议。

## 4. 感情特质
恋爱观、理想伴侣类型、相处模式。

## 5. 事业方向
适合的职业方向、工作风格、职场建议。

## 6. 人际关系
社交风格、与不同星座的相处之道。

## 7. 成长建议
个人发展方向、需要培养的能力。

要求：
- 每个章节 150-300 字
- 语气温暖专业，像一位懂你的老朋友
- 内容要有具体洞察，不要泛泛而谈
- 适当引用星座特质但不死板
- 总字数 1500-2500 字
```

### 5.3 配对分析 Prompt

```
你是一位专业的星座关系分析师。
用户 A：{name1}，出生日期 {birth_date1}，太阳星座 {sign1}
用户 B：{name2}，出生日期 {birth_date2}，太阳星座 {sign2}

请生成一份深度配对分析报告：

## 1. 缘分指数
总体契合度评分（0-100），以及各维度评分：
- 性格契合度
- 感情契合度
- 价值观契合度
- 生活习惯契合度

## 2. 你们的化学反应
两个星座相遇会碰撞出什么火花？核心吸引力在哪里？

## 3. 甜蜜优势
这段关系中最美好的部分，让你们走在一起的理由。

## 4. 潜在摩擦
可能出现分歧的地方，以及具体表现。

## 5. 相处秘诀
5 条针对性的建议，帮助你们更好地经营关系。

## 6. 总结寄语
一段温暖的祝福和总结。

要求：
- 总字数 1200-2000 字
- 具体到两个人的星座特质互动，不要泛泛而谈
- 语气积极温暖，即使指出问题也给出解决方案
- 不做绝对判断（不说"不合适"、"注定分开"等）
```

---

## 6. 支付对接：xorpay

### 6.1 xorpay 简介
xorpay（虎皮椒）是国内个人开发者常用的聚合支付平台，支持微信和支付宝，个人无需企业资质即可接入。

官网：https://xorpay.com

### 6.2 对接流程

```
用户点击"购买报告"
    │
    ▼
前端 POST /api/v1/payment/create
    │
    ▼
后端创建本地订单（MySQL，状态=pending）
    │
    ▼
后端调用 xorpay API 创建支付
    │
    ▼
返回支付 URL 给前端
    │
    ▼
前端跳转到 xorpay 支付页面（或展示二维码）
    │
    ▼
用户完成支付
    │
    ├── xorpay 异步回调 POST /api/v1/payment/notify
    │       │
    │       ▼
    │   后端验签 → 更新订单状态为 paid
    │
    └── 前端轮询 GET /api/v1/payment/status/{order_id}
            │
            ▼
        订单状态变为 paid → 解锁报告内容
```

### 6.3 xorpay API 调用

创建订单：
```
POST https://xorpay.com/api/pay/create
Content-Type: application/json

{
  "name": "星座性格分析报告",
  "pay_type": "native",           // native=扫码 / jsapi=公众号
  "price": "9.90",
  "order_id": "ord_20260331_xxx",
  "notify_url": "https://yourdomain.com/api/v1/payment/notify",
  "return_url": "https://yourdomain.com/payment/result?order_id=ord_20260331_xxx"
}
Headers: Authorization: Bearer {app_id}:{sign}

sign = MD5(app_id + order_id + price + app_secret)
```

回调验签：
```python
import hashlib

def verify_xorpay_sign(data: dict, app_secret: str) -> bool:
    """验证 xorpay 回调签名"""
    expected = hashlib.md5(
        f"{data['aoid']}{data['order_id']}{data['pay_price']}{app_secret}".encode()
    ).hexdigest()
    return expected == data.get('sign', '')
```

### 6.4 注意事项
- xorpay 手续费约 1.5%-2%（远低于抖音小程序 50%）
- 提现到个人银行卡/支付宝，T+1 到账
- 需要实名认证但不需要企业资质
- 回调 URL 必须是 HTTPS 公网可访问地址

---

## 7. 数据库设计

### 7.0 数据库隔离原则

> **每个项目独立一套数据库和缓存，禁止共用。**

| 资源 | StarLoom | HiFate | 说明 |
|------|----------|--------|------|
| MySQL | `starloom` 库（独立实例或独立库） | `hifate` 库 | 禁止共用同一个库 |
| Redis | 独立实例，或同实例使用 `db1` | `db0` | 禁止共用同一个 db |
| Docker 网络 | `starloom-network` | `hifate-network` | 容器网络隔离 |
| 数据卷 | `starloom-mysql-data` / `starloom-redis-data` | 各自独立 | 数据卷不共享 |

Docker Compose 示例（`docker-compose.yml`）：

```yaml
version: "3.8"
services:
  mysql:
    image: mysql:8.0
    container_name: starloom-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: starloom
    ports:
      - "3307:3306"        # 用 3307 避免与本地/HiFate 的 3306 冲突
    volumes:
      - starloom-mysql-data:/var/lib/mysql
    networks:
      - starloom-network

  redis:
    image: redis:7-alpine
    container_name: starloom-redis
    ports:
      - "6380:6379"        # 用 6380 避免与本地/HiFate 的 6379 冲突
    volumes:
      - starloom-redis-data:/data
    networks:
      - starloom-network

  backend:
    build: ./backend
    container_name: starloom-backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      - mysql
      - redis
    networks:
      - starloom-network

  nginx:
    image: nginx:alpine
    container_name: starloom-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html
      - ./deploy/nginx.conf:/etc/nginx/conf.d/default.conf
      - ./deploy/certs:/etc/nginx/certs
    depends_on:
      - backend
    networks:
      - starloom-network

volumes:
  starloom-mysql-data:
  starloom-redis-data:

networks:
  starloom-network:
    driver: bridge
```

### 7.1 用户表 `users`

```sql
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL COMMENT '设备指纹UUID',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号（可选）',
    nickname VARCHAR(50) DEFAULT NULL,
    birth_date DATE DEFAULT NULL COMMENT '出生日期',
    birth_time TIME DEFAULT NULL COMMENT '出生时间（可选）',
    sun_sign VARCHAR(20) DEFAULT NULL COMMENT '太阳星座',
    gender ENUM('male', 'female', 'unknown') DEFAULT 'unknown',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_device (device_id),
    INDEX idx_sign (sun_sign)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 7.2 订单表 `orders`

```sql
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(64) UNIQUE NOT NULL COMMENT '业务订单号',
    user_id BIGINT NOT NULL,
    product_type ENUM('personality', 'compatibility', 'annual', 'chat') NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status ENUM('pending', 'paid', 'expired', 'refunded') DEFAULT 'pending',
    pay_method VARCHAR(20) DEFAULT NULL COMMENT 'wechat/alipay',
    xorpay_order_id VARCHAR(64) DEFAULT NULL COMMENT 'xorpay 订单号',
    paid_at DATETIME DEFAULT NULL,
    expired_at DATETIME NOT NULL COMMENT '订单过期时间',
    extra_data JSON DEFAULT NULL COMMENT '附加数据（报告参数等）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order_id (order_id),
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 7.3 报告表 `reports`

```sql
CREATE TABLE reports (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    report_id VARCHAR(64) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    order_id VARCHAR(64) DEFAULT NULL COMMENT '关联订单（免费报告为空）',
    report_type ENUM('daily', 'personality', 'compatibility', 'annual') NOT NULL,
    sign VARCHAR(20) NOT NULL,
    input_data JSON NOT NULL COMMENT '输入参数',
    content TEXT NOT NULL COMMENT '报告内容',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_report_id (report_id),
    INDEX idx_user (user_id),
    INDEX idx_type_sign (report_type, sign),
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 7.4 每日运势缓存表 `daily_fortunes`（MySQL 备份，主要在 Redis）

```sql
CREATE TABLE daily_fortunes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sign VARCHAR(20) NOT NULL,
    fortune_date DATE NOT NULL,
    content JSON NOT NULL COMMENT '运势内容（JSON 格式）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sign_date (sign, fortune_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 8. 抖音运营策略

### 8.1 账号定位

- **账号名**：StarLoom 星座研究所 / AI 星座分析师（待定）
- **人设**：用 AI 技术做深度星座解读的专业分析师
- **差异化**：不是模板内容，每条分析都是 AI 实时生成
- **Bio**：「AI 深度星座分析 | 点击下方链接获取你的专属报告 ↓」

### 8.2 内容矩阵

| 内容类型 | 频率 | 目的 | 制作方式 |
|---------|------|------|---------|
| 每日运势 | 每天 1 条 | 基础流量 | AI 生成文案 + 剪映模板 |
| 配对分析 | 每周 2-3 条 | 高互动（评论区互动） | AI 生成 + 真人/AI 配音 |
| 性格揭秘 | 每周 2-3 条 | 涨粉 | 热门话题 + 星座角度 |
| 产品演示 | 每周 1-2 条 | 转化 | 屏幕录制 H5 页面 |

### 8.3 引流路径

```
抖音短视频
    ↓ （评论区引导："点主页链接看完整分析"）
抖音主页
    ↓ （主页链接指向 H5）
H5 首页（免费看运势）
    ↓ （页面内引导"解锁完整报告"）
付费页面
    ↓ （支付 9.9-29.9）
xorpay 支付
    ↓ （支付成功回调）
查看报告
```

### 8.4 视频批量制作流程

每周日集中制作下周内容：
1. 用 AI（Coze/ChatGPT）批量生成 7 天运势文案
2. 用剪映/CapCut 的模板批量套用
3. AI 文字转语音（或真人录制）
4. 添加背景音乐 + 字幕
5. 定时发布（每天早 8 点）

预计每周花 2-3 小时制作 7-10 条视频。

---

## 9. 合规指南

### 9.1 内容定性
- 产品定位为 **"星座文化与性格分析娱乐服务"**
- 不是算命、占卜、预测未来

### 9.2 必须有的声明
在 H5 页面底部和每份报告末尾加：

> 本服务基于星座文化提供性格分析参考，仅供娱乐，不构成任何决策建议。

### 9.3 抖音内容红线
- 不说 "算命"、"占卜"、"预言"
- 不做 "一定会发生" 的绝对预测
- 不涉及 医疗建议、投资建议
- 不恐吓用户（"不看会倒霉"之类）

### 9.4 支付合规
- xorpay 商品名称用 "星座性格分析报告"，不用 "算命"
- 保留用户退款通道（7 天无理由）

---

## 10. 里程碑计划

| 阶段 | 时间 | 目标 |
|------|------|------|
| MVP 开发 | 第 1 周 | H5 上线：首页 + 免费运势 + 1 个付费报告 + 支付 |
| 内容启动 | 第 2 周 | 抖音账号启动，日更 1 条视频 |
| 产品完善 | 第 3-4 周 | 补全配对分析、年度报告、AI 对话 |
| 数据验证 | 第 2 个月 | 验证转化率，优化付费路径 |
| 规模增长 | 第 3-6 个月 | 内容提频，测试投流，优化变现模型 |
