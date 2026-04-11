"""Shared helpers for constellation sub-routers."""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.order import Order, OrderStatus, ProductType
from app.models.report import Report, ReportType
from app.models.user import User
from app.services.growth_helpers import grant_zodiac_card_if_needed
from app.services.ir_converter import markdown_to_ir
from app.services.llm_service import LLMServiceFactory
from app.services.profile_extractor import extract_profile_from_report, merge_profile

logger = logging.getLogger(__name__)


def natal_for_user(
    user: Optional[User],
    bd: date,
    birth_time_override: Optional[str] = None,
    place_name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    tz: Optional[str] = None,
):
    from app.services.astro_service import (
        merge_birth_time,
        merge_chart_location,
        safe_compute_natal_chart,
    )

    pn, la, lo, tz_s = merge_chart_location(user, place_name, lat, lon, tz)
    bt = merge_birth_time(user, birth_time_override)
    return safe_compute_natal_chart(
        birth_date=bd,
        birth_time=bt,
        birth_place_name=pn,
        lat=la,
        lon=lo,
        tz_str=tz_s,
    )


async def resolve_paid_order(
    db: AsyncSession,
    user: User,
    order_id: Optional[str],
    product: ProductType,
) -> Order:
    if not order_id or not str(order_id).strip():
        raise HTTPException(status_code=400, detail="order_id required")
    result = await db.execute(
        select(Order).where(
            Order.order_id == order_id.strip(),
            Order.user_id == user.id,
            Order.product_type == product,
        )
    )
    order = result.scalar_one_or_none()
    if not order or order.status != OrderStatus.paid:
        raise HTTPException(status_code=402, detail="Payment required or invalid order")
    return order


async def save_report(
    db: AsyncSession,
    user_id: int,
    order_id: str,
    rtype: ReportType,
    sign: str,
    input_data: dict,
    content: str,
    report_id: str,
) -> None:
    content_ir = markdown_to_ir(content, {})
    rep = Report(
        report_id=report_id,
        user_id=user_id,
        order_id=order_id,
        report_type=rtype,
        sign=sign,
        input_data=input_data,
        content=content,
        content_ir=content_ir,
    )
    db.add(rep)
    await db.flush()
    if rtype in (
        ReportType.personality,
        ReportType.personality_career,
        ReportType.personality_love,
        ReportType.personality_growth,
    ):
        await grant_zodiac_card_if_needed(db, user_id, sign)


async def update_user_profile_background(
    user_id: int,
    report_type: str,
    content: str,
) -> None:
    try:
        settings = get_settings()
        llm = LLMServiceFactory.for_profile_extractor(settings)
        extraction = await extract_profile_from_report(llm, report_type, content)
        if not extraction:
            return
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            merged = merge_profile(user.ai_profile, extraction, report_type)
            user.ai_profile = merged
            session.add(user)
            await session.commit()
    except Exception as e:
        logger.warning("Background profile update failed: %s", e)


def schedule_profile_update(user_id: int, report_type: str, content: str) -> None:
    asyncio.create_task(update_user_profile_background(user_id, report_type, content))
