"""虎皮椒 (xunhupay.com) payment integration."""

from __future__ import annotations

import hashlib
import logging
import random
import string
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def generate_xunhupay_hash(params: dict[str, Any], appsecret: str) -> str:
    """
    虎皮椒签名：非空参数按 key 字典序拼接 key=value&...，末尾追加 APPSECRET，MD5 小写。
    hash 键不参与签名。
    """
    filtered: dict[str, str] = {}
    for k, v in params.items():
        if k == "hash":
            continue
        if v is None or v == "":
            continue
        filtered[k] = str(v)
    sorted_keys = sorted(filtered.keys())
    string_a = "&".join(f"{k}={filtered[k]}" for k in sorted_keys)
    return md5_hex(string_a + appsecret)


def generate_order_id() -> str:
    return f"ord_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:12]}"


def _nonce_str(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def _sanitize_title(title: str) -> str:
    t = title.replace("%", "").strip()
    if len(t) > 127:
        t = t[:127]
    return t


def _xunhupay_credentials(settings: Settings, pay_method: str) -> tuple[str, str]:
    """pay_method: wechat | alipay"""
    if pay_method == "wechat":
        return settings.xunhupay_appid_wechat, settings.xunhupay_appsecret_wechat
    if pay_method == "alipay":
        return settings.xunhupay_appid_alipay, settings.xunhupay_appsecret_alipay
    raise ValueError(f"Invalid pay_method: {pay_method}")


async def create_xunhupay_payment(
    settings: Settings,
    *,
    pay_method: str,
    name: str,
    price: Decimal,
    order_id: str,
    return_url: Optional[str] = None,
    callback_url: Optional[str] = None,
    attach: Optional[str] = None,
) -> dict[str, Any]:
    """
    调用虎皮椒创建支付。返回原始 JSON（含 errcode/errmsg/url/url_qrcode）。
    """
    appid, appsecret = _xunhupay_credentials(settings, pay_method)
    if not appid or not appsecret:
        raise ValueError(f"Xunhupay credentials not configured for pay_method={pay_method}")

    notify_url = (settings.xunhupay_notify_url or "").strip()
    if not notify_url:
        raise ValueError("XUNHUPAY_NOTIFY_URL is not set")

    # total_fee 单位：元；官方示例可不强制两位小数
    price_str = format(price, "f").rstrip("0").rstrip(".") or "0"

    ts = int(time.time())
    nonce = _nonce_str(32)
    title = _sanitize_title(name)

    body: dict[str, Any] = {
        "version": "1.1",
        "appid": appid,
        "trade_order_id": order_id,
        "total_fee": price_str,
        "title": title,
        "time": ts,
        "notify_url": notify_url,
        "nonce_str": nonce,
    }
    if return_url:
        body["return_url"] = return_url
    if callback_url:
        body["callback_url"] = callback_url
    if attach:
        body["attach"] = attach

    body["hash"] = generate_xunhupay_hash(body, appsecret)

    base = settings.xunhupay_api_base.rstrip("/")
    url = f"{base}/payment/do.html"

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, data=body)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            logger.exception("xunhupay create HTTP error: %s", r.text)
            raise
        try:
            data = r.json()
        except Exception:
            logger.exception("xunhupay create invalid JSON: %s", r.text)
            raise

    errcode = data.get("errcode")
    if errcode != 0:
        logger.warning("xunhupay create failed: %s", data)
        return data

    # 校验返回签名（官方文档要求）
    resp_hash = str(data.get("hash") or "")
    if resp_hash and appsecret:
        expected = generate_xunhupay_hash(dict(data), appsecret)
        if expected != resp_hash:
            logger.error("xunhupay response hash mismatch")
            raise ValueError("Invalid payment gateway response signature")

    return data


def verify_notify(data: dict[str, Any], appsecret: str) -> bool:
    """验证虎皮椒异步通知签名。"""
    sign = str(data.get("hash") or "")
    if not sign:
        return False
    expected = generate_xunhupay_hash(dict(data), appsecret)
    return expected == sign


def default_order_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=30)
