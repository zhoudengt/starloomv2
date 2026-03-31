import enum
from datetime import date, datetime, time
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Date, DateTime, Enum, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.report import Report


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    birth_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    sun_sign: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, values_callable=lambda x: [e.value for e in x]),
        default=Gender.unknown,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    reports: Mapped[List["Report"]] = relationship("Report", back_populates="user")
