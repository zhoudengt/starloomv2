"""Growth engine: group buy, assist, share preview, zodiac cards, user credits."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserGrowthProfile(Base):
    """Referral code, credits (yuan), season pass window."""

    __tablename__ = "user_growth_profiles"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    referred_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    credit_yuan: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    season_pass_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserZodiacCard(Base):
    """Collected zodiac cards (deterministic unlock, not gacha)."""

    __tablename__ = "user_zodiac_cards"
    __table_args__ = (UniqueConstraint("user_id", "sign", name="uq_user_sign_card"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    sign: Mapped[str] = mapped_column(String(24), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="report")  # report|purchase|season
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GroupBuy(Base):
    __tablename__ = "group_buys"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    leader_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    product_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_count: Mapped[int] = mapped_column(default=2)
    member_count: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open|complete|expired
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GroupBuyMember(Base):
    __tablename__ = "group_buy_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("group_buys.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AssistTask(Base):
    __tablename__ = "assist_tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    required_count: Mapped[int] = mapped_column(default=3)
    current_count: Mapped[int] = mapped_column(default=0)
    report_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reward_unlocked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AssistRecord(Base):
    __tablename__ = "assist_records"
    __table_args__ = (UniqueConstraint("task_id", "helper_user_id", name="uq_task_helper"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("assist_tasks.task_id"), nullable=False, index=True)
    helper_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CompatibilityShareToken(Base):
    """Public preview link for pairing report (fission)."""

    __tablename__ = "compatibility_share_tokens"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
