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
