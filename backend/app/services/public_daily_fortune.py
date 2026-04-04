"""Single code path: ensure public daily fortune exists in Redis + MySQL (optional LLM)."""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.daily_fortune import DailyFortune
from app.prompts.daily_fortune import build_daily_sign_ephemeris_stub
from app.services import cache_service
from app.services.astro_service import compute_ephemeris_snapshot_line
from app.services.daily_fortune_core import normalize_daily_payload
from app.services.llm_service import generate_json_daily
from app.utils.zodiac_calc import get_sign_meta, list_all_signs

logger = logging.getLogger(__name__)


async def ensure_public_daily_content(
    db: AsyncSession,
    sign_slug: str,
    fortune_date: date,
) -> dict[str, Any]:
    """
    Return normalized JSON for one sign + date.
    Order: Redis -> MySQL -> LLM, then write Redis + MySQL.
    Caller must commit the session (same as FastAPI get_db).
    """
    slug = sign_slug.lower().strip()
    meta = get_sign_meta(slug)
    if not meta:
        raise ValueError(f"unknown sign: {sign_slug}")

    cached = await cache_service.get_daily_cached(slug, fortune_date)
    if cached:
        return cached

    row = await db.execute(
        select(DailyFortune).where(
            DailyFortune.sign == slug,
            DailyFortune.fortune_date == fortune_date,
        )
    )
    existing = row.scalar_one_or_none()
    if existing:
        await cache_service.set_daily_cached(slug, fortune_date, existing.content)
        return existing.content

    sky = compute_ephemeris_snapshot_line(fortune_date)
    user_input = build_daily_sign_ephemeris_stub(meta["sign_cn"], fortune_date.isoformat(), sky)
    settings = get_settings()
    data = await generate_json_daily(
        settings, user_input, meta["sign_cn"], fortune_date.isoformat()
    )
    data = normalize_daily_payload(data, meta["sign_cn"], fortune_date)

    await cache_service.set_daily_cached(slug, fortune_date, data)
    stmt = mysql_insert(DailyFortune).values(
        sign=slug,
        fortune_date=fortune_date,
        content=data,
    )
    stmt = stmt.on_duplicate_key_update(content=stmt.inserted.content)
    await db.execute(stmt)
    return data


async def prefetch_all_public_daily_for_date(db: AsyncSession, fortune_date: date) -> None:
    """Used by cron: ensure all 12 signs for the given Beijing calendar day."""
    for meta in list_all_signs():
        slug = meta["sign"]
        if not get_sign_meta(slug):
            continue
        try:
            await ensure_public_daily_content(db, slug, fortune_date)
        except Exception:
            logger.exception("prefetch failed for sign=%s date=%s", slug, fortune_date)
