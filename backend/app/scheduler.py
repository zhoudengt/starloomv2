"""APScheduler jobs (Asia/Shanghai)."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.public_daily_fortune import prefetch_all_public_daily_for_date
from app.utils.beijing_date import BEIJING_TZ, fortune_date_beijing

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=BEIJING_TZ)


async def run_daily_prefetch_job() -> None:
    settings = get_settings()
    if not settings.daily_prefetch_enabled:
        return
    d = fortune_date_beijing()
    async with AsyncSessionLocal() as db:
        try:
            await prefetch_all_public_daily_for_date(db, d)
            await db.commit()
            logger.info("daily prefetch ok for %s (Beijing date)", d.isoformat())
        except Exception:
            await db.rollback()
            logger.exception("daily prefetch failed for %s", d.isoformat())
            raise


async def run_guide_generation_job() -> None:
    from app.services.guide_generator import generate_all_guides_for_date

    settings = get_settings()
    if not settings.guide_generation_enabled:
        return
    d = fortune_date_beijing()
    async with AsyncSessionLocal() as db:
        try:
            count = await generate_all_guides_for_date(db, d)
            await db.commit()
            logger.info("guide generation ok: %d guides for %s", count, d.isoformat())
        except Exception:
            await db.rollback()
            logger.exception("guide generation failed for %s", d.isoformat())


async def run_carousel_article_job() -> None:
    """首页轮播：热点聚合+改写短文（tags=carousel，与每日深析独立）。"""
    from app.services.article_scraper import generate_carousel_articles

    settings = get_settings()
    if not settings.carousel_generation_enabled:
        return
    d = fortune_date_beijing()
    async with AsyncSessionLocal() as db:
        try:
            n = await generate_carousel_articles(db, d)
            await db.commit()
            logger.info("carousel articles ok: %d saved for %s", n, d.isoformat())
        except Exception:
            await db.rollback()
            logger.exception("carousel article generation failed for %s", d.isoformat())


def setup_daily_prefetch_schedule() -> None:
    settings = get_settings()
    if not settings.daily_prefetch_enabled:
        logger.info("daily_prefetch_enabled=false, skip scheduler")
        return
    scheduler.add_job(
        run_daily_prefetch_job,
        CronTrigger(
            hour=settings.daily_prefetch_hour_beijing,
            minute=settings.daily_prefetch_minute_beijing,
            timezone=BEIJING_TZ,
        ),
        id="daily_prefetch_beijing",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info(
        "scheduled daily prefetch at Beijing %02d:%02d",
        settings.daily_prefetch_hour_beijing,
        settings.daily_prefetch_minute_beijing,
    )


async def run_h5_article_job() -> None:
    """Generate and publish H5 articles from external data sources + LLM."""
    settings = get_settings()
    if not settings.guide_generation_enabled:
        return
    d = fortune_date_beijing()
    try:
        from ops.pipeline import run_h5_content
        result = await run_h5_content(d, skip_articles=False)
        logger.info("h5 article generation ok for %s: %s", d.isoformat(), result)
    except Exception:
        logger.exception("h5 article generation failed for %s", d.isoformat())


def setup_guide_generation_schedule() -> None:
    settings = get_settings()
    if not settings.guide_generation_enabled:
        logger.info("guide_generation_enabled=false, skip guide scheduler")
        return
    scheduler.add_job(
        run_guide_generation_job,
        CronTrigger(
            hour=settings.guide_generation_hour_beijing,
            minute=settings.guide_generation_minute_beijing,
            timezone=BEIJING_TZ,
        ),
        id="guide_generation_beijing",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info(
        "scheduled guide generation at Beijing %02d:%02d",
        settings.guide_generation_hour_beijing,
        settings.guide_generation_minute_beijing,
    )

    scheduler.add_job(
        run_h5_article_job,
        CronTrigger(
            hour=settings.guide_generation_hour_beijing,
            minute=settings.guide_generation_minute_beijing + 5,
            timezone=BEIJING_TZ,
        ),
        id="h5_article_generation_beijing",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("scheduled h5 article generation at Beijing %02d:%02d",
                settings.guide_generation_hour_beijing,
                settings.guide_generation_minute_beijing + 5)


def setup_carousel_schedule() -> None:
    settings = get_settings()
    if not settings.carousel_generation_enabled:
        logger.info("carousel_generation_enabled=false, skip carousel scheduler")
        return
    scheduler.add_job(
        run_carousel_article_job,
        CronTrigger(
            hour=settings.carousel_generation_hour_beijing,
            minute=settings.carousel_generation_minute_beijing,
            timezone=BEIJING_TZ,
        ),
        id="carousel_articles_beijing",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info(
        "scheduled carousel articles at Beijing %02d:%02d",
        settings.carousel_generation_hour_beijing,
        settings.carousel_generation_minute_beijing,
    )
