"""Payment: xorpay create, notify, status."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PaymentCreateBody
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.order import Order, OrderStatus, ProductType
from app.models.user import User
from app.services.payment_service import (
    create_xorpay_payment,
    default_order_expiry,
    generate_order_id,
    verify_notify,
)

router = APIRouter(prefix="/api/v1/payment", tags=["payment"])

PRODUCT_PRICES: dict[str, Decimal] = {
    "personality": Decimal("9.90"),
    "compatibility": Decimal("19.90"),
    "annual": Decimal("29.90"),
    "chat": Decimal("9.90"),
}


@router.post("/create")
async def payment_create(
    body: PaymentCreateBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if body.product_type not in PRODUCT_PRICES:
        raise HTTPException(status_code=400, detail="Invalid product_type")
    expected = PRODUCT_PRICES[body.product_type]
    if body.amount != expected:
        raise HTTPException(status_code=400, detail="Amount mismatch")

    order_id = generate_order_id()
    product = ProductType(body.product_type)
    order = Order(
        order_id=order_id,
        user_id=user.id,
        product_type=product,
        amount=expected,
        status=OrderStatus.pending,
        pay_method=body.pay_method,
        expired_at=default_order_expiry(),
        extra_data={},
    )
    db.add(order)
    await db.flush()

    settings = get_settings()
    if not settings.xorpay_app_id or not settings.xorpay_app_secret:
        raise HTTPException(status_code=503, detail="Payment not configured")

    name_map = {
        "personality": "星座性格分析报告",
        "compatibility": "星座配对分析报告",
        "annual": "年度运势参考报告",
        "chat": "AI星座顾问对话",
    }
    return_url = f"{settings.frontend_url.rstrip('/')}/payment/result?order_id={order_id}"
    try:
        xp = await create_xorpay_payment(
            settings,
            name=name_map[body.product_type],
            price=expected,
            order_id=order_id,
            pay_type="native",
            return_url=return_url,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment provider error: {e!s}") from e

    pay_url = xp.get("url") or xp.get("pay_url") or xp.get("data", {}).get("url", "")
    qr = xp.get("qr") or xp.get("qr_code") or xp.get("data", {}).get("qr", "")
    return {
        "order_id": order_id,
        "pay_url": pay_url,
        "qr_code": qr,
        "expire_at": order.expired_at.isoformat() if order.expired_at else None,
    }


@router.post("/notify")
async def payment_notify(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    settings = get_settings()
    ct = (request.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        data = await request.json()
    else:
        form = await request.form()
        data = {k: str(v) for k, v in form.multi_items()}

    if not verify_notify(data, settings.xorpay_app_secret):
        raise HTTPException(status_code=400, detail="Invalid sign")

    order_id = str(data.get("order_id") or "")
    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    pay_price = Decimal(str(data.get("pay_price") or "0"))
    if pay_price != order.amount:
        raise HTTPException(status_code=400, detail="Amount mismatch")

    order.status = OrderStatus.paid
    order.paid_at = datetime.utcnow()
    order.xorpay_order_id = str(data.get("aoid") or "")
    await db.flush()
    return Response(content="success", media_type="text/plain")


@router.get("/status/{order_id}")
async def payment_status(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(Order).where(Order.order_id == order_id, Order.user_id == user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": order.order_id,
        "status": order.status.value,
        "product_type": order.product_type.value,
        "amount": str(order.amount),
    }
