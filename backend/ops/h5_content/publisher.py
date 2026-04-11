"""Publish generated articles and tips to the MySQL database."""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.article import (
    Article,
    ArticleCategory,
    ArticleStatus,
    DailyTip,
    TipCategory,
)

from ops.h5_content.article_generator import GeneratedArticle
from ops.h5_content.tip_generator import GeneratedTip

logger = logging.getLogger(__name__)

_CAT_MAP = {
    "career": ArticleCategory.career,
    "wealth": ArticleCategory.wealth,
    "relationship": ArticleCategory.relationship,
    "energy": ArticleCategory.energy,
    "general": ArticleCategory.general,
}

_TIP_CAT_MAP = {
    "career": TipCategory.career,
    "wealth": TipCategory.wealth,
    "relationship": TipCategory.relationship,
    "energy": TipCategory.energy,
}


async def publish_tips(tips: list[GeneratedTip], d: date) -> int:
    """Write daily tips to DB. Returns count of newly inserted tips."""
    count = 0
    async with AsyncSessionLocal() as session:
        for tip in tips:
            tc = _TIP_CAT_MAP.get(tip.category)
            if not tc:
                continue

            existing = await session.execute(
                select(DailyTip).where(
                    DailyTip.tip_date == d,
                    DailyTip.category == tc,
                )
            )
            if existing.scalar_one_or_none():
                continue

            session.add(
                DailyTip(
                    category=tc,
                    tip_text=tip.tip_text,
                    transit_basis=tip.transit_basis,
                    cta_product=tip.cta_product,
                    tip_date=d,
                )
            )
            count += 1

        await session.commit()
    logger.info("Published %d new tips for %s", count, d.isoformat())
    return count


async def publish_articles(articles: list[GeneratedArticle], d: date) -> int:
    """Write articles to DB. Returns count of newly inserted articles."""
    count = 0
    async with AsyncSessionLocal() as session:
        for art in articles:
            existing = await session.execute(
                select(Article).where(Article.slug == art.slug)
            )
            if existing.scalar_one_or_none():
                logger.debug("Skipping duplicate slug: %s", art.slug)
                continue

            cat = _CAT_MAP.get(art.category, ArticleCategory.general)
            session.add(
                Article(
                    slug=art.slug,
                    title=art.title,
                    cover_image=art.cover_image,
                    body=art.body,
                    category=cat,
                    cta_product=art.cta_product,
                    status=ArticleStatus.published,
                    source_keywords=art.source_keywords,
                    publish_date=d,
                )
            )
            count += 1

        await session.commit()
    logger.info("Published %d new articles for %s", count, d.isoformat())
    return count


async def run_h5_publish(
    tips: list[GeneratedTip],
    articles: list[GeneratedArticle],
    d: date,
) -> dict:
    """Convenience wrapper: publish both tips and articles."""
    tip_count = await publish_tips(tips, d)
    art_count = await publish_articles(articles, d)
    return {
        "date": d.isoformat(),
        "tips_published": tip_count,
        "articles_published": art_count,
    }
