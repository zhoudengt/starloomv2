"""Daily Guide API — preview (free), full content (paid), access check."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, get_optional_user
from app.models.daily_guide import DailyGuide, GuideCategory
from app.models.order import Order, OrderStatus, ProductType
from app.models.user import User
from app.utils.beijing_date import fortune_date_beijing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/guide", tags=["guide"])

_CATEGORY_META: dict[str, dict[str, str]] = {
    "career": {"label": "职场星运", "icon": "briefcase"},
    "wealth": {"label": "财富密码", "icon": "coin"},
    "relationship": {"label": "人际沟通", "icon": "users"},
    "energy": {"label": "情绪能量", "icon": "moon"},
}


class GuidePreviewItem(BaseModel):
    category: str
    label: str
    icon: str
    title: str
    preview: str
    transit_basis: Optional[str] = None


class GuidePreviewResponse(BaseModel):
    date: str
    sign: str
    has_access: bool
    items: list[GuidePreviewItem]


class GuideFullResponse(BaseModel):
    category: str
    label: str
    sign: str
    date: str
    title: str
    content: str
    preview: str
    transit_basis: Optional[str] = None
    has_access: bool
    content_ir: Optional[dict[str, Any]] = None


class GuideAccessResponse(BaseModel):
    has_access: bool
    date: str


async def _check_guide_access(db: AsyncSession, user_id: int, guide_date_str: str) -> bool:
    result = await db.execute(
        select(Order).where(
            Order.user_id == user_id,
            Order.product_type == ProductType.daily_guide,
            Order.status == OrderStatus.paid,
        )
    )
    orders = result.scalars().all()
    for order in orders:
        ed = (order.extra_data or {}).get("guide_date", "")
        if ed == guide_date_str:
            return True
    return False


@router.get("/preview", response_model=GuidePreviewResponse)
async def guide_preview(
    sign: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    today = fortune_date_beijing()
    date_str = today.isoformat()
    slug = sign.lower().strip()

    has_access = False
    if user:
        has_access = await _check_guide_access(db, user.id, date_str)

    result = await db.execute(
        select(DailyGuide).where(
            DailyGuide.sign == slug,
            DailyGuide.guide_date == today,
        ).order_by(DailyGuide.category)
    )
    guides = result.scalars().all()

    items: list[GuidePreviewItem] = []
    for g in guides:
        meta = _CATEGORY_META.get(g.category.value, {})
        items.append(GuidePreviewItem(
            category=g.category.value,
            label=meta.get("label", g.category.value),
            icon=meta.get("icon", "star"),
            title=g.title,
            preview=g.preview,
            transit_basis=g.transit_basis,
        ))

    for cat_key, meta in _CATEGORY_META.items():
        if not any(i.category == cat_key for i in items):
            items.append(GuidePreviewItem(
                category=cat_key,
                label=meta["label"],
                icon=meta["icon"],
                title=f"今日{meta['label']}",
                preview="内容生成中，请稍后刷新…",
                transit_basis=None,
            ))

    items.sort(key=lambda x: list(_CATEGORY_META.keys()).index(x.category))

    return GuidePreviewResponse(
        date=date_str,
        sign=slug,
        has_access=has_access,
        items=items,
    )


@router.get("/access", response_model=GuideAccessResponse)
async def guide_access_check(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = fortune_date_beijing()
    date_str = today.isoformat()
    has_access = await _check_guide_access(db, user.id, date_str)
    return GuideAccessResponse(has_access=has_access, date=date_str)


@router.get("/{category}", response_model=GuideFullResponse)
async def guide_full(
    category: str,
    sign: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    today = fortune_date_beijing()
    date_str = today.isoformat()
    slug = sign.lower().strip()

    try:
        cat_enum = GuideCategory(category.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    meta = _CATEGORY_META.get(cat_enum.value, {})

    has_access = False
    if user:
        has_access = await _check_guide_access(db, user.id, date_str)

    result = await db.execute(
        select(DailyGuide).where(
            DailyGuide.sign == slug,
            DailyGuide.category == cat_enum,
            DailyGuide.guide_date == today,
        )
    )
    guide = result.scalar_one_or_none()

    if not guide:
        raise HTTPException(status_code=404, detail="Guide content not available yet")

    content = guide.content if has_access else ""
    content_ir: Optional[dict[str, Any]] = guide.content_ir if has_access else None

    return GuideFullResponse(
        category=cat_enum.value,
        label=meta.get("label", cat_enum.value),
        sign=slug,
        date=date_str,
        title=guide.title,
        content=content,
        preview=guide.preview,
        transit_basis=guide.transit_basis,
        has_access=has_access,
        content_ir=content_ir,
    )
