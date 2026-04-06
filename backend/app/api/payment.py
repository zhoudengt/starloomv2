"""Payment: 虎皮椒 xunhupay create, notify, status."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PaymentCreateBody
from app.config import Settings, get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.growth import GroupBuy, GroupBuyMember
from app.models.order import Order, OrderStatus, ProductType
from app.models.user import User
from app.services.growth_helpers import apply_paid_order_rewards
from app.services.payment_service import (
    create_xunhupay_payment,
    default_order_expiry,
    generate_order_id,
    query_xunhupay_order,
    verify_notify,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payment", tags=["payment"])

PRODUCT_PRICES: dict[str, Decimal] = {
    "personality": Decimal("0.10"),
    "compatibility": Decimal("0.20"),
    "annual": Decimal("0.30"),
    "chat": Decimal("0.10"),
    "personality_career": Decimal("0.07"),
    "personality_love": Decimal("0.07"),
    "personality_growth": Decimal("0.07"),
    "astro_event": Decimal("0.10"),
    "season_pass": Decimal("0.13"),
}

GROUP_BUY_DISCOUNT = Decimal("0.70")


async def _expected_amount_for_payment(
    db: AsyncSession,
    user: User,
    product_type: str,
    extra: dict[str, Any],
) -> Decimal:
    if product_type not in PRODUCT_PRICES:
        raise HTTPException(status_code=400, detail="Invalid product_type")
    base = PRODUCT_PRICES[product_type]
    gid = (extra or {}).get("group_public_id")
    if not gid:
        return base
    result = await db.execute(select(GroupBuy).where(GroupBuy.public_id == str(gid).strip()))
    gb = result.scalar_one_or_none()
    if not gb:
        raise HTTPException(status_code=400, detail="Invalid group")
    if gb.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Group expired")
    if gb.status != "open":
        raise HTTPException(status_code=400, detail="Group closed")
    if gb.product_type != product_type:
        raise HTTPException(status_code=400, detail="Group product mismatch")
    if gb.member_count >= gb.target_count:
        raise HTTPException(status_code=400, detail="Group full")
    dup = await db.execute(
        select(GroupBuyMember).where(
            GroupBuyMember.group_id == gb.id,
            GroupBuyMember.user_id == user.id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already in this group")
    return (base * GROUP_BUY_DISCOUNT).quantize(Decimal("0.01"))


def _xunhupay_channel_configured(settings: Settings, pay_method: str) -> bool:
    if pay_method == "wechat":
        return bool(settings.xunhupay_appid_wechat and settings.xunhupay_appsecret_wechat)
    if pay_method == "alipay":
        return bool(settings.xunhupay_appid_alipay and settings.xunhupay_appsecret_alipay)
    return False


def _match_notify_secret(settings: Settings, data: dict[str, Any]) -> Optional[str]:
    """用回调中的 appid 匹配密钥并验签；若无 appid 则依次尝试两渠道。"""
    aid = str(data.get("appid") or "").strip()
    if aid and aid == settings.xunhupay_appid_wechat.strip():
        sec = settings.xunhupay_appsecret_wechat
        return sec if sec and verify_notify(data, sec) else None
    if aid and aid == settings.xunhupay_appid_alipay.strip():
        sec = settings.xunhupay_appsecret_alipay
        return sec if sec and verify_notify(data, sec) else None
    for sec in (settings.xunhupay_appsecret_wechat, settings.xunhupay_appsecret_alipay):
        if sec and verify_notify(data, sec):
            return sec
    return None


@router.post("/create")
async def payment_create(
    body: PaymentCreateBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    extra = dict(body.extra_data) if body.extra_data else {}
    expected = await _expected_amount_for_payment(db, user, body.product_type, extra)
    if body.amount != expected:
        raise HTTPException(status_code=400, detail="Amount mismatch")

    if body.pay_method not in ("wechat", "alipay"):
        raise HTTPException(status_code=400, detail="Invalid pay_method")

    settings = get_settings()
    order_id = generate_order_id()
    product = ProductType(body.product_type)

    if not settings.xunhupay_notify_url.strip():
        raise HTTPException(status_code=503, detail="Payment not configured: XUNHUPAY_NOTIFY_URL")
    if not _xunhupay_channel_configured(settings, body.pay_method):
        raise HTTPException(
            status_code=503,
            detail=f"Payment channel not configured for {body.pay_method}",
        )

    order = Order(
        order_id=order_id,
        user_id=user.id,
        product_type=product,
        amount=expected,
        status=OrderStatus.pending,
        pay_method=body.pay_method,
        expired_at=default_order_expiry(),
        extra_data=extra,
    )
    db.add(order)
    await db.flush()

    name_map = {
        "personality": "星座性格分析报告",
        "compatibility": "星座配对分析报告",
        "annual": "年度运势参考报告",
        "chat": "AI星座顾问对话",
        "personality_career": "性格报告·职场深潜包",
        "personality_love": "性格报告·恋爱深潜包",
        "personality_growth": "性格报告·成长深潜包",
        "astro_event": "天象事件参考分析",
        "season_pass": "星运月卡",
    }
    return_url = f"{settings.frontend_url.rstrip('/')}/payment/result?order_id={order_id}&auto=1"
    try:
        xh = await create_xunhupay_payment(
            settings,
            pay_method=body.pay_method,
            name=name_map[body.product_type],
            price=expected,
            order_id=order_id,
            return_url=return_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment provider error: {e!s}") from e

    if xh.get("errcode") != 0:
        msg = str(xh.get("errmsg") or "unknown error")
        raise HTTPException(status_code=502, detail=f"Payment gateway: {msg}")

    pay_jump = str(xh.get("url") or "").strip()
    qr = str(xh.get("url_qrcode") or "").strip()
    return {
        "order_id": order_id,
        "url": pay_jump,
        "url_qrcode": qr,
        "expire_at": order.expired_at.isoformat() if order.expired_at else None,
    }


@router.post("/notify")
async def payment_notify(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    settings = get_settings()
    ct = (request.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        raw = await request.json()
        data = {k: raw[k] for k in raw} if isinstance(raw, dict) else {}
    else:
        form = await request.form()
        data = {k: str(v) for k, v in form.multi_items()}

    if not _match_notify_secret(settings, data):
        raise HTTPException(status_code=400, detail="Invalid sign")

    order_id = str(data.get("trade_order_id") or "")
    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    status_raw = str(data.get("status") or "").upper()
    if status_raw != "OD":
        return Response(content="success", media_type="text/plain")

    pay_amount = Decimal(str(data.get("total_fee") or "0"))
    if pay_amount != order.amount:
        raise HTTPException(status_code=400, detail="Amount mismatch")

    if order.status == OrderStatus.paid:
        return Response(content="success", media_type="text/plain")

    order.status = OrderStatus.paid
    order.paid_at = datetime.utcnow()
    order.provider_order_id = str(data.get("open_order_id") or data.get("transaction_id") or "")
    await db.flush()
    ures = await db.execute(select(User).where(User.id == order.user_id))
    payer = ures.scalar_one_or_none()
    if payer:
        await apply_paid_order_rewards(db, order, payer)
    return Response(content="success", media_type="text/plain")


def _order_status_payload(order: Order) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "status": order.status.value,
        "product_type": order.product_type.value,
        "amount": str(order.amount),
        "extra_data": order.extra_data or {},
    }


@router.get("/pending")
async def payment_pending(
    product_type: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """当前用户该商品下最近一笔未过期且待支付的订单（用于避免重复下单、引导去结果页同步）。"""
    if product_type not in PRODUCT_PRICES:
        raise HTTPException(status_code=400, detail="Invalid product_type")
    now = datetime.utcnow()
    try:
        pt = ProductType(product_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid product_type") from e
    result = await db.execute(
        select(Order)
        .where(
            Order.user_id == user.id,
            Order.product_type == pt,
            Order.status == OrderStatus.pending,
            Order.expired_at > now,
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    order = result.scalar_one_or_none()
    if not order:
        return {"order_id": None}
    return {
        "order_id": order.order_id,
        "expired_at": order.expired_at.isoformat() if order.expired_at else None,
    }


@router.post("/sync/{order_id}")
async def payment_sync(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    主动向虎皮椒查询订单是否已支付并回写本地库。
    解决：本地开发时 XUNHUPAY_NOTIFY_URL 指向公网，异步通知打不到本机，轮询永远 pending 的问题。
    """
    settings = get_settings()
    result = await db.execute(
        select(Order).where(Order.order_id == order_id, Order.user_id == user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == OrderStatus.paid:
        return _order_status_payload(order)

    pm = (order.pay_method or "").strip()
    # Legacy: old demo orders in DB
    if pm == "demo":
        return _order_status_payload(order)

    if pm not in ("wechat", "alipay"):
        return _order_status_payload(order)

    if not _xunhupay_channel_configured(settings, pm):
        raise HTTPException(status_code=503, detail="Payment channel not configured")

    try:
        qh = await query_xunhupay_order(
            settings,
            pay_method=pm,
            out_trade_order=order.order_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        logger.exception("payment sync: query failed")
        raise HTTPException(status_code=502, detail=f"Payment query failed: {e!s}") from e

    if qh.get("errcode") != 0:
        return _order_status_payload(order)

    inner = qh.get("data")
    if not isinstance(inner, dict):
        return _order_status_payload(order)

    status_raw = str(inner.get("status") or "").upper()
    if status_raw != "OD":
        return _order_status_payload(order)

    fee_raw = inner.get("total_amount") or inner.get("total_fee") or "0"
    pay_amount = Decimal(str(fee_raw))
    if pay_amount.quantize(Decimal("0.01")) != order.amount.quantize(Decimal("0.01")):
        logger.error(
            "payment sync: amount mismatch order=%s local=%s remote=%s",
            order.order_id,
            order.amount,
            pay_amount,
        )
        raise HTTPException(status_code=400, detail="Amount mismatch")

    order.status = OrderStatus.paid
    order.paid_at = datetime.utcnow()
    order.provider_order_id = str(inner.get("open_order_id") or inner.get("transaction_id") or "")
    await db.flush()
    ures = await db.execute(select(User).where(User.id == order.user_id))
    payer = ures.scalar_one_or_none()
    if payer:
        await apply_paid_order_rewards(db, order, payer)

    return _order_status_payload(order)


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
    return _order_status_payload(order)
