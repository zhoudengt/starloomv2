# StarLoom v2 AI 优化方案执行计划

> 借鉴 MiroFish 项目的三个核心设计思想，结合 StarLoom 的 to-C 产品特点做轻量化落地。
> 本文档为执行蓝图，可在此基础上调整后交给 Cursor 实施。

---

## 架构借鉴来源

MiroFish 是一个多 Agent 社会模拟引擎，其核心架构有三个值得 StarLoom 借鉴的设计：

| MiroFish 设计 | 核心思想 | StarLoom 轻量化落地 |
|--------------|---------|-------------------|
| Zep 知识图谱作为共享记忆 | 所有模块读写同一个"用户世界观" | `users.ai_profile` JSON 字段 + Redis 上下文缓存 |
| ReACT 多轮报告生成 | LLM 先规划再分段查数据写内容 | 两阶段：规划 JSON → 逐章节流式撰写 |
| 模拟行为回写图谱 | 每次交互的产出沉淀为长期记忆 | 报告完成后提取标签回写用户画像 |

**不引入的部分**：Zep Cloud、LangChain/LangGraph、OASIS 模拟框架、IPC 进程通信。全部用现有技术栈（FastAPI + SQLAlchemy + Redis + 百炼）实现。

---

## 三个优化之间的依赖关系

```
优化三（用户画像积累）   ←  数据基础，其他两个都读取它
    ↓
优化一（Chat 持久记忆）  ←  读取画像 + 历史报告，组装 chat 上下文
优化二（两阶段报告）     ←  独立，可与优化一并行开发
```

三个优化共享一个基础设施改动：`users` 表新增 `ai_profile` JSON 字段。

---

## 优化一：Chat 加入持久记忆

### 现状问题

`backend/app/api/chat.py` 中：

```python
prompt = body.message.strip()
```

每次 chat 只发送用户当条消息，无任何上下文。对话记忆完全依赖百炼/Coze 平台侧（不在我方控制范围，换平台即丢失）。用户每次对话 LLM 都像"第一次认识你"。

### 目标

每次 chat 调用时，自动携带用户的星盘摘要 + 历史报告要点 + AI 画像标签，让 LLM 回答时"认识"这个用户。

### 涉及文件

| 文件 | 改动类型 |
|------|---------|
| `backend/app/models/user.py` | 修改：新增 `ai_profile` JSON 字段（与优化三共用） |
| `backend/app/database.py` | 修改：`init_db` 中补充迁移逻辑 |
| `backend/app/services/chat_context_service.py` | **新建**：上下文检索与组装 |
| `backend/app/api/chat.py` | 修改：调 LLM 前插入上下文组装 |

### 实现步骤

#### Step 1：用户模型加 `ai_profile` 字段

在 `backend/app/models/user.py` 的 `User` 类中新增：

```python
ai_profile: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
```

在 `backend/app/database.py` 的 `init_db` 中补充迁移逻辑（参照已有的 `ensure_users_birth_place_columns` 模式）：

```python
("ai_profile", "JSON NULL"),
```

#### Step 2：新建 `chat_context_service.py`

位置：`backend/app/services/chat_context_service.py`

```python
"""为 Chat 组装用户上下文，让 LLM 带着"记忆"回答问题。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.report import Report


async def build_chat_context(user: User, db: AsyncSession) -> str:
    """
    组装用户上下文，拼入 chat prompt 的前缀。
    返回空字符串时行为等同现状（无退化风险）。
    """
    parts = []

    # 1. 星盘摘要（静态，从 user 字段拼接）
    if user.sun_sign:
        parts.append(f"用户星座: {user.sun_sign}")
    if user.birth_date:
        parts.append(f"出生日期: {user.birth_date}")
    if getattr(user, 'birth_time', None):
        parts.append(f"出生时间: {user.birth_time}")

    # 2. AI 画像标签（来自优化三的回写）
    if user.ai_profile:
        tags = user.ai_profile.get("tags", [])
        if tags:
            parts.append(f"用户特征: {', '.join(tags[:10])}")
        summary = user.ai_profile.get("summary", "")
        if summary:
            parts.append(f"画像摘要: {summary[:200]}")

    # 3. 最近报告要点（取最近 3 份报告的前 150 字）
    result = await db.execute(
        select(Report)
        .where(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
        .limit(3)
    )
    recent_reports = result.scalars().all()
    if recent_reports:
        snippets = []
        for r in recent_reports:
            snippet = (r.content or "")[:150].replace("\n", " ")
            snippets.append(f"[{r.report_type.value}] {snippet}")
        parts.append("近期报告摘要:\n" + "\n".join(snippets))

    if not parts:
        return ""

    return (
        "=== 用户背景（请基于以下信息个性化回答）===\n"
        + "\n".join(parts)
        + "\n=== 用户问题 ===\n"
    )
```

#### Step 3：修改 `chat.py`

在构建 prompt 时插入上下文：

```python
from app.services.chat_context_service import build_chat_context

# 原: prompt = body.message.strip()
# 改为:
context = await build_chat_context(user, db)
prompt = context + body.message.strip()
```

### 性能影响

- `build_chat_context` 的 DB 查询（3 条 report）耗时 < 10ms
- 上下文文本约 300-500 字，不会显著增加 LLM 耗时
- 后续可将上下文缓存到 Redis（key: `chat_ctx:{user_id}`，TTL 1 小时）

### 风险与对策

| 风险 | 对策 |
|------|------|
| 百炼智能体 system prompt 与拼入的 context 格式冲突 | 测试确认百炼对长 prompt 的处理；如有问题可用分隔符标记 |
| 用户没有报告和画像数据 | context 返回空字符串，行为等同现状，零退化 |
| context 过长影响 LLM 质量 | 硬限制总 context < 800 字，超出则优先保留 tags 和 summary |

---

## 优化二：报告两阶段生成（轻量 ReACT）

### 现状问题

`backend/app/api/constellation.py` 报告生成流程：

```
build_*_user_input()  →  一次性塞入完整 natal_chart（30+ 条数据）→  stream_with_fallback()  →  一口气写完
```

LLM 一次收到几十条星盘数据，要同时记住所有行星位置、宫位、相位，然后写 2000 字报告。信息越多，LLM 越容易"泛泛而谈"或漏掉重要配置。

### 设计思路

**不是多个智能体**，是**同一个 LLM 分两步走**：

1. **规划阶段**（3-5 秒，非流式）：LLM 看完整星盘 → 输出 JSON 大纲（选出每章要聚焦的关键数据）
2. **撰写阶段**（20-25 秒，流式）：逐章节只给 LLM 精选的 3-5 条数据 → 深入撰写

```
                    ┌─────────────────────────────┐
                    │  完整星盘数据 (30+ 条)         │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  阶段1: LLM 输出 JSON 大纲     │  ← 3-5 秒，不流式
                    │  "核心性格要用太阳+水星+火星"    │
                    │  "情感模式要用金星+月亮+7宫"     │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ 章节1: 核心性格    │  │ 章节2: 情感模式    │  │ 章节3: 事业方向    │
    │ 只看太阳+水星+火星 │  │ 只看金星+月亮+7宫  │  │ 只看MC+土星+10宫  │
    │ → 深入写 400 字   │  │ → 深入写 400 字   │  │ → 深入写 400 字   │
    └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
             │                    │                    │
             ▼                    ▼                    ▼
           流式推送             流式推送             流式推送
```

### 为什么不做完整 ReACT 循环

| 方案 | LLM 调用次数 | 耗时 | 适用场景 |
|------|-------------|------|---------|
| 完整 ReACT（MiroFish 方式，8 轮） | 8-10 次 | 60-90 秒 | 离线分析报告 |
| **两阶段（推荐）** | **5-7 次** | **25-40 秒** | **付费实时报告** |
| 一次性（现状） | 1 次 | 15-30 秒 | 最快但质量有限 |

两阶段总耗时与现状接近（最坏多 10 秒），但用户看到文字分段出现，**感知等待时间反而更短**。

### 涉及文件

| 文件 | 改动类型 |
|------|---------|
| `backend/app/prompts/report_plan_prompt.py` | **新建**：规划阶段 prompt 模板 |
| `backend/app/services/report_planner.py` | **新建**：两阶段生成逻辑 |
| `backend/app/api/constellation.py` | 修改：报告路由改用两阶段 |
| `backend/app/services/llm_service.py` | 不改动，复用现有接口 |

### 实现步骤

#### Step 1：新建规划阶段 prompt

位置：`backend/app/prompts/report_plan_prompt.py`

```python
"""阶段 1 的 prompt：让 LLM 规划报告大纲而非直接写正文。"""

PLAN_SYSTEM_INSTRUCTION = """你是星座分析规划师。根据用户星盘数据，输出 JSON 格式的报告大纲。
每个章节标注：标题、要引用的关键星盘数据（直接摘抄原始数据行）、分析角度。
不要写正文，只输出 JSON 结构。"""

SECTION_HINTS = {
    "personality": "核心性格, 情感模式, 思维方式, 社交风格, 潜在挑战, 成长建议",
    "compatibility": "整体契合度, 沟通模式, 情感互动, 冲突点, 相处建议",
    "annual": "年度主题, 事业运势, 感情运势, 财运健康, 关键月份, 年度建议",
}

def build_plan_prompt(report_type: str, natal_chart_text: str) -> str:
    hints = SECTION_HINTS.get(report_type, "综合分析, 重点解读, 建议")
    return f"""{PLAN_SYSTEM_INSTRUCTION}

报告类型: {report_type}
建议章节方向: {hints}

星盘数据:
{natal_chart_text}

请输出 JSON，格式:
{{
  "sections": [
    {{
      "title": "章节标题",
      "key_data": "本章要引用的 2-4 条关键星盘数据（直接摘抄上面的数据行）",
      "angle": "分析角度/切入点（一句话）"
    }}
  ]
}}"""
```

#### Step 2：新建两阶段生成服务

位置：`backend/app/services/report_planner.py`

```python
"""两阶段报告生成：规划 → 逐章节撰写。"""

import json
import re
import logging
from typing import AsyncGenerator, Optional
from app.services.llm_service import BaseLLMService

logger = logging.getLogger(__name__)


async def two_stage_report(
    llm: BaseLLMService,
    plan_prompt: str,
    report_type: str,
    fallback_full_prompt: str,
) -> AsyncGenerator[str, None]:
    """
    两阶段报告生成。
    规划阶段失败时自动回退到一次性生成（与现状一致），零退化风险。
    """
    # --- 阶段 1：规划（非流式，后端内部调用） ---
    plan = None
    try:
        plan_text = await llm.generate(plan_prompt)
        plan = _parse_plan(plan_text)
    except Exception as e:
        logger.warning("Report plan failed, falling back: %s", e)

    if not plan:
        async for chunk in llm.stream_generate(fallback_full_prompt):
            yield chunk
        return

    # --- 阶段 2：逐章节流式撰写 ---
    written_titles = []
    for i, section in enumerate(plan):
        context_hint = ""
        if written_titles:
            context_hint = f"\n已完成的章节: {', '.join(written_titles)}。请勿重复上述内容。\n"

        section_prompt = (
            f"请撰写星座报告的「{section['title']}」章节。\n"
            f"{context_hint}\n"
            f"关键星盘数据:\n{section['key_data']}\n\n"
            f"分析角度: {section['angle']}\n\n"
            f"要求: 深入分析，400-600字，语气温暖专业，引用具体星盘数据。"
            f"直接输出正文，以 Markdown 二级标题开头。"
        )
        async for chunk in llm.stream_generate(section_prompt):
            yield chunk
        written_titles.append(section["title"])
        if i < len(plan) - 1:
            yield "\n\n"


def _parse_plan(text: str) -> Optional[list[dict]]:
    """从 LLM 输出中提取 JSON 大纲。解析失败返回 None。"""
    try:
        data = json.loads(text)
        sections = data.get("sections")
        if sections and isinstance(sections, list):
            return sections
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            data = json.loads(m.group())
            sections = data.get("sections")
            if sections and isinstance(sections, list):
                return sections
        except json.JSONDecodeError:
            pass
    return None
```

#### Step 3：修改 constellation.py 报告路由

以 `report_personality` 为例，将 `gen()` 内部改为：

```python
from app.services.report_planner import two_stage_report
from app.prompts.report_plan_prompt import build_plan_prompt
from app.prompts.chart_formatter import format_natal_chart_for_prompt

async def gen() -> AsyncGenerator[str, None]:
    full: list[str] = []
    try:
        plan_prompt = build_plan_prompt(
            "personality",
            format_natal_chart_for_prompt(natal) if natal else user_input,
        )
        async for chunk in two_stage_report(
            llm=primary,
            plan_prompt=plan_prompt,
            report_type="personality",
            fallback_full_prompt=user_input,
        ):
            full.append(chunk)
            yield sse_line({"type": "content", "text": chunk})
    except Exception:
        text = fallback_static_text()
        full.append(text)
        yield sse_line({"type": "content", "text": text})
    content = "".join(full)
    await _save_report(db, user.id, order.order_id, ReportType.personality, sign, {...}, report_id, content)
    yield sse_line({"type": "done", "report_id": report_id})
```

### 应用范围

| 报告类型 | 是否应用 | 理由 |
|---------|---------|------|
| `personality` | 是 | 数据最丰富，收益最大 |
| `compatibility` | 是 | 双人星盘数据量大，拆分后更清晰 |
| `annual` | 是 | 篇幅长，适合分章节 |
| `personality-dlc` | 可选 | 已是单主题，收益较小 |
| `astro-event` | 可选 | 通常较短，不一定需要 |

### 性能预估

| 阶段 | LLM 调用 | 耗时 | 输出量 |
|------|---------|------|-------|
| 规划 | 1 次 `generate` | 3-5 秒 | ~200 字 JSON |
| 撰写 | 4-6 次 `stream_generate` | 每章 4-6 秒 | 每章 400-600 字 |
| **总计** | **5-7 次** | **25-40 秒** | **2000-3000 字** |

### 回退机制

规划阶段任何异常（JSON 解析失败、LLM 超时等）→ 自动回退到原来的一次性 prompt。用户无感知，零退化风险。

### 风险与对策

| 风险 | 对策 |
|------|------|
| 百炼 system prompt 为"写报告"，规划阶段要输出 JSON | 在百炼控制台新建一个"规划用"应用，或在 prompt 中强调 JSON 格式要求 |
| 章节间内容重复 | 每章 prompt 带入已写章节标题列表（代码中 `written_titles`） |
| 总耗时增加 | 最坏多 10 秒，但用户看到分段出现文字，感知等待时间更短 |

---

## 优化三：用户画像渐进式积累

### 现状问题

用户数据仅限 `users` 表的静态字段（birth_date, sun_sign 等）。报告生成后内容存入 `reports.content`，但**再也不被任何流程读取**——下次生成报告或 chat 时，LLM 对这个用户的了解为零。

### 目标

每次报告生成完成后，用一个轻量 LLM 调用提取关键标签和摘要，写入 `users.ai_profile`。后续报告和 chat 可读取该画像，实现"越用越懂你"。

### `ai_profile` JSON 结构设计

```json
{
  "tags": ["直觉型思考者", "重视伴侣关系", "审美敏感", "职场变动期"],
  "summary": "太阳双鱼第十二宫，直觉力强，配合上升处女的细腻...",
  "dominant_traits": {
    "element": "水象主导",
    "modality": "变动为主",
    "key_placements": "太阳12宫, 月亮5宫, 金星8宫"
  },
  "report_insights": [
    {"type": "personality", "date": "2025-06-01", "insight": "内在冲突来自火星四分太阳"},
    {"type": "annual", "date": "2025-07-15", "insight": "2025下半年土星过境利于职业沉淀"}
  ],
  "updated_at": "2025-07-15T10:30:00"
}
```

### 涉及文件

| 文件 | 改动类型 |
|------|---------|
| `backend/app/models/user.py` | 修改：`ai_profile` 字段（与优化一共用，只加一次） |
| `backend/app/services/profile_extractor.py` | **新建**：从报告内容中提取标签 |
| `backend/app/api/constellation.py` | 修改：报告保存后触发画像更新 |

### 实现步骤

#### Step 1：新建 `profile_extractor.py`

位置：`backend/app/services/profile_extractor.py`

```python
"""从报告内容中提取用户画像标签，实现"越用越懂你"。"""

import json
import re
import logging
from datetime import datetime
from typing import Optional

from app.services.llm_service import BaseLLMService

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """从以下星座分析报告中提取用户画像关键信息。

报告类型: {report_type}
报告内容（节选）:
{content}

请输出 JSON，格式:
{{
  "tags": ["3-5个性格/行为标签，简短精炼"],
  "insight": "一句话核心洞察（30字内）"
}}

只输出 JSON，不要其他内容。"""


async def extract_profile_from_report(
    llm: BaseLLMService,
    report_type: str,
    content: str,
) -> Optional[dict]:
    """从报告内容中提取画像标签。截取前 1500 字以控制成本和速度。"""
    truncated = content[:1500]
    prompt = EXTRACT_PROMPT.format(report_type=report_type, content=truncated)
    try:
        raw = await llm.generate(prompt)
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group())
    except Exception as e:
        logger.warning("Profile extraction failed: %s", e)
    return None


def merge_profile(existing: Optional[dict], new_extraction: dict, report_type: str) -> dict:
    """将新提取的画像信息合并到已有画像中（增量式，不覆盖）。"""
    profile = existing.copy() if existing else {
        "tags": [], "summary": "", "report_insights": []
    }

    # 合并 tags（去重，保留最近的 15 个）
    new_tags = new_extraction.get("tags", [])
    all_tags = new_tags + profile.get("tags", [])
    seen = set()
    unique_tags = []
    for t in all_tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)
    profile["tags"] = unique_tags[:15]

    # 追加 insight（最多保留 10 条历史）
    insight = new_extraction.get("insight", "")
    if insight:
        insights = profile.get("report_insights", [])
        insights.insert(0, {
            "type": report_type,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "insight": insight,
        })
        profile["report_insights"] = insights[:10]

    profile["updated_at"] = datetime.utcnow().isoformat()
    return profile
```

#### Step 2：报告保存后触发画像更新

在 `constellation.py` 中新增一个辅助函数，在每个报告的 `_save_report` 之后调用：

```python
from app.services.profile_extractor import extract_profile_from_report, merge_profile
from app.database import AsyncSessionLocal

async def _update_user_profile_background(
    user_id: int,
    report_type: str,
    content: str,
    settings,
):
    """后台任务：从报告提取画像标签并回写。不阻塞 SSE，失败静默。"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return

            llm = LLMServiceFactory.for_daily(settings)
            extraction = await extract_profile_from_report(llm, report_type, content)
            if extraction:
                merged = merge_profile(user.ai_profile, extraction, report_type)
                user.ai_profile = merged
                session.add(user)
                await session.commit()
    except Exception as e:
        logger.warning("Background profile update failed: %s", e)
```

在每个报告 `gen()` 函数中，`_save_report` 之后、`yield done` 之前：

```python
import asyncio

asyncio.create_task(
    _update_user_profile_background(user.id, "personality", content, settings)
)
yield sse_line({"type": "done", "report_id": report_id})
```

### 数据消费方

| 消费方 | 读取字段 | 用途 |
|--------|---------|------|
| Chat 上下文（优化一） | `ai_profile.tags` + `ai_profile.summary` | 让 chat 回答个性化 |
| 报告规划（优化二） | 可选读取 `ai_profile.dominant_traits` | 规划阶段可参考已知用户特征 |
| 未来：个性化推荐 | `ai_profile.tags` | 根据用户特征推荐相关报告或内容 |
| 未来：复购引导 | `ai_profile.report_insights` | 基于已有洞察推荐深入分析方向 |

### 数据增长控制策略

`ai_profile` 是一个 JSON 字段，需要防止随用户使用时间增长而膨胀或质量退化。

#### 已有的硬上限

| 字段 | 上限 | 当前控制方式 |
|------|------|------------|
| `tags` | 15 个 | `merge_profile` 中 `unique_tags[:15]` |
| `report_insights` | 10 条 | `insights[:10]` |
| `summary` | 200 字 | 被 `build_chat_context` 读取时截断 |

整个 `ai_profile` JSON 的最大体积约 **2-3 KB**，不会无限增长。

#### 需要额外处理的问题：旧数据过时

用户半年前的标签可能已不准确（比如"职场变动期"在当时有效，半年后已稳定）。解决方式：

**方案 A：新标签覆盖旧标签（推荐，零额外成本）**

修改 `merge_profile` 的 tags 合并逻辑，**新提取的标签放在前面**，超出上限时**淘汰最旧的**：

```python
def merge_profile(existing: Optional[dict], new_extraction: dict, report_type: str) -> dict:
    profile = existing.copy() if existing else {
        "tags": [], "summary": "", "report_insights": []
    }

    # 新 tags 在前，旧 tags 在后 → 超出上限时旧的被自然淘汰
    new_tags = new_extraction.get("tags", [])
    old_tags = profile.get("tags", [])
    all_tags = new_tags + old_tags
    seen = set()
    unique_tags = []
    for t in all_tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)
    profile["tags"] = unique_tags[:15]  # 新的优先保留，旧的超限丢弃

    # insights 同理：新的在前，超过 10 条丢弃最旧的
    insight = new_extraction.get("insight", "")
    if insight:
        insights = profile.get("report_insights", [])
        insights.insert(0, {
            "type": report_type,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "insight": insight,
        })
        profile["report_insights"] = insights[:10]

    profile["updated_at"] = datetime.utcnow().isoformat()
    return profile
```

这样用户每次新报告生成后，**新标签自然挤掉最旧的标签**。无需额外定时任务。

**方案 B：过期淘汰（适合日活较高的阶段）**

如果未来需要更精确的时效控制，可在 tags 中带上时间戳：

```python
# tags 从 ["直觉型"] 变为 [{"tag": "直觉型", "at": "2025-06-01"}, ...]
# 读取时过滤掉超过 90 天的旧标签
```

**当前阶段用方案 A 即可**，代码已经自带这个行为。方案 B 等用户量上来后按需追加。

#### Chat 上下文（优化一）的增长控制

`build_chat_context` 本身不存储数据，每次实时查询组装。增长点全在它的数据源：

| 数据源 | 增长情况 | 控制方式 |
|--------|---------|---------|
| `reports` 表 | 随用户购买报告增长 | 查询时 `LIMIT 3`，只取最近 3 条 |
| `ai_profile` JSON | 受上述硬上限控制 | tags ≤ 15，insights ≤ 10 |
| 组装后的 context 文本 | — | 硬限制 ≤ 800 字，超出则优先保留 tags |

增加一个安全截断：

```python
async def build_chat_context(user: User, db: AsyncSession) -> str:
    # ... 组装 parts ...

    context = "\n".join(parts)
    # 硬限制：超过 800 字只保留前 800 字
    if len(context) > 800:
        context = context[:800] + "\n..."

    return (
        "=== 用户背景 ===\n" + context + "\n=== 用户问题 ===\n"
    )
```

#### 总结

| 问题 | 结论 |
|------|------|
| ai_profile 会无限增长吗 | 不会。tags ≤ 15，insights ≤ 10，总体 ≤ 3KB |
| 旧标签会过时吗 | 会，但新标签自然覆盖旧标签（FIFO 淘汰） |
| chat context 会越来越长吗 | 不会。reports 查询 LIMIT 3，context 硬限 800 字 |
| reports 表本身会增长吗 | 会，但这是正常业务数据，与优化方案无关 |

### 性能影响

- 画像提取是**后台异步任务**（`asyncio.create_task`），不影响 SSE 流式响应
- 提取 prompt 只取报告前 1500 字，LLM 调用耗时 < 3 秒
- 每次报告生成只多一次轻量 LLM 调用，成本可忽略

### 风险与对策

| 风险 | 对策 |
|------|------|
| `asyncio.create_task` 在请求结束后可能拿不到注入的 DB session | 在 task 内用 `AsyncSessionLocal()` 自建 session（代码已体现） |
| 两份报告同时完成可能并发写入 `ai_profile` 互相覆盖 | 生产环境可加 Redis 锁 `profile_lock:{user_id}`，TTL 10s |
| LLM 提取的标签质量不稳定 | `merge_profile` 是增量式的，新标签优先保留，旧标签自然淘汰 |
| 旧标签不再准确 | 方案 A（新覆盖旧）默认生效；方案 B（带时间戳过期淘汰）按需追加 |

---

## 实施顺序

```
Phase 1 — 基础设施（0.5h）
  └── users 表加 ai_profile JSON 字段 + 迁移脚本
      涉及: user.py, database.py

Phase 2 — 优化三：画像积累（2-3h）
  ├── 新建 profile_extractor.py
  ├── constellation.py 报告保存后触发异步提取
  └── 验证: 生成一份报告后查 SELECT ai_profile FROM users WHERE id=X

Phase 3 — 优化一：Chat 记忆（1-2h）
  ├── 新建 chat_context_service.py
  ├── 修改 chat.py
  └── 验证: chat 时检查发给 LLM 的 prompt 是否包含用户上下文

Phase 4 — 优化二：两阶段报告（3-4h）
  ├── 新建 report_plan_prompt.py
  ├── 新建 report_planner.py
  ├── 修改 constellation.py 的 personality 路由（先改一个验证效果）
  ├── 验证: 对比新旧报告的深度和具体性
  └── 推广到 compatibility / annual
```

**总预估: 7-10 小时开发 + 测试。**

---

## 验收标准

| 优化项 | 验收方式 |
|--------|---------|
| Chat 持久记忆 | 生成过性格报告的用户 chat 时，LLM 回答引用了用户的星盘特征（如"你的太阳双鱼..."） |
| 两阶段报告 | 性格报告每个章节有具体星盘数据引用（如"你的金星落在天蝎座第八宫"），而非泛泛而谈 |
| 用户画像 | 生成报告后查 `SELECT ai_profile FROM users WHERE id=X`，JSON 中有 tags 和 insights |
| 回退安全 | 断开 LLM 规划功能后，报告仍能正常生成（回退到一次性模式） |

---

## 新增文件清单

| 文件路径 | 对应优化 | 职责 |
|---------|---------|------|
| `backend/app/services/chat_context_service.py` | 优化一 | 为 chat 组装用户上下文 |
| `backend/app/services/report_planner.py` | 优化二 | 两阶段报告生成逻辑 |
| `backend/app/prompts/report_plan_prompt.py` | 优化二 | 规划阶段 prompt 模板 |
| `backend/app/services/profile_extractor.py` | 优化三 | 报告画像提取与合并 |

## 修改文件清单

| 文件路径 | 改动点 |
|---------|-------|
| `backend/app/models/user.py` | 新增 `ai_profile` JSON 字段 |
| `backend/app/database.py` | `init_db` 中补充 `ai_profile` 列迁移 |
| `backend/app/api/chat.py` | 调 LLM 前插入 `build_chat_context` |
| `backend/app/api/constellation.py` | 报告路由改用 `two_stage_report` + 保存后触发 `_update_user_profile_background` |
