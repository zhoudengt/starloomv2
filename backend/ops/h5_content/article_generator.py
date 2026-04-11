"""Generate H5 articles from trending hot topics + astrology angle.

Pipeline: hot keywords / RSS headlines -> match to category + zodiac angle
         -> AI-generate 800-1200 word original article -> compliance check
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.services.llm_service import BailianApplicationService

from ops.config import get_ops_settings
from ops.copy.compliance import check_compliance, strip_banned
from ops.media.wan_media import generate_h5_article_cover
from ops.data_sources.base import NewsHeadline
from ops.signals.astro_slice import ephemeris_one_liner

logger = logging.getLogger(__name__)

CATEGORY_ANGLES = {
    "career": ["职场", "工作", "升职", "面试", "跳槽", "领导", "同事", "项目", "效率", "加班", "创业"],
    "wealth": ["理财", "投资", "存钱", "消费", "薪资", "副业", "赚钱", "花钱", "省钱", "基金"],
    "relationship": ["沟通", "社交", "恋爱", "朋友", "家人", "吵架", "和好", "表白", "分手", "暧昧"],
    "energy": ["情绪", "休息", "睡眠", "压力", "焦虑", "放松", "健康", "运动", "冥想", "疲劳"],
}

CATEGORY_CTA = {
    "career": "personality_career",
    "wealth": "annual",
    "relationship": "compatibility",
    "energy": "season_pass",
}


@dataclass
class GeneratedArticle:
    slug: str
    title: str
    body: str
    category: str
    cta_product: str
    source_keywords: str
    cover_image: str


def _match_category(text: str) -> Optional[str]:
    scores: Dict[str, int] = {}
    for cat, kws in CATEGORY_ANGLES.items():
        scores[cat] = sum(1 for kw in kws if kw in text)
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] > 0:
        return best
    return None


def _pick_headline_angles(
    headlines: List[NewsHeadline],
    hot_keywords: List[str],
    max_articles: int = 3,
) -> List[Dict[str, Any]]:
    """Pick top headlines that match a content category, with deduplication by category."""
    angles: list[Dict[str, Any]] = []
    used_cats: set[str] = set()

    all_texts = [(h.title, h) for h in headlines]
    for kw in hot_keywords[:20]:
        for title, h in all_texts:
            if kw in title:
                cat = _match_category(title)
                if cat and cat not in used_cats:
                    matched_kws = [k for k in hot_keywords if k in title]
                    angles.append({
                        "headline": title,
                        "source": h.source,
                        "category": cat,
                        "matched_keywords": matched_kws[:5],
                    })
                    used_cats.add(cat)
                    if len(angles) >= max_articles:
                        return angles

    for title, h in all_texts:
        cat = _match_category(title)
        if cat and cat not in used_cats:
            angles.append({
                "headline": title,
                "source": h.source,
                "category": cat,
                "matched_keywords": [],
            })
            used_cats.add(cat)
            if len(angles) >= max_articles:
                break

    return angles


_ARTICLE_SYSTEM_PROMPT = """\
你是 StarLoom 星座内容编辑。根据给定的热点话题和天象数据，写一篇 800-1200 字的原创星座视角文章。

要求：
1. 标题：吸引点击，15-25字，包含星座关键词
2. 正文用 Markdown 格式，包含 2-3 个 ## 二级标题
3. 必须引用给定天象事实，不编造新数据
4. 融合热点话题，从星座角度给出实用建议
5. 语气：专业但亲切，像资深星座博主
6. 末尾加免责声明：「以上内容仅供参考与自我探索，不构成专业建议。」
7. 禁止使用「算命」「占卜」「必须」「一定会」

返回 JSON：
{"title": "文章标题", "body": "Markdown正文"}
"""

_COVER_IMAGES = {
    "career": "/illustrations/personality-hero.png",
    "wealth": "/illustrations/annual-hero.png",
    "relationship": "/illustrations/compatibility-home.png",
    "energy": "/illustrations/season-moon.png",
    "general": "/illustrations/astro-event.png",
}


def _slugify(title: str, d: date, idx: int) -> str:
    safe = re.sub(r'[^\w\u4e00-\u9fff]', '-', title)[:30].strip('-').lower()
    return f"{d.isoformat()}-{safe or 'article'}-{idx}"


async def generate_articles(
    d: date,
    headlines: List[NewsHeadline],
    hot_keywords: List[str],
    max_articles: int = 3,
) -> List[GeneratedArticle]:
    ops = get_ops_settings()
    settings = get_settings()

    angles = _pick_headline_angles(headlines, hot_keywords, max_articles)
    if not angles:
        logger.info("No matching headline angles found for article generation")
        return []

    if not ops.llm_enabled or not ops.bailian_app_id.strip() or not settings.bailian_api_key:
        logger.info("LLM not configured, skipping AI article generation")
        return []

    ep = ephemeris_one_liner(d)

    cal_ctx: Dict[str, Any] = {}
    try:
        from ops.data_sources.calendar_config import calendar_for_date
        from ops.config import load_calendar_yaml_path
        cal_ctx = calendar_for_date(load_calendar_yaml_path(), d)
    except Exception:
        pass
    banned = list(cal_ctx.get("banned_words") or [])

    svc = BailianApplicationService(settings, ops.bailian_app_id.strip())
    articles: list[GeneratedArticle] = []

    for idx, angle in enumerate(angles):
        user_input = (
            f"日期：{d.isoformat()}\n"
            f"天象概要：{ep}\n"
            f"热点话题：{angle['headline']}\n"
            f"关联关键词：{', '.join(angle['matched_keywords'])}\n"
            f"文章方向：{angle['category']}（{CATEGORY_ANGLES.get(angle['category'], [''])[0]}相关）"
        )

        try:
            raw = await svc.generate(f"{_ARTICLE_SYSTEM_PROMPT}\n\n{user_input}")
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if not match:
                logger.warning("Article LLM response not valid JSON for angle %s", angle["headline"])
                continue

            parsed = json.loads(match.group())
            title = str(parsed.get("title", ""))
            body = str(parsed.get("body", ""))

            if not title or not body or len(body) < 200:
                logger.warning("Article too short or missing title for: %s", angle["headline"])
                continue

            body = strip_banned(body, banned)
            cr = check_compliance(body, banned)
            if not cr.ok:
                logger.warning("Article compliance issue: %s", cr.violations)

            cat = angle["category"]
            slug = _slugify(title, d, idx)
            cover_image = _COVER_IMAGES.get(cat, _COVER_IMAGES["general"])
            if ops.wan_image_enabled:
                wan_r = await asyncio.to_thread(
                    generate_h5_article_cover,
                    settings,
                    slug=slug,
                    title=title,
                    category=cat,
                    publish_date=d,
                )
                if wan_r.get("ok") and wan_r.get("web_path"):
                    cover_image = str(wan_r["web_path"])
                else:
                    logger.warning(
                        "H5 article cover WAN failed slug=%s err=%s",
                        slug,
                        wan_r.get("error"),
                    )

            articles.append(
                GeneratedArticle(
                    slug=slug,
                    title=title,
                    body=body,
                    category=cat,
                    cta_product=CATEGORY_CTA.get(cat, "personality"),
                    source_keywords=",".join(angle["matched_keywords"]),
                    cover_image=cover_image,
                )
            )

        except Exception:
            logger.exception("Failed to generate article for: %s", angle["headline"])
            continue

    return articles
