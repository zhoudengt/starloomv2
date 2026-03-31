"""xorpay (虎皮椒) payment integration."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def sign_create_order(app_id: str, order_id: str, price: str, app_secret: str) -> str:
    """MD5(app_id + order_id + price + app_secret) per spec."""
    return md5_hex(f"{app_id}{order_id}{price}{app_secret}")


def sign_notify(aoid: str, order_id: str, pay_price: str, app_secret: str) -> str:
    """Callback signature verification."""
    return md5_hex(f"{aoid}{order_id}{pay_price}{app_secret}")


def generate_order_id() -> str:
    return f"ord_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:12]}"


async def create_xorpay_payment(
    settings: Settings,
    *,
    name: str,
    price: Decimal,
    order_id: str,
    pay_type: str = "native",
    return_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Call xorpay API to create payment. Returns JSON from provider."""
    price_str = f"{price:.2f}"
    sign = sign_create_order(settings.xorpay_app_id, order_id, price_str, settings.xorpay_app_secret)
    url = f"{settings.xorpay_api_base.rstrip('/')}/api/pay/create"
    body: Dict[str, Any] = {
        "name": name,
        "pay_type": pay_type,
        "price": price_str,
        "order_id": order_id,
        "notify_url": settings.xorpay_notify_url,
    }
    if return_url:
        body["return_url"] = return_url
    headers = {
        "Authorization": f"Bearer {settings.xorpay_app_id}:{sign}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, json=body, headers=headers)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            logger.exception("xorpay create failed: %s", r.text)
            raise
        return r.json()


def verify_notify(data: dict, app_secret: str) -> bool:
    """Verify xorpay async notify payload."""
    aoid = str(data.get("aoid") or "")
    order_id = str(data.get("order_id") or "")
    pay_price = str(data.get("pay_price") or "")
    sign = str(data.get("sign") or "")
    expected = sign_notify(aoid, order_id, pay_price, app_secret)
    return expected == sign


def default_order_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=30)
