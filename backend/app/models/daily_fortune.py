from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DailyFortune(Base):
    __tablename__ = "daily_fortunes"
    __table_args__ = (UniqueConstraint("sign", "fortune_date", name="uk_sign_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sign: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fortune_date: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
