"""从读路径异步补拉「今日」轮播 / 深析（带冷却，避免每次请求打爆 LLM）。"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_unified_last: float = 0.0
_guide_last: float = 0.0
_UNIFIED_COOLDOWN_SEC = 120.0
_GUIDE_COOLDOWN_SEC = 120.0


async def kick_unified_daily_if_needed() -> None:
    """今日尚无轮播文章时由读路径触发 run_daily；冷却内忽略。"""
    global _unified_last
    now = time.monotonic()
    if now - _unified_last < _UNIFIED_COOLDOWN_SEC:
        return
    _unified_last = now
    from app.utils.beijing_date import fortune_date_beijing

    d = fortune_date_beijing()
    try:
        from ops.pipeline import run_daily
        await run_daily(d, skip_wan_media=True)
        logger.info("kick_unified_daily ok date=%s", d)
    except Exception:
        logger.exception("kick_unified_daily failed")


async def kick_guides_for_today_if_needed() -> None:
    """今日深析未齐时由读路径触发；冷却内忽略。"""
    global _guide_last
    now = time.monotonic()
    if now - _guide_last < _GUIDE_COOLDOWN_SEC:
        return
    _guide_last = now
    from app.database import AsyncSessionLocal
    from app.services.guide_generator import generate_all_guides_for_date
    from app.utils.beijing_date import fortune_date_beijing

    d = fortune_date_beijing()
    try:
        async with AsyncSessionLocal() as db:
            n = await generate_all_guides_for_date(db, d, force=False)
            logger.info("kick_guides_for_today rows=%s date=%s", n, d)
    except Exception:
        logger.exception("kick_guides_for_today failed")
