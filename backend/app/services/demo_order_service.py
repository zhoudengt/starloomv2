"""Demo mode: auto-create paid orders so reports work without real payment."""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus, ProductType
from app.models.user import User
from app.services.growth_helpers import apply_paid_order_rewards

_DEMO_AMOUNTS: dict[ProductType, Decimal] = {
    ProductType.personality: Decimal("0.10"),
    ProductType.compatibility: Decimal("0.20"),
    ProductType.annual: Decimal("0.30"),
    ProductType.chat: Decimal("0.10"),
    ProductType.personality_career: Decimal("0.07"),
    ProductType.personality_love: Decimal("0.07"),
    ProductType.personality_growth: Decimal("0.07"),
    ProductType.astro_event: Decimal("0.10"),
    ProductType.season_pass: Decimal("0.13"),
}


async def get_or_create_demo_paid_order(
    db: AsyncSession,
    user: User,
    product: ProductType,
) -> Order:
    order_id = f"demo_{user.id}_{product.value}"
    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    if order:
        if order.status != OrderStatus.paid:
            order.status = OrderStatus.paid
            order.paid_at = datetime.utcnow()
            await db.flush()
        return order

    new_order = Order(
        order_id=order_id,
        user_id=user.id,
        product_type=product,
        amount=_DEMO_AMOUNTS[product],
        status=OrderStatus.paid,
        paid_at=datetime.utcnow(),
        expired_at=datetime.utcnow() + timedelta(days=3650),
        pay_method="demo",
        extra_data={"demo": True},
    )
    db.add(new_order)
    try:
        await db.flush()
        await apply_paid_order_rewards(db, new_order, user)
        return new_order
    except IntegrityError:
        await db.rollback()
        result = await db.execute(select(Order).where(Order.order_id == order_id))
        order = result.scalar_one_or_none()
        if order:
            if order.status != OrderStatus.paid:
                order.status = OrderStatus.paid
                order.paid_at = datetime.utcnow()
                await db.flush()
            return order
        raise
