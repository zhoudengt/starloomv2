"""Content API: articles & daily practical tips."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.services.article_scraper import CAROUSEL_TAG
from app.services.daily_generation_kick import kick_carousel_for_today_if_needed
from app.utils.beijing_date import fortune_date_beijing
from app.models.article import (
    Article,
    ArticleCategory,
    ArticleStatus,
    DailyTip,
    TipCategory,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["content"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ArticleBrief(BaseModel):
    id: int
    slug: str
    title: str
    cover_image: str
    category: str
    cta_product: Optional[str] = None
    publish_date: Optional[date] = None
    view_count: int = 0
    subtitle: Optional[str] = None
    reading_minutes: Optional[int] = None


class ArticleDetail(ArticleBrief):
    body: str
    tags: Optional[str] = None
    body_ir: Optional[dict[str, Any]] = None


class TipItem(BaseModel):
    id: int
    category: str
    tip_text: str
    transit_basis: Optional[str] = None
    cta_product: str
    tip_date: date

    category_label: str = ""
    category_icon: str = ""


_CATEGORY_META: dict[str, tuple[str, str]] = {
    "career": ("职场星运", "briefcase"),
    "wealth": ("财富密码", "coins"),
    "relationship": ("人际沟通", "users"),
    "energy": ("情绪能量", "moon"),
}


class TipsResponse(BaseModel):
    date: date
    tips: list[TipItem]


class ArticlesResponse(BaseModel):
    items: list[ArticleBrief]
    total: int
    # carousel=1 时：today=北京当日；yesterday=无当日则用昨日发文；fallback=更早窗口；empty=无匹配
    carousel_source: Optional[str] = None


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------

def _article_brief_from_row(a: Article) -> ArticleBrief:
    """Subtitle / reading time from IR meta when present."""
    subtitle: Optional[str] = None
    reading_minutes: Optional[int] = None
    ir = getattr(a, "body_ir", None)
    if isinstance(ir, dict):
        meta = ir.get("meta") or {}
        if isinstance(meta, dict):
            subtitle = meta.get("subtitle") if isinstance(meta.get("subtitle"), str) else None
            rm = meta.get("reading_minutes")
            if isinstance(rm, int):
                reading_minutes = rm
    return ArticleBrief(
        id=a.id,
        slug=a.slug,
        title=a.title,
        cover_image=a.cover_image,
        category=a.category.value,
        cta_product=a.cta_product,
        publish_date=a.publish_date,
        view_count=a.view_count,
        subtitle=subtitle,
        reading_minutes=reading_minutes,
    )


def _category_filter(category: Optional[str]) -> Optional[ArticleCategory]:
    if not category:
        return None
    try:
        return ArticleCategory(category)
    except ValueError:
        return None


@router.get("/articles", response_model=ArticlesResponse)
async def list_articles(
    background_tasks: BackgroundTasks,
    category: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    carousel: int = Query(0, ge=0, le=1, description="1=首页轮播：优先北京当日已发布，否则回退窗口"),
    db: AsyncSession = Depends(get_db),
):
    cat_enum = _category_filter(category)
    base_pub = Article.status == ArticleStatus.published
    if cat_enum is not None:
        base_pub = and_(base_pub, Article.category == cat_enum)

    if not carousel:
        q = select(Article).where(base_pub)
        count_q = select(func.count(Article.id)).where(base_pub)
        q = q.order_by(Article.publish_date.desc(), Article.id.desc())
        q = q.offset(offset).limit(limit)
        result = await db.execute(q)
        articles = result.scalars().all()
        total_result = await db.execute(count_q)
        total = int(total_result.scalar_one() or 0)
        return ArticlesResponse(
            items=[_article_brief_from_row(a) for a in articles],
            total=total,
            carousel_source=None,
        )

    settings = get_settings()
    today = fortune_date_beijing()
    yesterday = today - timedelta(days=1)
    since = today - timedelta(days=settings.article_carousel_fallback_days)

    # 首页轮播：仅展示 tags=carousel 的管线文章（与 article_scraper 写入一致）
    base_carousel = and_(base_pub, Article.tags == CAROUSEL_TAG)

    cond_today = and_(base_carousel, Article.publish_date == today)
    count_today = await db.scalar(select(func.count(Article.id)).where(cond_today)) or 0
    if count_today > 0:
        q = (
            select(Article)
            .where(cond_today)
            .order_by(Article.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(q)
        articles = result.scalars().all()
        return ArticlesResponse(
            items=[_article_brief_from_row(a) for a in articles],
            total=int(count_today),
            carousel_source="today",
        )

    # 无今日：异步补拉今日轮播（冷却内合并为一次）
    background_tasks.add_task(kick_carousel_for_today_if_needed)

    cond_yesterday = and_(base_carousel, Article.publish_date == yesterday)
    count_y = await db.scalar(select(func.count(Article.id)).where(cond_yesterday)) or 0
    if count_y > 0:
        q = (
            select(Article)
            .where(cond_yesterday)
            .order_by(Article.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(q)
        articles = result.scalars().all()
        return ArticlesResponse(
            items=[_article_brief_from_row(a) for a in articles],
            total=int(count_y),
            carousel_source="yesterday",
        )

    cond_fb = and_(
        base_carousel,
        Article.publish_date.isnot(None),
        Article.publish_date >= since,
        Article.publish_date < today,
    )
    count_fb = await db.scalar(select(func.count(Article.id)).where(cond_fb)) or 0
    if count_fb > 0:
        q = (
            select(Article)
            .where(cond_fb)
            .order_by(Article.publish_date.desc(), Article.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(q)
        articles = result.scalars().all()
        return ArticlesResponse(
            items=[_article_brief_from_row(a) for a in articles],
            total=int(count_fb),
            carousel_source="fallback",
        )

    return ArticlesResponse(items=[], total=0, carousel_source="empty")


def _article_readable_status():
    """列表/轮播仅 published；详情允许 archived 深链（不出现在轮播但仍可阅读）。"""
    return or_(
        Article.status == ArticleStatus.published,
        Article.status == ArticleStatus.archived,
    )


@router.get("/articles/{slug}", response_model=ArticleDetail)
async def get_article(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article).where(Article.slug == slug, _article_readable_status())
    )
    article = result.scalar_one_or_none()
    if not article:
        from fastapi import HTTPException
        raise HTTPException(404, "文章不存在")

    await db.execute(
        update(Article).where(Article.id == article.id).values(view_count=Article.view_count + 1)
    )

    brief = _article_brief_from_row(article)
    return ArticleDetail(
        **brief.model_dump(),
        body=article.body,
        tags=article.tags,
        body_ir=article.body_ir,
    )


# ---------------------------------------------------------------------------
# Daily Tips
# ---------------------------------------------------------------------------

@router.get("/tips/today", response_model=TipsResponse)
async def get_today_tips(db: AsyncSession = Depends(get_db)):
    today = fortune_date_beijing()

    result = await db.execute(
        select(DailyTip)
        .where(DailyTip.tip_date == today)
        .order_by(DailyTip.category)
    )
    tips = result.scalars().all()

    if not tips:
        result = await db.execute(
            select(DailyTip)
            .where(DailyTip.tip_date < today)
            .order_by(DailyTip.tip_date.desc())
            .limit(4)
        )
        tips = result.scalars().all()

    items: list[TipItem] = []
    for t in tips:
        label, icon = _CATEGORY_META.get(t.category.value, ("", ""))
        items.append(
            TipItem(
                id=t.id,
                category=t.category.value,
                tip_text=t.tip_text,
                transit_basis=t.transit_basis,
                cta_product=t.cta_product,
                tip_date=t.tip_date,
                category_label=label,
                category_icon=icon,
            )
        )

    return TipsResponse(date=today, tips=items)


# ---------------------------------------------------------------------------
# Share links
# ---------------------------------------------------------------------------

class ShareLinkResponse(BaseModel):
    url: str
    title: str
    description: str


@router.get("/articles/{slug}/share", response_model=ShareLinkResponse)
async def get_article_share_link(
    slug: str,
    source: str = Query("direct", description="share source: wechat, douyin, weibo, direct"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Article).where(Article.slug == slug, _article_readable_status())
    )
    article = result.scalar_one_or_none()
    if not article:
        from fastapi import HTTPException
        raise HTTPException(404, "文章不存在")

    from app.config import get_settings
    settings = get_settings()
    base = (settings.frontend_url or "http://localhost:5173").rstrip("/")
    utm = f"utm_source={source}&utm_medium=share&utm_campaign=article"
    url = f"{base}/articles/{slug}?{utm}"

    body_preview = (article.body or "")[:80].replace("\n", " ").strip()

    return ShareLinkResponse(
        url=url,
        title=article.title,
        description=body_preview + "…" if len(article.body or "") > 80 else body_preview,
    )


@router.get("/tips/{tip_id}/share", response_model=ShareLinkResponse)
async def get_tip_share_link(
    tip_id: int,
    source: str = Query("direct"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DailyTip).where(DailyTip.id == tip_id))
    tip = result.scalar_one_or_none()
    if not tip:
        from fastapi import HTTPException
        raise HTTPException(404, "tips 不存在")

    from app.config import get_settings
    settings = get_settings()
    base = (settings.frontend_url or "http://localhost:5173").rstrip("/")
    utm = f"utm_source={source}&utm_medium=share&utm_campaign=tip"
    url = f"{base}/?{utm}"

    label, _ = _CATEGORY_META.get(tip.category.value, ("", ""))

    return ShareLinkResponse(
        url=url,
        title=f"StarLoom · {label}",
        description=tip.tip_text[:80],
    )
