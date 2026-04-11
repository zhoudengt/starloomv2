import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ProductType(str, enum.Enum):
    personality = "personality"
    compatibility = "compatibility"
    annual = "annual"
    chat = "chat"
    personality_career = "personality_career"
    personality_love = "personality_love"
    personality_growth = "personality_growth"
    astro_event = "astro_event"
    season_pass = "season_pass"
    daily_guide = "daily_guide"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    expired = "expired"
    refunded = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    product_type: Mapped[ProductType] = mapped_column(
        Enum(ProductType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, values_callable=lambda x: [e.value for e in x]),
        default=OrderStatus.pending,
        index=True,
    )
    pay_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    extra_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="orders")
