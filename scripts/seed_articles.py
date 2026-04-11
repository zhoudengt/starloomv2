"""Seed the articles and daily_tips tables with initial data.

新插入的文章默认为 draft、无 publish_date，不参与首页 `carousel=1` 已发布池；
生产可再执行 `scripts/archive_seed_carousel_articles.py` 将历史种子标为 archived。

Usage:
    cd backend && source .venv/bin/activate
    python -m scripts.seed_articles

Or from project root:
    cd backend && .venv/bin/python ../scripts/seed_articles.py
"""

import asyncio
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select, update  # noqa: E402

from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.models.article import (  # noqa: E402
    Article,
    ArticleCategory,
    ArticleStatus,
    DailyTip,
    TipCategory,
)
from app.models.base import Base  # noqa: E402

_BJ = timezone(timedelta(hours=8))
TODAY = datetime.now(_BJ).date()

SEED_ARTICLES = [
    {
        "slug": "sun-sign-and-self",
        "title": "太阳星座与自我认知：从标签到日常习惯",
        "cover_image": "/illustrations/personality-hero-neutral.png",
        "category": ArticleCategory.general,
        "cta_product": "personality",
        "body": """许多人第一次接触星座，都是从「太阳星座」开始的。它更像一种**性格参考坐标**，帮助你观察自己在压力、社交与独处时的默认反应，而不是固定命运。

## 为什么值得当作「自我观察」工具

把星座当作语言，而不是判决。你可以对照自己的太阳星座描述，记录一周内哪些情境让你感到顺手、哪些让你耗能——这比单纯记住标签更有用。

## 三个可练习的小问题

1. 做决定时，你更依赖直觉、逻辑，还是他人反馈？
2. 疲惫时，你更想独处恢复，还是需要热闹分散注意力？
3. 被否定时，你第一反应是解释、沉默，还是转移话题？

## 与 StarLoom 报告的关系

在 StarLoom 中，个人性格报告会把出生信息与 AI 分析结合，生成可回看的章节结构；本文仅提供通用参考，帮助你建立观察框架。

以上内容仅供娱乐与自我探索，不构成任何专业建议。""",
    },
    {
        "slug": "pairing-communication",
        "title": "双人合盘之前：先搞懂沟通节奏",
        "cover_image": "/illustrations/compatibility-couple-banner.png",
        "category": ArticleCategory.relationship,
        "cta_product": "compatibility",
        "body": """配对分析常被期待成「合或不合」的答案，但更健康的使用方式，是把它当作**沟通与期待的说明书**：你们可能在哪些话题上容易误会？哪些时刻需要多一点确认？

## 合盘能参考什么

- 各自在关系里更需要的安全感来源
- 冲突时常见的表达差异（直接 vs 迂回、理性 vs 感受）
- 适合一起讨论的规则：金钱、时间、社交边界

## 相处里比分数更重要的事

再契合的组合，也需要把话说清楚。建议把「我希望你…」换成「我感受到…，如果可以…我会更安心」，降低指责感。

StarLoom 的配对报告在支付后可解锁完整章节，由 AI 流式生成，便于保存与回看。

以上内容仅供性格与关系参考，请理性对待。""",
    },
    {
        "slug": "annual-focus-habits",
        "title": "年度规划与习惯：把「运势参考」落到行动",
        "cover_image": "/illustrations/annual-hero.png",
        "category": ArticleCategory.career,
        "cta_product": "annual",
        "body": """年度运势类内容常被用来设定心理预期。更有价值的是：把「今年想强化什么」拆成**可执行的小习惯**，而不是等待某一天突然变好。

## 从三个维度做轻量规划

| 维度 | 可以问自己的问题 |
|------|------------------|
| 学习 | 今年想掌握的一项硬技能或软技能？ |
| 健康 | 睡眠、运动、情绪，哪一个最想先改善？ |
| 关系 | 想主动修复、加深，还是设立边界？ |

## 与报告搭配使用

年度运势报告适合作为「思考起点」：读完一章，写下三条下周可做的具体动作，比反复阅读更有留存价值。

以上内容仅供生活规划参考，不构成投资、医疗或法律建议。""",
    },
    {
        "slug": "astro-events-calendar",
        "title": "天象日历怎么读：关注节奏，不制造焦虑",
        "cover_image": "/illustrations/quicktest-crystal.png",
        "category": ArticleCategory.general,
        "cta_product": "astro_event",
        "body": """天象信息（如行星相位、逆行等）常被媒体简化成「水逆必翻车」。更稳妥的态度是：把它当作**节奏提示**——哪些时段适合复盘、收尾、沟通确认，而不是宿命论。

## 实用读法

- **逆行**：适合检查旧项目、备份数据、澄清误会，而非强行开新坑。
- **新月 / 满月**：可做轻量计划与复盘，不必迷信仪式。

## 与情绪的关系

若你本身容易焦虑，建议减少刷屏式运势推送，把信息源固定在一两个可信的总结即可。

StarLoom 的天象相关内容同样定位为文化参考与自我觉察，请理性使用。""",
    },
    {
        "slug": "moon-and-rest",
        "title": "情绪与休息：用「月亮」话题整理睡眠与感受",
        "cover_image": "/illustrations/chat-advisor.png",
        "category": ArticleCategory.energy,
        "cta_product": "season_pass",
        "body": """月亮在占星语境里常和情绪、安全感联系在一起。即使你不相信行星影响身体，也可以借用这个比喻：**先照顾好睡眠与身体，再谈决策质量**。

## 两个休息原则

1. **固定起床时间**比固定入睡更容易坚持。
2. 睡前一小时降低蓝光与刺激性内容，比任何「转运」都实在。

## 与产品功能的衔接

星运月卡等功能若开通，可在 App 内查看更结构化的每日参考；未开通时，也不妨碍你使用免费运势与性格分析入口。

以上内容仅供生活方式参考，如有身心困扰请咨询专业人士。""",
    },
]

SEED_TIPS = [
    {
        "category": TipCategory.career,
        "tip_text": "水星刚进入稳健的金牛区间，本周适合做长期规划而非临时决策——先把手头的优先级列清楚再行动。",
        "transit_basis": "水星过境金牛座",
        "cta_product": "personality_career",
    },
    {
        "category": TipCategory.wealth,
        "tip_text": "木星与金星形成和谐相位，消费冲动会偏高。下单前给自己 24 小时冷静期，看看明天是否还想买。",
        "transit_basis": "木星三分金星",
        "cta_product": "annual",
    },
    {
        "category": TipCategory.relationship,
        "tip_text": "火星四分相期间，表达容易带火气。开口前多停顿 3 秒，把「你怎么总是…」换成「我感觉到…」。",
        "transit_basis": "火星四分水星",
        "cta_product": "compatibility",
    },
    {
        "category": TipCategory.energy,
        "tip_text": "月亮今天进入巨蟹座，情绪感知力飙升。如果觉得累，那不是懒——是身体在提醒你充电。适合独处、早睡。",
        "transit_basis": "月亮过境巨蟹座",
        "cta_product": "season_pass",
    },
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for art_data in SEED_ARTICLES:
            existing = await session.execute(
                select(Article).where(Article.slug == art_data["slug"])
            )
            if existing.scalar_one_or_none():
                print(f"  skip (exists): {art_data['slug']}")
                continue

            article = Article(
                slug=art_data["slug"],
                title=art_data["title"],
                cover_image=art_data["cover_image"],
                body=art_data["body"],
                category=art_data["category"],
                cta_product=art_data.get("cta_product"),
                status=ArticleStatus.draft,
                publish_date=None,
            )
            session.add(article)
            print(f"  added: {art_data['slug']}")

        for tip_data in SEED_TIPS:
            existing = await session.execute(
                select(DailyTip).where(
                    DailyTip.tip_date == TODAY,
                    DailyTip.category == tip_data["category"],
                )
            )
            if existing.scalar_one_or_none():
                print(f"  skip tip (exists): {tip_data['category'].value}")
                continue

            tip = DailyTip(
                category=tip_data["category"],
                tip_text=tip_data["tip_text"],
                transit_basis=tip_data["transit_basis"],
                cta_product=tip_data["cta_product"],
                tip_date=TODAY,
            )
            session.add(tip)
            print(f"  added tip: {tip_data['category'].value}")

        for art_data in SEED_ARTICLES:
            await session.execute(
                update(Article)
                .where(Article.slug == art_data["slug"])
                .values(cover_image=art_data["cover_image"])
            )
            print(f"  sync cover: {art_data['slug']}")

        await session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
