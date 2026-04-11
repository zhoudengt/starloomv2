"""Daily Guide model — per-sign professional content (paid product)."""

import enum
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Date, DateTime, Enum, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GuideCategory(str, enum.Enum):
    career = "career"
    wealth = "wealth"
    relationship = "relationship"
    energy = "energy"


class DailyGuide(Base):
    __tablename__ = "daily_guides"
    __table_args__ = (
        UniqueConstraint("sign", "category", "guide_date", name="uq_sign_cat_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sign: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[GuideCategory] = mapped_column(
        Enum(GuideCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    guide_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    preview: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_ir: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    transit_basis: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
