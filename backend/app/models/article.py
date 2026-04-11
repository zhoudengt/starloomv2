import enum
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Date, DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArticleStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class ArticleCategory(str, enum.Enum):
    general = "general"
    career = "career"
    wealth = "wealth"
    relationship = "relationship"
    energy = "energy"


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    cover_image: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_ir: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    category: Mapped[ArticleCategory] = mapped_column(
        Enum(ArticleCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ArticleCategory.general,
        index=True,
    )
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cta_product: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[ArticleStatus] = mapped_column(
        Enum(ArticleStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ArticleStatus.draft,
        index=True,
    )
    source_keywords: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    publish_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class TipCategory(str, enum.Enum):
    career = "career"
    wealth = "wealth"
    relationship = "relationship"
    energy = "energy"


class DailyTip(Base):
    __tablename__ = "daily_tips"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    category: Mapped[TipCategory] = mapped_column(
        Enum(TipCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    sign: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    tip_text: Mapped[str] = mapped_column(Text, nullable=False)
    transit_basis: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    cta_product: Mapped[str] = mapped_column(String(64), nullable=False)
    tip_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
