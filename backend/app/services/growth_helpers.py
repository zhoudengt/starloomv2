"""Growth: referral rewards, zodiac cards, season pass, profiles."""

import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.growth import GroupBuy, GroupBuyMember, UserGrowthProfile, UserZodiacCard
from app.models.order import Order, OrderStatus, ProductType
from app.models.user import User


def _referral_code_for_user(user_id: int) -> str:
    """Deterministic unique code: R + 7-digit user id + 4 random digits."""
    suf = secrets.randbelow(9000) + 1000
    return f"R{user_id:07d}{suf}"


async def get_or_create_growth_profile(db: AsyncSession, user: User) -> UserGrowthProfile:
    result = await db.execute(
        select(UserGrowthProfile).where(UserGrowthProfile.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    gp = UserGrowthProfile(user_id=user.id, referral_code=_referral_code_for_user(user.id))
    db.add(gp)
    await db.flush()
    return gp


async def grant_zodiac_card_if_needed(
    db: AsyncSession, user_id: int, sign: str, source: str = "report"
) -> None:
    sign_l = sign.lower()[:24]
    result = await db.execute(
        select(UserZodiacCard).where(
            UserZodiacCard.user_id == user_id,
            UserZodiacCard.sign == sign_l,
        )
    )
    if result.scalar_one_or_none():
        return
    db.add(UserZodiacCard(user_id=user_id, sign=sign_l, source=source))
    await db.flush()


async def record_group_buy_if_any(db: AsyncSession, order: Order, user: User) -> None:
    extra = order.extra_data or {}
    gid = extra.get("group_public_id")
    if not gid:
        return
    result = await db.execute(select(GroupBuy).where(GroupBuy.public_id == str(gid).strip()))
    gb = result.scalar_one_or_none()
    if not gb or gb.status != "open":
        return
    if gb.expires_at < datetime.utcnow():
        gb.status = "expired"
        await db.flush()
        return
    dup = await db.execute(
        select(GroupBuyMember).where(
            GroupBuyMember.group_id == gb.id,
            GroupBuyMember.user_id == user.id,
        )
    )
    if dup.scalar_one_or_none():
        return
    if gb.member_count >= gb.target_count and gb.status == "open":
        return
    db.add(GroupBuyMember(group_id=gb.id, user_id=user.id, order_id=order.order_id))
    gb.member_count += 1
    if gb.member_count >= gb.target_count:
        gb.status = "complete"
    await db.flush()


async def apply_paid_order_rewards(db: AsyncSession, order: Order, user: User) -> None:
    """Referral credit (single level), season pass extension, first-paid tracking, group buy."""
    if order.status != OrderStatus.paid:
        return
    await record_group_buy_if_any(db, order, user)
    gp = await get_or_create_growth_profile(db, user)

    if order.product_type == ProductType.season_pass:
        base = gp.season_pass_until or datetime.utcnow()
        start = max(base, datetime.utcnow())
        gp.season_pass_until = start + timedelta(days=31)
        gp.updated_at = datetime.utcnow()

    if gp.first_paid_at is None:
        gp.first_paid_at = datetime.utcnow()
        inviter_id = gp.referred_by_user_id
        if inviter_id and inviter_id != user.id:
            inv = await db.execute(
                select(UserGrowthProfile).where(UserGrowthProfile.user_id == inviter_id)
            )
            inv_gp = inv.scalar_one_or_none()
            if inv_gp:
                inv_gp.credit_yuan = (inv_gp.credit_yuan or Decimal("0")) + Decimal("2.00")
                inv_gp.updated_at = datetime.utcnow()
    gp.updated_at = datetime.utcnow()
    await db.flush()


async def bind_referral_if_new_user(
    db: AsyncSession, user: User, ref_code: str | None
) -> None:
    if not ref_code or not str(ref_code).strip():
        return
    code = str(ref_code).strip().upper()[:32]
    result = await db.execute(
        select(UserGrowthProfile).where(UserGrowthProfile.referral_code == code)
    )
    inviter = result.scalar_one_or_none()
    if not inviter or inviter.user_id == user.id:
        return
    gp = await get_or_create_growth_profile(db, user)
    if gp.referred_by_user_id is None:
        gp.referred_by_user_id = inviter.user_id
        gp.updated_at = datetime.utcnow()
        await db.flush()
